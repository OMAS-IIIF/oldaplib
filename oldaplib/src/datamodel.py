import io
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import Dict, List, Optional, Union, Any, Self, TextIO

from oldaplib.src.cachesingleton import CacheSingleton, CacheSingletonRedis
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.helpers.construct_processor import ConstructProcessor
from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.helpers.irincname import IriOrNCName
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapError, OldapErrorValue, \
    OldapErrorNoPermission, OldapErrorNotFound, OldapErrorAlreadyExists
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_qname import Xsd_QName

@dataclass
class ExternalOntologyChange:
    old_value: ExternalOntology | None
    action: Action

@dataclass
class ResourceClassChange:
    old_value: ResourceClass | None
    action: Action

@dataclass
class PropertyClassChange:
    old_value: PropertyClass | None
    action: Action

@serializer
class DataModel(Model):
    __graph: Xsd_NCName
    _project: Project
    __context: Context
    __version: SemanticVersion
    __extontos: dict[Xsd_QName, ExternalOntology]
    __propclasses: dict[Xsd_QName, PropertyClass | None]
    __resclasses: dict[Xsd_QName, ResourceClass | None]
    __extontos_changeset: dict[Xsd_QName, ExternalOntologyChange]
    __resclasses_changeset: dict[Xsd_QName, ResourceClassChange]
    __propclasses_changeset: dict[Xsd_QName, PropertyClassChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | str | None = None,
                 created: Xsd_dateTime | datetime | str | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | datetime | str | None = None,
                 project: Project | Iri | Xsd_NCName | str,
                 extontos: list[ExternalOntology] | None = None,
                 propclasses: list[PropertyClass] | None = None,
                 resclasses: list[ResourceClass] | None = None,
                 validate: bool = False) -> None:
        timestamp = Xsd_dateTime()
        if creator is None:
            creator = con.userIri
        if created is None:
            created = timestamp
        if contributor is None:
            contributor = con.userIri
        if modified is None:
            modified = timestamp
        super().__init__(connection=con,
                         creator=creator,
                         created=created,
                         contributor=contributor,
                         modified=modified,
                         validate=validate)
        self.__version = SemanticVersion()

        if isinstance(project, Project):
            self._project = project
        else:
            if not isinstance(project, (Iri, Xsd_NCName)):
                project = IriOrNCName(project, validate=validate)
            self._project = Project.read(self._con, project)
        self.__context = Context(name=self._con.context_name)
        self.__context[self._project.projectShortName] = self._project.namespaceIri
        self.__context.use(self._project.projectShortName)
        self.__graph = self._project.projectShortName

        self.__extontos = {}
        if extontos is not None:
            for e in extontos:
                self.__extontos[e.extonto_qname] = e
        self.__propclasses = {}
        if propclasses is not None:
            for p in propclasses:
                self.__propclasses[p.property_class_iri] = p
        self.__resclasses = {}
        if resclasses is not None:
            for r in resclasses:
                self.__resclasses[r.owl_class_iri] = r
        self.__extontos_changeset = {}
        self.__propclasses_changeset = {}
        self.__resclasses_changeset = {}

    def _as_dict(self):
        return {x.fragment: y for x, y in self._attributes.items()} | super()._as_dict() | {
            'project': self._project.projectShortName,
            **({'extontos': [x for x in self.__extontos.values()]} if self.__extontos else {}),
            **({'propclasses': [x for x in self.__propclasses.values()]} if self.__propclasses else {}),
            **({'resclasses': [x for x in self.__resclasses.values()]} if self.__resclasses else {}),
        }

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
        instance.__extontos = deepcopy(self.__extontos, memo)
        instance.__propclasses = deepcopy(self.__propclasses, memo)
        instance.__resclasses = deepcopy(self.__resclasses, memo)
        instance.__resclasses_changeset = deepcopy(self.__resclasses_changeset, memo)
        instance.__propclasses_changeset = deepcopy(self.__propclasses_changeset, memo)
        return instance

    def __getitem__(self, key: Xsd_QName) -> ExternalOntology | PropertyClass | ResourceClass:
        if key in self.__extontos:
            return self.__extontos[key]
        if key in self.__resclasses:
            return self.__resclasses[key]
        if key in self.__propclasses:
            return self.__propclasses[key]
        else:
            raise KeyError(key)

    def __setitem__(self, key: Xsd_QName, value: ExternalOntology | PropertyClass | ResourceClass) -> None:
        if isinstance(value, ExternalOntology):
            if self.__extontos.get(key) is None:
                self.__extontos_changeset[key] = ExternalOntologyChange(None, Action.CREATE)
            else:
                raise OldapErrorAlreadyExists(f'The external ontology "{key}" already exists. It cannot be replaced. Update/delete it.')
            self.__extontos[key] = value
        elif isinstance(value, PropertyClass):
            if self.__propclasses.get(key) is None:
                self.__propclasses_changeset[key] = PropertyClassChange(None, Action.CREATE)
            else:
                raise OldapErrorAlreadyExists(f'The property class "{key}" already exists. It cannot be replaced. Update/delete it.')
            self.__propclasses[key] = value
        elif isinstance(value, ResourceClass):
            if self.__resclasses.get(key) is None:
                self.__resclasses_changeset[key] = ResourceClassChange(None, Action.CREATE)
            else:
                raise OldapErrorAlreadyExists(f'The resource class "{key}" already exists. It cannot be replaced. Update/delete it.')
            self.__resclasses[key] = value
        else:
            raise OldapErrorValue(f'"{key}" must be either PropertyClass or ResourceClass (is "{type(value).__name__}")')

    def __delitem__(self, key: Xsd_QName | str) -> None:
        if not isinstance(key, Xsd_QName):
            key = Xsd_QName(key, validate=True)
        if key in self.__extontos:
            self.__extontos_changeset[key] = ExternalOntologyChange(self.__extontos[key], Action.DELETE)
            del self.__extontos[key]
        elif key in self.__propclasses:
            self.__propclasses_changeset[key] = PropertyClassChange(self.__propclasses[key], Action.DELETE)
            del self.__propclasses[key]
        elif key in self.__resclasses:
            self.__resclasses_changeset[key] = ResourceClassChange(self.__resclasses[key], Action.DELETE)
            del self.__resclasses[key]
        else:
            raise OldapErrorValue(f'"{key}" must be either PropertyClass or ResourceClass')

    def get(self, key: Xsd_QName | str) -> ExternalOntology | PropertyClass | ResourceClass | None:
        """
        Retrieves an instance of `PropertyClass` or `ResourceClass` associated with the
        specified `key`. The `key` can be either an `Iri` instance or a string. If the
        `key` is a string, it will be converted to an `Iri` object with validation before
        retrieving the associated object. Returns `None` if no associated object exists
        for the given `key`.

        :param key: Identifier for the instance to be retrieved. Can be a string or
           an Iri object.
        :return: An instance of `PropertyClass` or `ResourceClass` associated with the
           given key, or `None` if no match is found.
        :raises OldapErrorValue: If the `key` is not a valid Iri object.
        :raises OldapErrorNotFound: If no instance is found for the given `key`.
        """
        if not isinstance(key, Xsd_QName):
            key = Xsd_QName(key, validate=True)
        if key in self.__extontos:
            return self.__extontos[key]
        elif key in self.__propclasses:
            return self.__propclasses[key]
        elif key in self.__resclasses:
            return self.__resclasses[key]
        else:
            return None

    def get_extontos(self) -> list[Xsd_QName]:
        """
        Extract and return the list of extended ontologies.

        This method retrieves the extended ontologies by iterating over an internal
        attribute and returning the values.

        :return: A list containing the extended ontologies.
        :rtype: list[Xsd_QName]
        """
        return [x for x in self.__extontos]

    def get_propclasses(self) -> list[Xsd_QName]:
        """
        Get a list of the IRIs of the standalone property classes.

        This method retrieves and returns a list containing the IRIs of
        the property classes that have been identified as standalone.

        :return: List of IRIs for standalone property classes
        :rtype: list[Iri]
        """
        return [x for x in self.__propclasses]

    def get_resclasses(self) -> list[Xsd_QName]:
        """
        Get a list of the IRIs of the resource classes.

        This method retrieves a list of IRIs corresponding to resource classes. It
        provides a way to access these IRIs directly.

        :return: A list containing IRIs of the resource classes
        :rtype: list[Iri]
        """
        return [x for x in self.__resclasses]

    @property
    def context(self) -> Context:
        return self.__context

    @property
    def changeset(self) -> dict[Xsd_QName, ExternalOntologyChange | PropertyClassChange | ResourceClassChange]:
        return self.__extontos_changeset | self.__resclasses_changeset | self.__propclasses_changeset

    def clear_changeset(self) -> None:
        """
        Clears all recorded changes from the current changeset. The function iterates through
        various internal tracking structures and resets or clears their state as needed. This
        ensures that the current changeset reflects no modifications and all marked changes
        are reverted or cleared.

        Raises:
            No explicit errors are raised by this function

        Returns:
            None
        """
        for onto, change in self.__extontos_changeset.items():
            if change.action == Action.MODIFY:
                self.__extontos[onto].clear_changeset()
        for prop, change in self.__propclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__propclasses[prop].clear_changeset()
        self.__propclasses_changeset = {}
        for res, change in self.__resclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__resclasses[res].clear_changeset()
        self.__resclasses_changeset = {}
        self._changeset = {}

    def notifier(self, what: Xsd_QName) -> None:
        if what in self.__extontos:
            self.__extontos_changeset[what] = ExternalOntologyChange(None, Action.MODIFY)
        elif what in self.__propclasses:
            self.__propclasses_changeset[what] = PropertyClassChange(None, Action.MODIFY)
        elif what in self.__resclasses:
            self.__resclasses_changeset[what] = ResourceClassChange(None, Action.MODIFY)
        else:
            raise OldapErrorInconsistency(f'No resclass or property "{what}" in datamodel.')

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project | Xsd_QName | Xsd_NCName | str,
             ignore_cache: bool = False):
        logger = logging.getLogger(__name__)

        logger.debug(f'Reading datamodel for project {project}')

        if isinstance(project, Project):
            proj = project
        else:
            proj = Project.read(con, project)
        cache = CacheSingletonRedis()
        if not ignore_cache:
            tmp = cache.get(Xsd_QName(proj.projectShortName, 'shacl'), connection=con)
            if tmp is not None:
                return tmp

        context = Context(name=con.context_name)
        context[proj.projectShortName] = proj.namespaceIri
        context.use(proj.projectShortName)
        graph = proj.projectShortName
        #
        # first we read all the SHACL
        #
        shacl_obj = ConstructProcessor.query_shacl(con=con, project=proj)
        onto_obj = ConstructProcessor.query_onto(con=con, project=proj)

        if not shacl_obj:
            raise OldapErrorNotFound(f'Datamodel for project {project} not existing!')

        #
        # find all assertion properties and collect in list
        #
        assertion_propclasses: list[PropertyClass] = []
        props = {iri: shape for iri, shape in shacl_obj.items() if shape.get(Xsd_QName("oldap:appliesToProperty"), None)}
        for iri, propshape in props.items():
            attributes = {attr.fragment: value for attr, value in propshape[Xsd_QName("sh:property")].items()}
            property_class_iri = None
            if attributes.get("path") is not None:
                property_class_iri = attributes["path"]
                del attributes["path"]
            if not property_class_iri:
                property_class_iri = Xsd_QName(propshape.prefix, propshape.fragment.removesuffix('Shape'))
            if onto_obj.get(property_class_iri) is not None:
                # some consistency checks between SHACL and OWL
                if onto_obj[property_class_iri][Xsd_QName("rdf:type")] == Xsd_QName("owl:DatatypeProperty") and attributes.get('datatype') is None:
                    raise OldapErrorInconsistency(f'Property with "owl:DatatypeProperty" must have "sh:datetype" defined! ({property_class_iri})')
                if onto_obj[property_class_iri][Xsd_QName("rdf:type")] == Xsd_QName("owl:ObjectProperty") and attributes.get('class') is None:
                    raise OldapErrorInconsistency(f'Property with "owl:ObjectProperty" must have "sh:class" defined! ({property_class_iri})')
                if onto_obj[property_class_iri].get('rdfs:subPropertyOf'):
                    attributes['subPropertyOf'] = onto_obj[property_class_iri]['rdfs:subPropertyOf']

            propclass = PropertyClass(con=con,
                                     project=proj,
                                     property_class_iri=property_class_iri,
                                     creator=propshape[Xsd_QName("dcterms:creator")],
                                     created=propshape[Xsd_QName("dcterms:created")],
                                     modified=propshape[Xsd_QName("dcterms:modified")],
                                     contributor=propshape[Xsd_QName("dcterms:contributor")],
                                     appliesToProperty=propshape[Xsd_QName("oldap:appliesToProperty")],
                                     validate=False,
                                     **attributes)
            assertion_propclasses.append(propclass)

        #
        # we select all "sh:NodeShape", but we exclude assertion properties (which are sh:NodeShapes but must have
        # an "oldap:appliesToProperty" attribute!
        #
        resclasses: list[ResourceClass] = []
        rescs = {iri: shape for iri, shape in shacl_obj.items() if shape.get(Xsd_QName("rdf:type")) == Xsd_QName("sh:NodeShape") and not shape.get(Xsd_QName("oldap:appliesToProperty"))}
        #sorted_d = {iri: rescs[iri] for iri in sorted(rescs)}  # TODO: only for debugging....
        #rescs = sorted_d

        for resclass_shapeiri, resshape in rescs.items():
            propclasses = resshape.get(Xsd_QName("sh:property"))
            properties: list[PropertyClass] = []
            if propclasses:
                if not isinstance(propclasses, list):
                    propclasses = [propclasses]
                for propshape in propclasses:
                    property_class_iri = propshape[Xsd_QName("sh:path")]
                    del propshape[Xsd_QName("sh:path")]
                    attributes = {attr.fragment: value for attr, value in propshape.items()}
                    # TODO: insert here consistency checks...
                    # TODO: Add data from :onto graph
                    property = PropertyClass(con=con,
                                              project=proj,
                                              property_class_iri=property_class_iri,
                                              validate=False,
                                              **attributes)
                    properties.append(property)

            tmp_resclass_iri = resshape[Xsd_QName("sh:targetClass")]
            del resshape[Xsd_QName("sh:targetClass")]

            #
            # now let's extract the superclasses (which are given by the property "sh:node")
            #
            superclass = None
            if resshape.get(Xsd_QName("sh:node")):
                superclass = resshape[Xsd_QName("sh:node")]
                del resshape[Xsd_QName("sh:node")]
                if not isinstance(superclass, list):
                    superclass = [superclass]
            #
            # remove the suffix "Shape": This from SHACL, therefore we have the <superclass>Shape name
            #
            if superclass:
                superclass = [x.removesuffix('Shape') for x in superclass if x is not None]
            if tmp_resclass_iri.fragment != resclass_shapeiri.fragment.removesuffix('Shape'):
                raise OldapErrorInconsistency(f'Inconsistency in data model!! "{tmp_resclass_iri}" "{resclass_shapeiri}"')  # TODO: Better error message

            #
            # Superclasses from external ontologies OLDAP does not know about (e.g. for mapping to ontologies of other
            # frameworks are only defined in OWL and must be added here
            #
            if isinstance(onto_obj[tmp_resclass_iri], dict):
                tmp = onto_obj[tmp_resclass_iri].get(Xsd_QName("rdfs:subClassOf"), [])
                if tmp:
                    if not isinstance(tmp, list):
                        tmp = [tmp]
                    tmp_list = []
                    for sc in tmp:
                        if not superclass or sc in superclass:
                            continue
                        tmp_list.append(sc)

                    if tmp_list:
                        superclass.extend(tmp_list)

            #
            # prepare the attributes
            #
            attributes = {attr.fragment: value for attr, value in resshape.items() if
                          attr.fragment != 'property' and \
                          attr.fragment != 'type'}

            # TODO: add data from :onto graph
            resclass = ResourceClass(con=con,
                                     project=proj,
                                     owlclass_iri=tmp_resclass_iri,
                                     properties=properties,
                                     superclass=superclass,
                                     **attributes)
            resclasses.append(resclass)

        if shacl_obj.get(Xsd_QName(graph, 'shapes')):
            tmp_version = shacl_obj[Xsd_QName(graph, 'shapes')].get(Xsd_QName("schema:version"))
            shacl_version = SemanticVersion.fromString(tmp_version)
        else:
            shacl_version = SemanticVersion.fromString('0.0.1')

        if onto_obj.get(Xsd_QName(graph, 'ontology')):
            tmp_version = onto_obj[Xsd_QName(graph, 'ontology')].get(Xsd_QName('owl:versionInfo'))
            owl_version = SemanticVersion.fromString(tmp_version)
        else:
            owl_version = SemanticVersion.fromString('0.0.1')
        if shacl_version != owl_version:
            raise OldapErrorInconsistency(f'Versionnumber of SHACL ({shacl_version}) and OWL ({owl_version}) do not match')
        #
        # now read the external ontologies that are used in this datamodel
        #
        extontos: list[ExternalOntology] = []
        tmp_extontos = {iri: data for iri, data in shacl_obj.items() if data.get(Xsd_QName("rdf:type")) == Xsd_QName("oldap:ExternalOntology")}
        for iri, eoshape in tmp_extontos.items():
            attributes = {attr.fragment: value for attr, value in eoshape.items() if attr != (Xsd_QName("rdf:type"))}

            #
            # after the first read, all subsequent reads have the namespae already in the context and it will be a
            # Xsd_QName. Therefore, we have to convert the Xsd_QName to an Iri...
            #
            if attributes.get('namespaceIri'):
                if isinstance(attributes['namespaceIri'], Xsd_QName):
                    attributes['namespaceIri'] = context.qname2iri(attributes['namespaceIri'])

            extonto = ExternalOntology(con=con,
                                       projectShortName=proj.projectShortName,
                                       validate=False,
                                       **attributes)
            extontos.append(extonto)
            context[extonto.prefix] = extonto.namespaceIri

        #
        # now let's find all the OldapLists in order to set up the Context also for the OldapLists
        #
        ols = OldapList.search(con=con, project=proj)
        for ol in ols:
            oldaplist = OldapList.read(con=con, project=proj.projectShortName, oldapListId=ol.fragment)


        instance = cls(project=proj, con=con, propclasses=assertion_propclasses, resclasses=resclasses, extontos=extontos)
        for qname in instance.get_extontos():
            instance[qname].set_notifier(instance.notifier, qname)
        for qname in instance.get_propclasses():
            instance[qname].set_notifier(instance.notifier, qname)
        for qname in instance.get_resclasses():
            instance[qname].set_notifier(instance.notifier, qname)

        cache.set(Xsd_QName(proj.projectShortName, 'shacl'), instance)

        instance.clear_changeset()
        return instance

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Creates and writes all the information of the DataModel instance to the triple store.
        Ensures the user has the appropriate permissions and processes all relevant data
        to prepare and execute SPARQL queries for a semantic triple store.

        :param indent: The current indentation level used within the SPARQL query.
        :type indent: int
        :param indent_inc: The incremental indentation level for formatting nested SPARQL commands.
        :type indent_inc: int
        :return: None

        :raises OldapErrorNoPermission: If the logged-in user does not have the required permissions.
        :raises OldapError: If an unexpected error occurs during the SPARQL query execution.
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

        #
        # first we check if the graph already exists
        #
        sparql = context.sparql_context
        sparql += f"ASK {{ GRAPH {self.__graph}:shacl {{ ?s ?p ?o }} }}"
        sparql += '\n'
        result = self._con.query(sparql)
        if result['boolean']:
            raise OldapErrorAlreadyExists(f'Datamodel "{self.__graph}" already exists.')

        sparql = context.sparql_context

        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:shacl {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:shapes schema:version {self.__version.toRdf} .\n'
        sparql += '\n'

        for qname, onto in self.__extontos.items():
            sparql += onto.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        for propiri, propclass in self.__propclasses.items():
            sparql += propclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        for resiri, resclass in self.__resclasses.items():
            sparql += resclass.create_shacl(timestamp=timestamp, indent=2)
            sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += '\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self.__graph}:onto {{\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:ontology owl:type owl:Ontology ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}owl:versionInfo {self.__version.toRdf} ;\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}owl:versionIRI <http://oldap.org/ontology/{self.__graph}/version/{str(self.__version)}> .\n'
        sparql += '\n'

        # no OWL for ExternalOntologies

        for propiri, propclass in self.__propclasses.items():
            sparql += propclass.create_owl(indent=2)

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

        cache = CacheSingletonRedis()
        cache.set(Xsd_QName(self._project.projectShortName, 'shacl'), self)

    def update(self) -> None:
        """
        Updates the triple store to reflect changes made to the data model, such as adding,
        modifying, or deleting properties or resource classes. This method ensures that
        the data model and the underlying triple store are synchronized.

        :raises OldapError: If an error occurs during the update process.
        :raises OldapErrorNoPermission: If the logged-in actor lacks the required permissions.
        :return: None
        """
        logger = logging.getLogger(__name__)
        logger.debug(f'Updating datamodel for project {self._project.projectShortName}')
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        for qname, change in self.__extontos_changeset.items():
            logger.debug(f'External Ontology {qname} changed: {change.action}')
            match(change.action):
                case Action.CREATE:
                    self.__extontos[qname].create()
                case Action.MODIFY:
                    self.__extontos[qname].update()
                case Action.DELETE:
                    change.old_value.delete()

        for qname, change in self.__propclasses_changeset.items():
            logger.debug(f'Property class {qname} changed: {change.action}')
            match(change.action):
                case Action.CREATE:
                    self.__propclasses[qname].create()
                case Action.MODIFY:
                    self.__propclasses[qname].update()
                case Action.DELETE:
                    #self.__propclasses[qname].delete()
                    change.old_value.delete()

        for qname, change in self.__resclasses_changeset.items():
            logger.debug(f'Resource class {qname} changed: {change.action}')
            match (change.action):
                case Action.CREATE:
                    self.__resclasses[qname].create()
                case Action.MODIFY:
                    self.__resclasses[qname].update()
                case Action.DELETE:
                    #self.__resclasses[qname].delete()
                    change.old_value.delete()
        self.clear_changeset()
        cache = CacheSingletonRedis()
        cache.delete(Xsd_QName(self._project.projectShortName, 'shacl'))
        #cache.set(Xsd_QName(self._project.projectShortName, 'shacl'), self)

    def delete(self):
        """
        Deletes resources associated with a specific graph in the SHACL and ONTO context. This
        function checks permissions of the user, formulates SPARQL queries to delete data from
        the graph, and commits or rolls back the transaction accordingly. It finally clears the
        cache related to the graph.

        :raises OldapErrorNoPermission: If the actor does not have sufficient permissions for
            the operation.
        :raises OldapError: If an error occurs during the deletion process, including database
            transaction errors.
        :return: None
        """
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
        cache = CacheSingletonRedis()
        cache.delete(Xsd_QName(self._project.projectShortName, 'shacl'))

    def __to_trig_format(self, f: TextIO, indent: int = 0, indent_inc: int = 4) -> None:
        """
        Generates and writes TriG-formatted RDF data to the given TextIO object. The method constructs
        SHACL and OWL ontology representations based on the internal state and configuration of the
        object. SHACL validation shapes, ontology metadata, and RDF structure are included. This
        method is primarily used for exporting RDF data in a standard, compliant format.

        :param f: The output stream (e.g., a file or any TextIO object) where the generated TriG
            data will be written.
        :param indent: The base indentation level applied when formatting the output.
        :param indent_inc: The number of spaces added for each level of indentation to format
            nested structures cleanly.
        :return: None
        """
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        f.write('\n')
        f.write(context.turtle_context)
        f.write(f'\n{blank:{indent * indent_inc}}{self.__graph}:shacl {{\n')
        f.write(f'{blank:{(indent + 1) * indent_inc}}{self.__graph}:shapes schema:version {self.__version.toRdf} .\n')
        f.write('\n')
        for qname, onto in self.__extontos.items():
            f.write(onto.create_shacl(timestamp=timestamp, indent=1))
        f.write('\n\n')
        for iri, prop in self.__propclasses.items():
            if not prop.internal:
                f.write(prop.create_shacl(timestamp=timestamp, indent=1))
        f.write('\n\n')
        for iri, resclass in self.__resclasses.items():
            f.write(resclass.create_shacl(timestamp=timestamp, indent=1))
        f.write('\n\n')
        f.write(f'\n{blank:{indent * indent_inc}}}}\n')

        f.write(f'{blank:{indent * indent_inc}}{self.__graph}:onto {{\n')
        f.write(f'{blank:{(indent + 2) * indent_inc}}{self.__graph}:ontology owl:type owl:Ontology ;\n')
        f.write(f'{blank:{(indent + 2) * indent_inc}}owl:versionInfo {self.__version.toRdf} .\n')
        f.write('\n')
        for iri, prop in self.__propclasses.items():
            f.write(prop.create_owl(timestamp=timestamp, indent=2))
        for iri, resclass in self.__resclasses.items():
            f.write(resclass.create_owl(timestamp=timestamp))
        f.write(f'{blank:{indent * indent_inc}}}}\n')

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        with open(filename, 'w') as f:
            self.__to_trig_format(f, indent=indent, indent_inc=indent_inc)

    def write_as_str(self, indent: int = 0, indent_inc: int = 4) -> str:
        f = io.StringIO()
        self.__to_trig_format(f, indent=indent, indent_inc=indent_inc)
        return f.getvalue()



