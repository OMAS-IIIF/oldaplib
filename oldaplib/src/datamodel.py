from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any, Self

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapError, OldapErrorValue, \
    OldapErrorNoPermission, OldapErrorNotFound
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_qname import Xsd_QName


@dataclass
class ResourceClassChange:
    old_value: ResourceClass | None
    action: Action

@dataclass
class PropertyClassChange:
    old_value: PropertyClass | None
    action: Action

class DataModel(Model):
    """
    This class implements the representation of a OLDAP datamodel The datamodel itself contains standalone properties
    and resources with the associated property definitions. A datamodel can be instantiated completeley with all
    property and resource defintion at once, or it can be instanciated empty and property/resource definition can be
    added later incrementally.

    An OLDAP datamodel is bound to a project. This means, that a project can have exactely one datamodel. Currently
    a project is limited to one datamodel. The datamodel uses the namespace defined in the project definition and
    the project shortname is used for the named graphs:

    - _projectshortname:shacl_ contains the SHACL triples
    - _projectshortname:onto_ contains the OWL triples
    - _projectshortname:data_ contains the data
    """
    __graph: Xsd_NCName
    _project: Project
    __context: Context
    __version: SemanticVersion
    __propclasses: dict[Iri, PropertyClass | None]
    __resclasses: dict[Iri, ResourceClass | None]
    __resclasses_changeset: dict[Iri, ResourceClassChange]
    __propclasses_changeset: dict[Iri, PropertyClassChange]

    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 propclasses: list[PropertyClass] | None = None,
                 resclasses: list[ResourceClass] | None = None) -> None:
        """
        Create a datamodel instance
        :param con: Valid connection to triple store
        :type con: IConnection (subclass)
        :param project: Project instance, project iri or project shortnanme
        :type project: Project | Iri | Xsd_NCName | str
        :param propclasses: List of PropertyClass instances (standalone properties) [OPTIONAL]
        :param resclasses: List of ResourceClass instances [OPTIONAL]
        """
        super().__init__(connection=con,
                         creator=con.userIri,
                         created=None,
                         contributor=con.userIri,
                         modified=None)
        self.__version = SemanticVersion()

        if isinstance(project, Project):
            self._project = project
        else:
            self._project = Project.read(self._con, project)
        self.__context = Context(name=self._con.context_name)
        self.__context[self._project.projectShortName] = self._project.namespaceIri
        self.__context.use(self._project.projectShortName)
        self.__graph = self._project.projectShortName

        self.__propclasses = {}
        if propclasses is not None:
            for p in propclasses:
                self.__propclasses[p.property_class_iri] = p
        self.__resclasses = {}
        if resclasses is not None:
            for r in resclasses:
                self.__resclasses[r.owl_class_iri] = r
        self.__propclasses_changeset = {}
        self.__resclasses_changeset = {}

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('oldap:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if not self._project:
                return False, f'Actor has no ADMIN_MODEL permission. Actor not associated with a project.'
            proj = self._project.projectShortName
            if actor.inProject.get(proj) is None:
                return False, f'Actor has no ADMIN_MODEL permission for project "{proj}"'
            else:
                if AdminPermission.ADMIN_MODEL not in actor.inProject.get(proj):
                    return False, f'Actor has no ADMIN_MODEL permission for project "{proj}"'
            return True, "OK"

    def __deepcopy__(self, memo: dict[Any, Any]) -> Self:
        if id(self) in memo:
            return memo[id(self)]
        cls = self.__class__
        instance = cls.__new__(cls)
        memo[id(self)] = instance
        Model.__init__(instance,
                       connection=deepcopy(self._con, memo),
                       creator=deepcopy(self._creator, memo),
                       created=deepcopy(self._created, memo),
                       contributor=deepcopy(self._contributor, memo),
                       modified=deepcopy(self._modified, memo))
        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)
        # Other thins
        instance.__graph = deepcopy(self.__graph, memo)
        instance.__context = deepcopy(self.__context, memo)
        instance.__version = deepcopy(self.__version, memo)
        instance._project = deepcopy(self._project, memo)
        instance.__propclasses = deepcopy(self.__propclasses, memo)
        instance.__resclasses = deepcopy(self.__resclasses, memo)
        instance.__resclasses_changeset = deepcopy(self.__resclasses_changeset, memo)
        instance.__propclasses_changeset = deepcopy(self.__propclasses_changeset, memo)
        return instance

    def __getitem__(self, key: Iri) -> PropertyClass | ResourceClass:
        if key in self.__resclasses:
            return self.__resclasses[key]
        if key in self.__propclasses:
            return self.__propclasses[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key: Iri, value: PropertyClass | ResourceClass) -> None:
        if isinstance(value, PropertyClass):
            if self.__propclasses.get(key) is None:
                self.__propclasses_changeset[key] = PropertyClassChange(None, Action.CREATE)
            else:
                old_value = deepcopy(self.__propclasses[key])
                self.__propclasses_changeset[key] = PropertyClassChange(old_value, Action.MODIFY)
            self.__propclasses[key] = value
        elif isinstance(value, ResourceClass):
            if self.__resclasses.get(key) is None:
                self.__resclasses_changeset[key] = ResourceClassChange(None, Action.CREATE)
            else:
                old_value = deepcopy(self.__resclasses[key])
                self.__resclasses_changeset[key] = ResourceClassChange(old_value, Action.MODIFY)
            self.__resclasses[key] = value
        else:
            raise OldapErrorValue(f'"{key}" must be either PropertyClass or ResourceClass (is "{type(value).__name__}")')

    def __delitem__(self, key: Iri) -> None:
        if key in self.__propclasses:
            self.__propclasses_changeset[key] = PropertyClassChange(self.__propclasses[key], Action.DELETE)
            del self.__propclasses[key]
        elif key in self.__resclasses:
            self.__resclasses_changeset[key] = ResourceClassChange(self.__resclasses[key], Action.DELETE)
            del self.__resclasses[key]
        else:
            raise OldapErrorValue(f'"{key}" must be either PropertyClass or ResourceClass')

    def get(self, key: Iri) -> PropertyClass | ResourceClass | None:
        if key in self.__propclasses:
            return self.__propclasses[key]
        elif key in self.__resclasses:
            return self.__resclasses[key]
        else:
            return None

    def get_propclasses(self) -> list[Iri]:
        """
        Get list of the iri's of the standalone proeprty classes
        :return: List of Iri's
        :rtype: list[Iri]
        """
        return [x for x in self.__propclasses]

    def get_resclasses(self) -> list[Iri]:
        """
        Get list of the iri's of the resource classes'
        :return:
        """
        return [x for x in self.__resclasses]

    @property
    def changeset(self) -> dict[Iri, PropertyClassChange | ResourceClassChange]:
        return self.__resclasses_changeset | self.__propclasses_changeset

    def changeset_clear(self) -> None:
        for prop, change in self.__propclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__propclasses[prop].clear_changeset()
        self.__propclasses_changeset = {}
        for res, change in self.__resclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__resclasses[res].changeset_clear()
        self.__resclasses_changeset = {}
        self.clear_changeset()

    def notifier(self, what: Iri) -> None:
        if what in self.__propclasses:
            self.__propclasses_changeset[what] = PropertyClassChange(None, Action.MODIFY)
        elif what in self.__resclasses:
            self.__resclasses_changeset[what] = ResourceClassChange(None, Action.MODIFY)
        else:
            raise OldapErrorInconsistency(f'No resclass or property "{what}" in datamodel.')

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Iri | Xsd_NCName | str,
             ignore_cache: bool = False):
        """
        Read the datamodel fromn the given project from the triple store.
        :param con: Valid connection to the triple store
        :type con: IConnection or subclass thereof
        :param project: Project instance, project iri or project shortname
        :type project: Project | Iri | Xsd_NCName | str
        :param ignore_cache: If True, read the data from the triple store ifen if the project is in the cache
        :type ignore_cache: bool
        :return: Instance of the DataModel
        :rtype: DataModel
        """
        if isinstance(project, Project):
            project = project
        else:
            project = Project.read(con, project)
        cache = CacheSingleton()
        if not ignore_cache:
            tmp = cache.get(Xsd_QName(project.projectShortName, 'shacl'))
            if tmp is not None:
                tmp._con = con
                return tmp
        cls.__context = Context(name=con.context_name)
        cls.__context[project.projectShortName] = project.namespaceIri
        cls.__context.use(project.projectShortName)
        cls.__graph = project.projectShortName
        #
        # first we read the shapes metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?version
        FROM {cls.__graph}:shacl
        WHERE {{
            {cls.__graph}:shapes dcterms:hasVersion ?version .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Datamodel "{cls.__graph}:shacl" not found')
        cls.__version = SemanticVersion.fromString(res[0]['version'])
        #
        # now we read the OWL ontology metadata
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?version
        FROM {cls.__graph}:onto
        WHERE {{
            {cls.__graph}:ontology owl:versionInfo ?version .
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Datamodel "{cls.__graph}:onto" not found')
        version = SemanticVersion.fromString(res[0]['version'])
        if version != cls.__version:
            raise OldapErrorInconsistency(f'Versionnumber of SHACL ({cls.__version}) and OWL ({version}) do not match')
        #
        # now get the QNames of all standalone properties within the data model
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?prop
        FROM {cls.__graph}:shacl
        FROM shared:shacl
        WHERE {{
            ?prop a sh:PropertyShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        #
        # now read all standalone properties
        #
        propclasses: list[PropertyClass] = []
        for r in res:
            propnameshacl = str(r['prop'])
            propclassiri = propnameshacl.removesuffix("Shape")
            propclass = PropertyClass.read(con, project, Iri(propclassiri, validate=False), ignore_cache=ignore_cache)
            propclass.force_external()
            propclasses.append(propclass)
        sa_props = {x.property_class_iri: x for x in propclasses}
        #
        # now get all resources defined in the data model
        #
        query = cls.__context.sparql_context
        query += f"""
        SELECT ?shape
        FROM {cls.__graph}:shacl
        WHERE {{
            ?shape a sh:NodeShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        #
        # now read all resource classes
        #
        resclasses = []
        for r in res:
            resnameshacl = str(r['shape'])
            resclassiri = resnameshacl.removesuffix("Shape")
            # TODO: If ignore cache is not True, _prop_changeset of resourceclass is not empty!
            # create empty data model -> update -> add resource without property -> add property -> update
            # _prop_changeset is not empoty after update... ERROR!!!!!!!!!!!!!!!!!!!!!
            resclass = ResourceClass.read(con, project, Iri(resclassiri, validate=False), sa_props=sa_props, ignore_cache=ignore_cache)
            resclasses.append(resclass)
        instance = cls(project=project, con=con, propclasses=propclasses, resclasses=resclasses)
        for qname in instance.get_propclasses():
            instance[qname].set_notifier(instance.notifier, qname)
        for qname in instance.get_resclasses():
            instance[qname].set_notifier(instance.notifier, qname)
        cache.set(Xsd_QName(project.projectShortName, 'shacl'), instance)

        instance.changeset_clear()
        return instance

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        If the Instance has been created using the Python constructor, this method writes all the information
        of the DataModel instance to the triple store.
        :param indent: internl use
        :type indent: int
        :param indent_inc: internal use
        :type indent_inc: int
        :return: None
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:shapes dcterms:hasVersion {self.__version.toRdf} .\n'
        sparql += '\n'

        for propiri, propclass in self.__propclasses.items():
            if propclass.internal:
                raise OldapErrorInconsistency(f"Property class {propclass.property_class_iri} is internal and cannot be used here.")
            sparql += propclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        for resiri, resclass in self.__resclasses.items():
            sparql += resclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:onto {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:ontology owl:type owl:Ontology ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}owl:versionInfo {self.__version.toRdf} .\n'
        sparql += '\n'

        for propiri, propclass in self.__propclasses.items():
            sparql += propclass.create_owl_part1(timestamp=timestamp, indent=2)

        for resiri, resclass in self.__resclasses.items():
            sparql += resclass.create_owl(timestamp=timestamp, indent=2)

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'

        try:
            self._con.transaction_start()
            self._con.transaction_update(sparql)
            for propiri, propclass in self.__propclasses.items():
                propclass.set_creation_metadata(timestamp=timestamp)
            for resiri, resclass in self.__resclasses.items():
                resclass.set_creation_metadata(timestamp=timestamp)
            self._con.transaction_commit()
        except OldapError as err:
            self._con.transaction_abort()
            raise

        self.clear_changeset()

        cache = CacheSingleton()
        cache.set(Xsd_QName(self._project.projectShortName, 'shacl'), self)

    def update(self) -> None:
        """
        After modifing a data model by adding/modifying/deleting properties or resoutce classes, these
        changes have to be written to the triple store using the update method.
        :return: None
        :raises: OldapError or subclass
        """
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        for qname, change in self.__propclasses_changeset.items():
            match(change.action):
                case Action.CREATE:
                    self.__propclasses[qname].create()
                case Action.MODIFY:
                    self.__propclasses[qname].update()
                case Action.DELETE:
                    #self.__propclasses[qname].delete()
                    change.old_value.delete()
        for qname, change in self.__resclasses_changeset.items():
            match (change.action):
                case Action.CREATE:
                    self.__resclasses[qname].create()
                case Action.MODIFY:
                    self.__resclasses[qname].update()
                case Action.DELETE:
                    #self.__resclasses[qname].delete()
                    change.old_value.delete()
        self.changeset_clear()
        cache = CacheSingleton()
        cache.set(Xsd_QName(self._project.projectShortName, 'shacl'), self)

    def delete(self):
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        context = Context(name=self._con.context_name)
        sparql = context.sparql_context

        sparql1 = sparql + f"""DELETE WHERE {{ GRAPH {self.__graph}:shacl {{ ?s ?p ?o }} }}"""
        sparql2 = sparql + f"""DELETE WHERE {{ GRAPH {self.__graph}:onto {{ ?s ?p ?o }} }}"""

        try:
            self._con.transaction_start()
            self._con.transaction_update(sparql1)
            self._con.transaction_update(sparql2)
            self._con.transaction_commit()
        except OldapError as err:
            self._con.transaction_abort()
            raise


    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Write the complete datamodel in the trig format to a file.
        :param filename: The path of the file
        :type filename: str
        :param indent: Start level of indentation
        :type indent: int
        :param indent_inc: Increment (number of characters) of a indentation level
        :type indent_inc: int
        :return: None
        """
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime.now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write('\n')
            f.write(context.turtle_context)
            f.write(f'\n{blank:{indent * indent_inc}}{self.__graph}:shacl {{\n')
            f.write(f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:shapes dcterms:hasVersion {self.__version.toRdf} .\n')
            f.write('\n')
            for iri, prop in self.__propclasses.items():
                if not prop.internal:
                    f.write(prop.create_shacl(timestamp=timestamp, indent=1))
            for iri, resclass in self.__resclasses.items():
                f.write(resclass.create_shacl(timestamp=timestamp, indent=1))
            f.write(f'\n{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self.__graph}:onto {{\n')
            f.write(f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:ontology owl:type owl:Ontology ;\n')
            f.write(f'{blank:{(indent + 2) * indent_inc}}owl:versionInfo {self.__version.toRdf} .\n')
            f.write('\n')
            for iri, prop in self.__propclasses.items():
                f.write(prop.create_owl_part1(timestamp=timestamp, indent=2))
            for iri, resclass in self.__resclasses.items():
                f.write(resclass.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')




