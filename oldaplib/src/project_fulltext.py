"""Project-authorized access to the connection's managed Jena text backend."""
from uuid import UUID

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.jena_fulltext import jena_fulltext_fields
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration, OldapErrorNoPermission, OldapErrorValue
from oldaplib.src.project import Project


class ProjectFulltext:
    """Resolve project identity freshly and authorize each administration request.

    Args:
        con: Authenticated connection bound to the same dataset as its fulltext
            transport. A normal GraphDB connection deliberately refuses support.
        project: Project identifier accepted by Project.read.

    Token permission claims alone are insufficient: the ASK query checks active
    user, asserted membership and RDF 1.2 permission reifier in current RDF.
    """
    def __init__(self, con, project):
        if not con._managed_fulltext:
            raise OldapErrorConfiguration('Managed Jena fulltext is unavailable on this connection.')
        self.con = con
        self.project = Project.read(con, project, ignore_cache=True)
        self.name = str(self.project.projectShortName)
        self.graph = str(self.project.namespaceIri) + 'data'
        context = Context(name=con.context_name)
        actor = con.userdata.userIri.toRdf
        project_iri = self.project.projectIri.toRdf
        query = context.sparql_context + f'''ASK {{ GRAPH oldap:admin {{
            {actor} a oldap:User ; oldap:isActive true ; oldap:inProject ?project .
            VALUES (?project ?permission) {{
                ({project_iri} oldap:ADMIN_MODEL)
                (oldap:SystemProject oldap:ADMIN_OLDAP)
            }}
            ?grant rdf:reifies <<( {actor} oldap:inProject ?project )>> ;
                oldap:hasAdminPermission ?permission .
        }} }}'''
        if con.query(query).get('boolean') is not True:
            raise OldapErrorNoPermission('Fulltext administration requires current ADMIN_MODEL or ADMIN_OLDAP.')

    def read(self):
        """Return active configuration/revision, refusing a mismatched data graph."""
        state = self.con._fulltext_admin('FULLTEXT_STATE', {'project': self.name})
        if state.get('project') != self.name:
            raise OldapErrorConfiguration('Fulltext backend returned another project.')
        if state.get('configuration') is not None and state['configuration'].get('graph') != self.graph:
            raise OldapErrorConfiguration('Fulltext configuration does not match the authoritative project namespace.')
        return state

    def apply(self, configuration, expected_revision):
        """Validate full predicate paths and send one CAS activation, without retries.

        Configuration contains graph and fields. The graph must equal the freshly
        resolved project data graph. Revisions are opaque canonical UUIDs or null.
        Backend failures/uncertain outcomes are propagated, never replayed.
        """
        if not isinstance(configuration, dict) or set(configuration) != {'graph', 'fields'}:
            raise OldapErrorValue('Expected graph and fields configuration.')
        if configuration['graph'] != self.graph:
            raise OldapErrorValue('Fulltext graph must match the project namespace.')
        if expected_revision is not None:
            if not isinstance(expected_revision, str) or str(UUID(expected_revision)) != expected_revision:
                raise OldapErrorValue('expectedRevision must be a canonical UUID or null.')
        fields = configuration['fields']
        resolved = jena_fulltext_fields({'fields': fields}, Context(name=self.con.context_name))
        # Public administration takes normalized full IRIs, not caller-dependent
        # QName aliases that could change between project/model updates.
        normalized = {name: [str(p) for p in path] for name, path in resolved.items()}
        if normalized != fields:
            raise OldapErrorValue('Fulltext administration requires full predicate IRIs.')
        if len(fields) > 256 or any(len(path) > 16 for path in fields.values()):
            raise OldapErrorValue('At most 256 fields and 16 predicates per path are supported.')
        return self.con._fulltext_admin('FULLTEXT_APPLY', {
            'project': self.name, 'configuration': {'graph': self.graph, 'fields': normalized},
            'expectedRevision': expected_revision})
