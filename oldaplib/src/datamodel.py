from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from oldaplib.src.helpers.context import Context
from oldaplib.src.enums.action import Action
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapErrorInconsistency, OldapError, OldapErrorValue
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass

@dataclass
class ResourceClassChange:
    old_value: ResourceClass | None
    action: Action

@dataclass
class PropertyClassChange:
    old_value: PropertyClass | None
    action: Action

class DataModel(Model):
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
                 project: Project,
                 propclasses: list[PropertyClass] | None = None,
                 resclasses: list[ResourceClass] | None = None) -> None:
        super().__init__(con)
        self.__version = SemanticVersion()

        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
        self._project = project
        context = Context(name=self._con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        self.__graph = project.projectShortName

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
        return [x for x in self.__propclasses]

    def get_resclasses(self) -> list[Iri]:
        return [x for x in self.__resclasses]

    @property
    def changeset(self) -> dict[Iri, PropertyClassChange | ResourceClassChange]:
        return self.__resclasses_changeset | self.__propclasses_changeset

    def changeset_clear(self) -> None:
        for prop, change in self.__propclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__propclasses[prop].changeset_clear()
        self.__propclasses_changeset = {}
        for res, change in self.__resclasses_changeset.items():
            if change.action == Action.MODIFY:
                self.__resclasses[res].changeset_clear()
        self.__resclasses_changeset = {}

    def notifier(self, what: Iri) -> None:
        if what in self.__propclasses:
            self.__propclasses_changeset[what] = PropertyClassChange(None, Action.MODIFY)
        elif what in self.__resclasses:
            self.__resclasses_changeset[what] = ResourceClassChange(None, Action.MODIFY)
        else:
            raise OldapErrorInconsistency(f'No resclass or property "{what}" in datamodel.')

    @classmethod
    def read(cls, con: IConnection,
             project: Project):
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')
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
        WHERE {{
            ?prop a sh:PropertyShape
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=cls.__context, query_result=jsonobj)
        propclasses = []
        for r in res:
            propnameshacl = str(r['prop'])
            propclassiri = propnameshacl.removesuffix("Shape")
            propclass = PropertyClass.read(con, project, Iri(propclassiri, validate=False))
            propclasses.append(propclass)
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
        resclasses = []
        for r in res:
            resnameshacl = str(r['shape'])
            resclassiri = resnameshacl.removesuffix("Shape")
            resclass = ResourceClass.read(con, project, Iri(resclassiri, validate=False))
            resclasses.append(resclass)
        instance = cls(project=project, con=con, propclasses=propclasses, resclasses=resclasses)
        for qname in instance.get_propclasses():
            instance[qname].set_notifier(instance.notifier, qname)
        for qname in instance.get_resclasses():
            instance[qname].set_notifier(instance.notifier, qname)
        return instance

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
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
        #sparql += f'{blank:{(indent + 2) * indent_inc}}owl:imports <http://www.w3.org/2004/02/skos/core> ;\n'
        #sparql += f'{blank:{(indent + 2) * indent_inc}}owl:imports oldap:ontology .\n'
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

    def update(self):
        for qname, change in self.__propclasses_changeset.items():
            match(change.action):
                case Action.CREATE:
                    self.__propclasses[qname].create()
                case Action.MODIFY:
                    self.__propclasses[qname].update()
                case Action.DELETE:
                    self.__propclasses[qname].delete()
        for qname, change in self.__resclasses_changeset.items():
            match (change.action):
                case Action.CREATE:
                    self.__resclasses[qname].create()
                case Action.MODIFY:
                    self.__resclasses[qname].update()
                case Action.DELETE:
                    self.__resclasses[qname].delete()

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4):
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
            # f.write(f'{blank:{(indent + 2) * indent_inc}}owl:imports <http://www.w3.org/2004/02/skos/core> ;\n')
            # f.write(f'{blank:{(indent + 2) * indent_inc}}owl:imports oldap:ontology .\n')
            f.write('\n')
            for iri, prop in self.__propclasses.items():
                f.write(prop.create_owl_part1(timestamp=timestamp, indent=2))
            for iri, resclass in self.__resclasses.items():
                f.write(resclass.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')




