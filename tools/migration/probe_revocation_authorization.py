"""Atomic RDF 1.2 administrator authorization acceptance on owned Fuseki only."""
from unittest.mock import patch
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.authentication_revocation import AuthenticationRevocation
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_authentication_revocation import RevocationAttempt
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from probe_revocation_connection import RevocationProbeConnection


def run_authorization_checks(update, query, check):
    """Prove all-project/root checks, graph scope, stale grants and receipt replay."""
    context = Context(name='JENA_REVOCATION_AUTHORIZATION')
    before = Xsd_dateTime('2026-10-27T12:00:00Z')
    after = Xsd_dateTime('2026-10-27T12:01:00Z')
    sequence = 0

    def fixture(*, projects=('p1',), grants=(), root=False, grant_graph='oldap:admin',
                membership=True, annotation=True):
        nonlocal sequence
        sequence += 1
        stem = f'https://example.org/jena-authorization/{sequence}/'
        actor, target = Iri(stem + 'actor'), Iri(stem + 'target')
        project_iris = {name: Iri(stem + name) for name in set(projects) | set(grants)}
        memberships = ' '.join(f'{target.toRdf} oldap:inProject {project_iris[p].toRdf} .' for p in projects)
        update(context.sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
            {target.toRdf} a oldap:User ; oldap:authVersion "0"^^xsd:nonNegativeInteger ;
                dcterms:modified {before.toRdf} ; dcterms:contributor {target.toRdf} .
            {actor.toRdf} a oldap:User . {memberships}
        }} }}''')
        for name, permission, project in (
                [(p, 'ADMIN_USERS', project_iris[p].toRdf) for p in grants]
                + ([('root', 'ADMIN_OLDAP', 'oldap:SystemProject')] if root else [])):
            relation = f'{actor.toRdf} oldap:inProject {project} .' if membership else ''
            reifier = (f'<{stem}grant/{name}> rdf:reifies <<( {actor.toRdf} oldap:inProject {project} )>> ; '
                       f'oldap:hasAdminPermission oldap:{permission} .') if annotation else ''
            update(context.sparql_context + f'INSERT DATA {{ GRAPH {grant_graph} {{ {relation} {reifier} }} }}')
        command = AuthenticationRevocation.prepare(context=context, user=target, actor=actor,
                    expected=Xsd_nonNegativeInteger(0), previous_modified=before, modified=after)
        return RevocationAttempt.prepare(command), actor, target, project_iris

    def outcome(attempt, allowed):
        try:
            attempt.execute(update=update, query=query)
        except OldapErrorNoPermission:
            assert not allowed, 'Unexpected denial'
        else:
            assert allowed, 'Unauthorized mutation succeeded'
        command = attempt.command
        version = 1 if allowed else 0
        timestamp = after if allowed else before
        contributor = command.actor if allowed else command.user
        rows = query(context.sparql_context + f'''SELECT ?version ?modified ?contributor
            WHERE {{ GRAPH oldap:admin {{
                {command.user} oldap:authVersion ?version ; dcterms:modified ?modified ;
                    dcterms:contributor ?contributor .
            }} }}''')['results']['bindings']
        assert len(rows) == 1, 'Missing or multiple user mutation values'
        row = rows[0]
        assert int(row['version']['value']) == version, 'Unexpected version mutation'
        assert Xsd_dateTime(row['modified']['value']) == timestamp, 'Unexpected timestamp mutation'
        assert Iri(row['contributor']['value']).toRdf == contributor, 'Unexpected contributor mutation'


    cases = [
        ('all target projects authorized', dict(projects=('p1', 'p2'), grants=('p1', 'p2')), True),
        ('one missing project grant denies', dict(projects=('p1', 'p2'), grants=('p1',)), False),
        ('membership without annotation denies', dict(grants=('p1',), annotation=False), False),
        ('reifier without asserted membership denies', dict(grants=('p1',), membership=False), False),
        ('grants in another graph deny', dict(grants=('p1',), grant_graph='<urn:jena-auth:wrong-graph>'), False),
        ('no target project denies ordinary administrator', dict(projects=(), grants=('p1',)), False),
        ('root can manage user without projects', dict(projects=(), root=True), True),
        ('root can manage multiple projects', dict(projects=('p1', 'p2'), root=True), True),
        ('root annotation without membership denies', dict(root=True, membership=False), False),
        ('root membership without annotation denies', dict(root=True, annotation=False), False),
    ]
    for name, settings, allowed in cases:
        attempt, *_ = fixture(**settings)
        outcome(attempt, allowed)
        check('Authorization: ' + name)

    attempt, actor, target, projects = fixture(grants=('p1',))
    # Remove the live grant after preparing an otherwise valid command. The
    # actor's cached permissions/command do not authorize this database write.
    update(context.sparql_context + f'''DELETE WHERE {{ GRAPH oldap:admin {{
        ?grant rdf:reifies <<( {actor.toRdf} oldap:inProject {projects['p1'].toRdf} )>> ;
               oldap:hasAdminPermission oldap:ADMIN_USERS . }} }}''')
    outcome(attempt, False)
    check('Authorization: grant removed after preparation denies atomically')
    # Restoring permission must not turn an already denied operation into a
    # successful retry under the same identity.
    update(context.sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
        <https://example.org/restored-grant> rdf:reifies <<( {actor.toRdf} oldap:inProject {projects['p1'].toRdf} )>> ;
            oldap:hasAdminPermission oldap:ADMIN_USERS . }} }}''')
    outcome(attempt, False)
    check('Authorization: denied receipt remains denied after permission restoration')

    attempt, actor, target, _ = fixture(grants=('p1',))
    update(context.sparql_context + f'''INSERT DATA {{ GRAPH oldap:admin {{
        {target.toRdf} oldap:inProject <https://example.org/new-unmanaged-project> . }} }}''')
    outcome(attempt, False)
    check('Authorization: new target membership cannot bypass all-project check')

    attempt, actor, target, projects = fixture(grants=('p1',))
    outcome(attempt, True)
    update(context.sparql_context + f'''DELETE WHERE {{ GRAPH oldap:admin {{
        {actor.toRdf} oldap:inProject ?project . }} }}''')
    outcome(attempt, True)
    check('Authorization: committed replay stays successful after later grant removal')

    # Exercise the public method with both current and stale cached contexts.
    # In the stale case its local check passes; only the database guard denies.
    for name, settings, allowed in [
            ('project administrator succeeds', dict(grants=('p1',)), True),
            ('root administrator succeeds without target projects', dict(projects=(), root=True), True),
            ('stale permission denies without local/cache effects', dict(grants=()), False)]:
        attempt, actor, target, projects = fixture(**settings)
        con = RevocationProbeConnection(actor, update, query)
        actor_projects = ({Iri('oldap:SystemProject'): {AdminPermission.ADMIN_OLDAP}}
                          if settings.get('root') else {projects['p1']: {AdminPermission.ADMIN_USERS}})
        con._userdata = replace(con.userdata, inProject=InProjectClass(actor_projects))
        user = User(con=con, userIri=target, userId='managed', familyName='Probe',
                    givenName='Synthetic', email='managed@example.org', credentials='$2b$unused-fixture',
                    inProject={iri: set() for iri in projects.values()}, modified=before)
        assert user.check_for_permissions()[0]
        with patch('oldaplib.src.user.CacheSingletonRedis') as cache, \
                patch('oldaplib.src.user.Xsd_dateTime.now', return_value=after):
            try:
                result = user.revoke_authentication()
            except OldapErrorNoPermission:
                assert not allowed
            else:
                assert allowed and isinstance(result, Xsd_nonNegativeInteger) and int(result) == 1
            check('Authorization public User: ' + name,
                  int(user.authVersion) == (1 if allowed else 0)
                  and user.modified == (after if allowed else before)
                  and cache.return_value.delete.call_count == (1 if allowed else 0))

    # Serializable writer ordering may choose either winner. A denial must have
    # no user mutation, while success must have a complete committed receipt.
    for _ in range(6):
        attempt, actor, target, projects = fixture(grants=('p1',))
        removal = context.sparql_context + f'''DELETE WHERE {{ GRAPH oldap:admin {{
            {actor.toRdf} oldap:inProject ?project . }} }}'''
        with ThreadPoolExecutor(max_workers=2) as pool:
            mutation = pool.submit(attempt.execute, update=update, query=query)
            deletion = pool.submit(update, removal)
            deletion.result(timeout=20)
            try:
                mutation.result(timeout=20)
            except OldapErrorNoPermission:
                allowed = False
            else:
                allowed = True
        # Replay establishes the original decision, even though the actor now
        # has no membership. State and decision must agree in either ordering.
        outcome(attempt, allowed)
    check('Authorization: concurrent grant removal yields consistent atomic decisions (six runs)')
