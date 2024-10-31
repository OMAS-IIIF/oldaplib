from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Union, List, Dict, Callable, Self, Any, TypeVar

from oldaplib.src.cachesingleton import CacheSingleton
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.enums.attributeclass import AttributeClass
from oldaplib.src.enums.haspropertyattr import HasPropertyAttr
from oldaplib.src.globalconfig import GlobalConfig
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.Notify import Notify
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorAlreadyExists, \
    OldapErrorInconsistency, OldapErrorUpdateFailed, \
    OldapErrorValue, OldapErrorNotImplemented, OldapErrorNoPermission
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.helpers.semantic_version import SemanticVersion
from oldaplib.src.helpers.tools import RdfModifyRes, RdfModifyItem, lprint
from oldaplib.src.dtypes.bnode import BNode
from oldaplib.src.enums.action import Action
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.context import Context
from oldaplib.src.iconnection import IConnection
from oldaplib.src.model import Model
from oldaplib.src.helpers.attributechange import AttributeChange
from oldaplib.src.propertyclass import PropertyClass, Attributes, HasPropertyData
from oldaplib.src.xsd.xsd_nonnegativeinteger import Xsd_nonNegativeInteger
from oldaplib.src.xsd.xsd_string import Xsd_string

#
# Datatype definitions
#
RC = TypeVar('RC', bound='ResourceClass')
AttributeTypes = Iri | LangString | Xsd_boolean | ObservableDict[Iri, RC | None] | None
ResourceClassAttributesContainer = Dict[ResClassAttribute, AttributeTypes]
SuperclassParam = Iri | str | list[Iri] | tuple[Iri] | set[Iri] | None
AttributeParams = LangString | Xsd_boolean | SuperclassParam


@dataclass
class ResourceClassPropertyChange:
    old_value: Union[HasProperty, None]
    action: Action
    test_in_use: bool


#@strict
class ResourceClass(Model, Notify):
    _graph: Xsd_NCName
    _project: Project
    _sysproject: Project = None
    _owlclass_iri: Iri | None
    _attributes: ResourceClassAttributesContainer
    _properties: dict[Iri, HasProperty]
    _prop_changeset: dict[Iri, ResourceClassPropertyChange]
    _hp_prop_changeset: dict[Iri, ResourceClassPropertyChange]
    __version: SemanticVersion
    __from_triplestore: bool

    def assign_superclass(self, superclass: SuperclassParam) -> ObservableDict[Iri, RC | None]:

        def __check(sc: Any):
            scval = Iri(sc)
            sucla = None
            if scval.is_qname:
                match scval.prefix:
                    case self._project.projectShortName:
                        sucla = ResourceClass.read(self._con, self._project, scval)
                    case 'oldap':
                        sucla = ResourceClass.read(self._con, self._sysproject, scval)
                    case 'shared':
                        raise OldapErrorNotImplemented("Not yet implemented!")
                    case _:
                        # external resource not defined in Oldap
                        # -> we can not read it -> we pass None -> no "sh:node" in SHACL!
                        pass
            return scval, sucla

        data = ObservableDict()
        if isinstance(superclass, (list, tuple, set)):
            for sc in superclass:
                iri, sucla = __check(sc)
                data[iri] = sucla
        else:
            iri, sucla = __check(superclass)
            data[iri] = sucla
        data.set_on_change(self.__sc_changed)
        return data


    def __init__(self, *,
                 con: IConnection,
                 project: Project | Iri | Xsd_NCName | str,
                 owlclass_iri: Iri | str | None = None,
                 hasproperties: List[HasProperty] | None = None,
                 notifier: Callable[[PropClassAttr], None] | None = None,
                 notify_data: PropClassAttr | None = None,
                 **kwargs):
        Model.__init__(self,
                       connection=con,
                       creator=con.userIri,
                       created=None,
                       contributor=con.userIri,
                       modified=None)
        Notify.__init__(self, notifier, notify_data)
        self._prop_changeset = {}
        self._hp_prop_changeset = {}

        if isinstance(project, Project):
            self._project = project
        else:
            self._project = Project.read(self._con, project)
        if self._sysproject is None:
            self._sysproject = Project.read(self._con, Xsd_NCName("oldap"))

        context = Context(name=self._con.context_name)
        context[self._project.projectShortName] = self._project.namespaceIri
        context.use(self._project.projectShortName)
        self._graph = self._project.projectShortName

        if isinstance(owlclass_iri, Iri):
            self._owlclass_iri = owlclass_iri
        elif owlclass_iri is not None:
            self._owlclass_iri = Iri(owlclass_iri)
        else:
            self._owlclass_iri = None
        new_kwargs: dict[str, Any] = {}
        for name, value in kwargs.items():
            if name == ResClassAttribute.SUPERCLASS.value.fragment:
                new_kwargs[name] = self.assign_superclass(value)
            else:
                new_kwargs[name] = value
        #
        # now we add if necessary the mandatory superclass "oldap:Thing". Every ResourceClass is OLDAP must be
        # a subclass of "oldap:Thing"!
        #
        thing_iri = Iri('oldap:Thing', validate=False)
        if self._owlclass_iri != thing_iri:
            if not new_kwargs.get(ResClassAttribute.SUPERCLASS.value.fragment):
                new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment] = self.assign_superclass(thing_iri)
            else :
                if not thing_iri in new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment]:
                    thing = ResourceClass.read(self._con, self._sysproject, thing_iri)
                    new_kwargs[ResClassAttribute.SUPERCLASS.value.fragment][thing_iri] = thing
        self.set_attributes(new_kwargs, ResClassAttribute)

        self._properties = {}
        if hasproperties is not None:
            for hasprop in hasproperties:
                if isinstance(hasprop.prop, Iri):  # Reference to an external, standalone property definition
                    fixed_prop = Iri(str(hasprop.prop).removesuffix("Shape"))
                    try:
                        hasprop.prop = PropertyClass.read(self._con, self._project, fixed_prop)
                    except OldapErrorNotFound as err:
                        hasprop.prop = fixed_prop
                elif isinstance(hasprop.prop, PropertyClass):  # an internal, private property definition
                    if not hasprop.prop._force_external:
                        hasprop.prop._internal = owlclass_iri
                else:
                    raise OldapErrorValue(f'Unexpected property type: {type(hasprop.prop).__name__}')
                iri = hasprop.prop.property_class_iri if isinstance(hasprop.prop, PropertyClass) else hasprop.prop
                self._properties[iri] = hasprop
                if isinstance(hasprop.prop, PropertyClass):
                    hasprop.prop.set_notifier(self.notifier, hasprop.prop.property_class_iri)
                hasprop.set_notifier(self.hp_notifier, hasprop.prop.property_class_iri)

        for attr in ResClassAttribute:
            setattr(ResourceClass, attr.value.fragment, property(
                partial(ResourceClass._get_value, attr=attr),
                partial(ResourceClass._set_value, attr=attr),
                partial(ResourceClass._del_value, attr=attr)))

        self._test_in_use = False
        self.__version = SemanticVersion()
        self.__from_triplestore = False

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

    def pre_transform(self, attr: AttributeClass, value: Any) -> Any:
        if attr == ResClassAttribute.SUPERCLASS:
            return self.assign_superclass(value)
        else:
            return value

    def _change_setter(self, key: ResClassAttribute | Iri, value: AttributeParams | HasProperty) -> None:
        if not isinstance(key, (ResClassAttribute, Iri)):
            raise ValueError(f'Invalid key type {type(key)} of key {key}')
        if getattr(value, 'set_notifier', None) is not None:
            value.set_notifier(self.notifier, key)
        if isinstance(key, ResClassAttribute):
            super()._change_setter(key, value)
        elif isinstance(key, Iri):  # Iri, we add a HasProperty instance
            if self._properties.get(key) is None:  # Property not set -> CREATE action
                self._prop_changeset[key] = ResourceClassPropertyChange(None, Action.CREATE, False)
                if isinstance(value.prop, Iri):  # we just add a reference to an existing (!) standalone property!
                    try:
                        p = PropertyClass.read(self._con, project=self._project, property_class_iri=value.prop)
                        value.prop = p
                        self._properties[key] = value
                    except OldapErrorNotFound as err:
                        self._properties[key] = value
                else:
                    value.prop._internal = self._owlclass_iri  # we need to access the private variable here
                    value.prop._property_class_iri = key  # we need to access the private variable here
                    self._properties[key] = value
            else:  # REPLACE action
                if self._prop_changeset.get(key) is None:
                    self._prop_changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.REPLACE, True)
                else:
                    self._prop_changeset[key] = ResourceClassPropertyChange(self._prop_changeset[key].old_value, Action.REPLACE, True)
                if isinstance(value.prop, Iri):
                    try:
                        p = PropertyClass.read(self._con, project=self._project, property_class_iri=value.prop)
                        value.prop = p
                        self._properties[key] = value
                    except OldapErrorNotFound as err:
                        self._properties[key] = value
                else:
                    value.prop._internal = self._owlclass_iri  # we need to access the private variable here
                    value._property_class_iri = key  # we need to access the private variable here
                    self.prop._properties[key] = value
        else:
            raise OldapError(f'Invalid key type {type(key).__name__} of key {key}')
        self.notify()

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
        Notify.__init__(instance,
                        notifier=self._notifier,
                        data=deepcopy(self._notify_data, memo))
        # Copy internals of Model:
        instance._attributes = deepcopy(self._attributes, memo)
        instance._changset = deepcopy(self._changeset, memo)

        instance._graph = deepcopy(self._graph, memo)
        instance._project = deepcopy(self._project, memo)
        instance._sysproject = deepcopy(self._sysproject, memo)
        instance._owlclass_iri = deepcopy(self._owlclass_iri, memo)
        instance.__version = deepcopy(self.__version, memo)
        instance._properties = deepcopy(self._properties, memo)
        instance._prop_changeset = deepcopy(self._prop_changeset, memo)
        instance._hp_prop_changeset = deepcopy(self._hp_prop_changeset, memo)
        instance.__from_triplestore = self.__from_triplestore
        #
        # we have to set the callback for the associated props to the method in the new instance
        #
        for iri, hasprop in instance._properties.items():
            hasprop.set_notifier(instance.hp_notifier, hasprop.prop.property_class_iri)
        return instance


    def __getitem__(self, key: ResClassAttribute | Iri) -> AttributeTypes | HasProperty | Iri:
        if isinstance(key, ResClassAttribute):
            return super().__getitem__(key)
        elif isinstance(key, Iri):
            return self._properties.get(key)
        else:
            return None

    def get(self, key: ResClassAttribute | Iri) -> AttributeTypes | HasProperty | Iri | None:
        if isinstance(key, ResClassAttribute):
            return self._attributes.get(key)
        elif isinstance(key, Iri):
            return self._properties.get(key)
        else:
            return None

    def __setitem__(self, key: ResClassAttribute | Iri, value: AttributeParams | HasProperty) -> None:
        self._change_setter(key, value)

    def __delitem__(self, key: ResClassAttribute | Iri) -> None:
        if not isinstance(key, (ResClassAttribute, Iri)):
            raise ValueError(f'Invalid key type {type(key).__name__} of key {key}')
        if isinstance(key, ResClassAttribute):
            super().__delitem__(key)
        elif isinstance(key, Iri):
            if self._prop_changeset.get(key) is None:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._properties[key], Action.DELETE, False)
            else:
                self._prop_changeset[key] = ResourceClassPropertyChange(self._prop_changeset[key].old_value, Action.DELETE, False)
            del self._properties[key]
        self.notify()

    @property
    def owl_class_iri(self) -> Iri:
        return self._owlclass_iri

    @property
    def version(self) -> SemanticVersion:
        return self.__version

    @property
    def properties(self) -> dict[Iri, HasProperty]:
        return self._properties

    def properties_items(self):
        return self._properties.items()

    def attributes_items(self):
        return self._attributes.items()

    def __str__(self):
        blank = ' '
        indent = 2
        s = f'Shape: {self._owlclass_iri}Shape\n'
        s += super().__str__()
        s += f'{blank:{indent*1}}Properties:\n'
        sorted_properties = sorted(self._properties.items(), key=lambda prop: prop[1].order if prop[1].order is not None else 9999)
        for qname, hasprop in sorted_properties:
            s += f'{blank:{indent*2}}{qname} = {hasprop.prop} (minCount={hasprop.minCount}, maxCount={hasprop.maxCount}\n'
        return s

    def changeset_clear(self) -> None:
        super().clear_changeset()
        for prop, change in self._prop_changeset.items():
            if change.action == Action.MODIFY:
                self._properties[prop].prop.clear_changeset()
        self._prop_changeset = {}
        for hp_prop, change in self._hp_prop_changeset.items():
            if change.action == Action.MODIFY:
                self._properties[hp_prop].clear_changeset()
        self._hp_prop_changeset = {}

    def notifier(self, what: ResClassAttribute | Iri):
        if isinstance(what, ResClassAttribute):
            self._changeset[what] = AttributeChange(None, Action.MODIFY)
        elif isinstance(what, Iri):
            self._prop_changeset[what] = ResourceClassPropertyChange(None, Action.MODIFY, True)
        self.notify()

    def __sc_changed(self, oldval: ObservableDict[Iri, RC]):
        if self._changeset.get(ResClassAttribute.SUPERCLASS) is None:
            self._changeset[ResClassAttribute.SUPERCLASS] = AttributeChange(oldval, Action.MODIFY)

    def hp_notifier(self, what: Iri):
        if self._hp_prop_changeset.get(what) is None:
            self._hp_prop_changeset[what] = ResourceClassPropertyChange(None, Action.MODIFY, True)

    @property
    def in_use(self) -> bool:
        context = Context(name=self._con.context_name)
        query = context.sparql_context
        query += f"""
        SELECT (COUNT(?resinstances) as ?nresinstances)
        WHERE {{
            ?resinstance rdf:type {self._owlclass_iri} .
            FILTER(?resinstances != {self._owlclass_iri}Shape)
        }} LIMIT 2
        """
        jsonobj = self._con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            raise OldapError('Internal Error in "ResourceClass.in_use"')
        for r in res:
            if int(r.nresinstances) > 0:
                return True
            else:
                return False

    @staticmethod
    def __query_shacl(con: IConnection,
                      project: Project,
                      owl_class_iri: Iri) -> Attributes:
        context = Context(name=con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        query = context.sparql_context
        query += f"""
        SELECT ?attriri ?value
        FROM {graph}:shacl
        WHERE {{
            BIND({owl_class_iri}Shape AS ?shape)
            ?shape ?attriri ?value
        }}
         """
        jsonobj = con.query(query)
        res = QueryProcessor(context, jsonobj)
        if len(res) == 0:
            raise OldapErrorNotFound(f'Resource with iri "{owl_class_iri}" does not exist."')
        attributes: Attributes = {}
        for r in res:
            attriri = r['attriri']
            if attriri == 'rdf:type':
                tmp_owl_class_iri = r['value']
                if tmp_owl_class_iri == 'sh:NodeShape':
                    continue
                if tmp_owl_class_iri != owl_class_iri:
                    raise OldapError(f'Inconsistent Shape for "{owl_class_iri}": rdf:type="{tmp_owl_class_iri}"')
            elif attriri == 'sh:property':
                continue  # processes later – points to a BNode containing
            else:
                attriri = r['attriri']
                if isinstance(r['value'], Iri):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
                elif isinstance(r['value'], Xsd_string):
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(str(r['value']))
                elif isinstance(r['value'], BNode):
                    pass
                else:
                    if attributes.get(attriri) is None:
                        attributes[attriri] = []
                    attributes[attriri].append(r['value'])
        return attributes

    def _parse_shacl(self, attributes: Attributes) -> None:
        for key, val in attributes.items():
            if key == 'sh:targetClass':
                continue
            if key == 'dcterms:hasVersion':
                self.__version = SemanticVersion.fromString(val[0])
            elif key == 'dcterms:creator':
                self._creator = val[0]
            elif key == 'dcterms:created':
                self._created = val[0]
            elif key == 'dcterms:contributor':
                self._contributor = val[0]
            elif key == 'dcterms:modified':
                self._modified = val[0]
            elif key == 'sh:node':
                #
                # we expect sh:node only if the superclass is also defined as SHACL and we can read it's
                # definitions. All other superlcasses (referencing external ontologies) are only
                # used in the OWL definitions
                #
                if self._attributes.get(ResClassAttribute.SUPERCLASS) is None:
                    self._attributes[ResClassAttribute.SUPERCLASS] = ObservableDict(on_change=self.__sc_changed)
                if str(val[0]).endswith("Shape"):
                    owliri = Iri(str(val[0])[:-5], validate=False)
                    if owliri.prefix == 'oldap':
                        conf = GlobalConfig(self._con)
                        sysproj = conf.sysproject
                        superclass = ResourceClass.read(self._con, sysproj, owliri)
                    else:
                        superclass = ResourceClass.read(self._con, self._project, owliri)
                    self._attributes[ResClassAttribute.SUPERCLASS][owliri] = superclass
                else:
                    raise OldapErrorInconsistency(f'Value "{val[0]}" must end with "Shape".')
            else:
                attr = ResClassAttribute.from_value(key.as_qname)
                if attr.datatype == LangString:
                    self._attributes[attr] = attr.datatype(val)
                else:
                    self._attributes[attr] = attr.datatype(val[0])
                if getattr(self._attributes[attr], 'set_notifier', None) is not None:
                    self._attributes[attr].set_notifier(self.notifier, attr)

        self.__from_triplestore = True
        self.changeset_clear()

    @staticmethod
    def __query_resource_props(con: IConnection,
                               project: Project,
                               owlclass_iri: Iri,
                               sa_props: dict[Iri, PropertyClass] | None = None) -> List[HasProperty | Iri]:
        """
        This method queries and returns a list of properties defined in a sh:NodeShape. The properties may be
        given "inline" as BNode or may be a reference to an external sh:PropertyShape. These external shapes will be
        read when the ResourceClass is constructed (see __init__() of ResourceClass).

        :param con: IConnection instance
        :param graph: Name of the graph
        :param owlclass_iri: The QName of the OWL class defining the resource. The "Shape" ending will be added
        :return: List of PropertyClasses/QNames
        """

        context = Context(name=con.context_name)
        context[project.projectShortName] = project.namespaceIri
        context.use(project.projectShortName)
        graph = project.projectShortName

        #
        # first we query all the properties that part of this resource
        #
        # There may be several ways to defines these properties:
        #
        # A. sh:property <iri> ;
        #    Reference to an external property without any additional information. The property may be a foreign
        #    property (e.g. cidoc:E5_Event) or a standalone property within the given datamodel
        # B. sh:property [
        #        sh:node <iri> ;
        #        sh:maxCount "1"^^xsd:integer
        #    ]
        #    Reference to a foreign or standalone property with additional information (sh:minCount, sh:maxCount,
        #    sh:order, sh:group)
        # C. sh:property [
        #        dcterm:creation "..." ;
        #        ...
        #        sh:datatype: xsd:string ;
        #        ...
        #    ]
        #    An internal property local to this resource. May not be reused for other resources!
        #
        query = context.sparql_context
        query += f"""
        SELECT ?prop ?attriri ?value ?oo
        FROM {graph}:shacl
        WHERE {{
            BIND({owlclass_iri}Shape AS ?shape)
            ?shape sh:property ?prop .
            OPTIONAL {{
                ?prop ?attriri ?value .
                OPTIONAL {{
                    ?value rdf:rest*/rdf:first ?oo
                }}
            }}
        }}
        """
        jsonobj = con.query(query)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propinfos: Dict[Iri, Attributes] = {}
        #
        # first we run over all triples to gather the information about the properties of the possible
        # BNode based sh:property-Shapes.
        # NOTE: some of the nodes may actually be QNames referencing shapes defines as "standalone" sh:PropertyShape's.
        #
        for r in res:
            if r.get('value') and isinstance(r['value'], Iri) and r['value'] == 'rdf:type':
                continue
            if r.get('attriri') and not isinstance(r['attriri'], Iri):
                raise OldapError(f"There is some inconsistency in this shape! ({r['attriri']})")
            propnode = r['prop']  # Iri (case A. above) or a BNode (case B. and C. above)
            prop: PropertyClass | Iri
            if isinstance(propnode, Iri):
                qname = propnode
                propinfos[qname] = propnode
            elif isinstance(propnode, BNode):
                if propinfos.get(propnode) is None:
                    propinfos[propnode]: Attributes = {}
                PropertyClass.process_triple(r, propinfos[propnode])
            else:
                raise OldapError(f'Unexpected type for propnode in SHACL. Type = "{type(propnode)}".')
        #
        # now we collected all the information from the triple store. Let's process the information into
        # a list of full PropertyClasses or QName's to external definitions
        #
        proplist: List[HasProperty] = []
        for prop_iri, attributes in propinfos.items():
            if isinstance(attributes, Iri):
                #
                # Case A.: sh:property <iri> ;
                #
                if sa_props and prop_iri in sa_props:
                    proplist.append(HasProperty(con=con,
                                                prop=sa_props[prop_iri]))
                else:
                    proplist.append(HasProperty(con=con,
                                                prop=prop_iri))
            else:
                prop = PropertyClass(con=con, project=project)
                haspropdata = prop.parse_shacl(attributes=attributes)
                if haspropdata.refprop:
                    #
                    # Case B.
                    #
                    if sa_props and haspropdata.refprop in sa_props:
                        proplist.append(HasProperty(con=con,
                                                    prop=sa_props[haspropdata.refprop],
                                                    minCount=haspropdata.minCount,
                                                    maxCount=haspropdata.maxCount,
                                                    order=haspropdata.order,
                                                    group=haspropdata.group))  # TODO: Callback ????
                    else:
                        if haspropdata.refprop.is_qname:
                            if haspropdata.refprop.as_qname.prefix != project.projectShortName:
                                # TODO: the list has to come from outside! Config?? Or read from triplestore? !!!!!!!!!!
                                if haspropdata.refprop.as_qname.prefix in {'rdfs', 'dcterms', 'schema'}:
                                    propproj = Project.read(con=con, projectIri_SName='oldap')
                                else:
                                    propproj = Project.read(con=con, projectIri_SName=haspropdata.refprop.as_qname.prefix)
                            else:
                                propproj = project
                        else:
                            propproj = project
                        prop = PropertyClass.read(con, propproj, haspropdata.refprop)
                        prop.force_external()
                        proplist.append(HasProperty(con=con,
                                                    prop=prop,
                                                    minCount=haspropdata.minCount,
                                                    maxCount=haspropdata.maxCount,
                                                    order=haspropdata.order,
                                                    group=haspropdata.group))  # TODO: Callback ????
                else:
                    #
                    # Case C.
                    #
                    prop.read_owl()
                    if prop._internal != owlclass_iri:
                        OldapErrorInconsistency(f'ERRROR ERROR ERROR')
                    proplist.append(HasProperty(con=con,
                                                prop=prop,
                                                minCount=haspropdata.minCount,
                                                maxCount=haspropdata.maxCount,
                                                order=haspropdata.order,
                                                group=haspropdata.group))  # TODO: Callback ????
        return proplist

    def __read_owl(self):
        context = Context(name=self._con.context_name)
        query1 = context.sparql_context
        query1 += f"""
        SELECT ?prop ?p ?o
        FROM {self._owlclass_iri.prefix}:onto
        WHERE {{
   	        {self._owlclass_iri.toRdf} rdfs:subClassOf ?prop .
            ?prop ?p ?o .
            FILTER(?o != owl:Restriction)
            FILTER NOT EXISTS {{ ?prop a owl:Class }} .
        }}
        """
        jsonobj = self._con.query(query1)
        res = QueryProcessor(context=context, query_result=jsonobj)
        propdict = {}
        for r in res:
            bnode_id = str(r['prop'])
            if not propdict.get(bnode_id):
                propdict[bnode_id] = {}
            p = r['p']
            if p == 'owl:onProperty':
                propdict[bnode_id]['property_iri'] = r['o']
            elif p == 'owl:onClass':
                propdict[bnode_id]['to_node_iri'] = r['o']
            elif p == 'owl:minQualifiedCardinality':
                propdict[bnode_id]['min_count'] = r['o']
            elif p == 'owl:maxQualifiedCardinality':
                propdict[bnode_id]['max_count'] = r['o']
            elif p == 'owl:qualifiedCardinality':
                propdict[bnode_id]['min_count'] = r['o']
                propdict[bnode_id]['max_count'] = r['o']
            elif p == 'owl:onDatatype':
                propdict[bnode_id]['datatype'] = r['o']
            else:
                print(f'ERROR ERROR ERROR: Unknown restriction property: "{p}"')
        for bn, pp in propdict.items():
            if pp.get('property_iri') is None:
                OldapError('Invalid restriction node: No property_iri!')
            property_iri = pp['property_iri']
            prop = [x for x in self._properties if x == property_iri]
            if len(prop) != 1:
                raise OldapError(f'Property "{property_iri}" of "{self._owlclass_iri}" from OWL has no SHACL definition!')
            self._properties[prop[0]].prop.read_owl()
        #
        # now get all the subClassOf of other classes
        #
        query2 = context.sparql_context
        query2 += f"""
        SELECT ?superclass ?p ?o
        FROM {self._owlclass_iri.prefix}:onto
        WHERE {{
            {self._owlclass_iri.toRdf} rdfs:subClassOf ?superclass .
            FILTER isIRI(?superclass) 
        }}
        """
        jsonobj = self._con.query(query2)
        res = QueryProcessor(context=context, query_result=jsonobj)
        if not self._attributes.get(ResClassAttribute.SUPERCLASS):
            self._attributes[ResClassAttribute.SUPERCLASS] = ObservableDict(on_change=self.__sc_changed)
        for r in res:
            if r['superclass'] not in self._attributes[ResClassAttribute.SUPERCLASS]:
                self._attributes[ResClassAttribute.SUPERCLASS][r['superclass']] = None

    @classmethod
    def read(cls,
             con: IConnection,
             project: Project,
             owl_class_iri: Iri,
             sa_props: dict[Iri, PropertyClass] | None = None,
             ignore_cache: bool = False) -> Self:
        if not isinstance(project, Project):
            raise OldapErrorValue('The project parameter must be a Project instance')

        cache = CacheSingleton()
        if not ignore_cache:
            tmp = cache.get(owl_class_iri)
            if tmp is not None:
                tmp._con = con
                return tmp

        hasproperties: list[HasProperty | Iri] = ResourceClass.__query_resource_props(con=con,
                                                                                      project=project,
                                                                                      owlclass_iri=owl_class_iri,
                                                                                      sa_props=sa_props)
        resclass = cls(con=con, project=project, owlclass_iri=owl_class_iri, hasproperties=hasproperties)
        for hasprop in hasproperties:
            if isinstance(hasprop, HasProperty):  # not an Iri...
                if isinstance(hasprop.prop, PropertyClass):
                    hasprop.prop.set_notifier(resclass.notifier, hasprop.prop.property_class_iri)
                    hasprop.set_notifier(resclass.hp_notifier, hasprop.prop.property_class_iri)
                elif isinstance(hasprop.prop, Iri):
                    hasprop.set_notifier(resclass.hp_notifier, hasprop.prop)
                else:
                    raise OldapError(f'Invalid datatype: {type(hasprop.prop).__name}')
        attributes = ResourceClass.__query_shacl(con, project=project, owl_class_iri=owl_class_iri)
        resclass._parse_shacl(attributes=attributes)
        resclass.__read_owl()

        resclass.changeset_clear()

        cache = CacheSingleton()
        cache.set(resclass._owlclass_iri, resclass)
        return resclass

    def read_modified_shacl(self, *,
                            context: Context,
                            graph: Xsd_NCName,
                            indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:shacl\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._owlclass_iri}Shape as ?res)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def read_modified_owl(self, *,
                          context: Context,
                          graph: Xsd_NCName,
                          indent: int = 0, indent_inc: int = 4) -> Union[datetime, None]:
        blank = ''
        sparql = context.sparql_context
        sparql += f"{blank:{indent * indent_inc}}SELECT ?modified\n"
        sparql += f"{blank:{indent * indent_inc}}FROM {graph}:onto\n"
        sparql += f"{blank:{indent * indent_inc}}WHERE {{\n"
        sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self._owlclass_iri} as ?res)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
        sparql += f"{blank:{indent * indent_inc}}}}"
        jsonobj = self._con.transaction_query(sparql)
        res = QueryProcessor(context, jsonobj)
        if len(res) != 1:
            return None
        return res[0].get('modified')

    def create_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{(indent + 1)*indent_inc}}{self._owlclass_iri}Shape a sh:NodeShape, {self._owlclass_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:targetClass {self._owlclass_iri.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:hasVersion {self.__version.toRdf}'
        self._created = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:created {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:creator {self._creator.toRdf}'
        self._modified = timestamp
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:modified {timestamp.toRdf}'
        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}dcterms:contributor {self._contributor.toRdf}'
        for attr, value in self._attributes.items():
            if attr == ResClassAttribute.SUPERCLASS:
                #
                # In SHACL, superclasses are only added if we have access to it's SHACL definition, that is,
                # if it's given as ResourceClass instance.
                # Superclasses without SHACL definition will be only added to the OWL file for reasoning.
                #
                scset = [f'{iri.toRdf}Shape' for iri, resclass in value.items() if resclass]
                valstr = ", ".join(scset)
                if valstr:
                    sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:node {valstr}'
            else:
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}{attr.value} {value.toRdf}'

        sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property'
        sparql += f'\n{blank:{(indent + 3) * indent_inc}}['
        sparql += f'\n{blank:{(indent + 4) * indent_inc}}sh:path rdf:type'
        sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'

        for iri, hp in self._properties.items():
            if isinstance(hp.prop, Iri):
                # just a property Iri (to some foreign property in an "unknown" ontology...
                sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property {hp.prop.toRdf}'
                continue
            if hp.prop.internal is not None:
                # it's an internal property
                sparql += f' ;\n{blank:{(indent + 2)*indent_inc}}sh:property'
                sparql += f'\n{blank:{(indent + 3)*indent_inc}}[\n'
                sparql += hp.prop.property_node_shacl(timestamp=timestamp,
                                                      haspropdata=hp.haspropdata,
                                                      indent=4)
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
            else:
                # it's an external but well known property within the ontolopgy...
                if hp.minCount or hp.maxCount or hp.order or hp.group:
                    sparql += f' ;\n{blank:{(indent + 2) * indent_inc}}sh:property'
                    sparql += f'\n{blank:{(indent + 3) * indent_inc}}['
                    sparql += f'\n{blank:{(indent + 4) * indent_inc}}sh:node {iri}Shape'
                    sparql += hp.create_shacl(indent=4)
                    sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
                else:
                    sparql += f' ;\n{blank:{(indent + 2)*indent_inc}}sh:property {iri}Shape'
        #if len(self._properties) > 0:
        sparql += ' .\n'
        return sparql

    def create_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4):
        blank = ''
        sparql = ''
        for iri, hp in self._properties.items():
            if isinstance(hp.prop, Iri):
                continue
            if not hp.prop.from_triplestore:
                sparql += hp.prop.create_owl_part1(timestamp, indent + 2) + '\n'

        sparql += f'{blank:{(indent + 2) * indent_inc}}{self._owlclass_iri} rdf:type owl:Class ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:hasVersion {self.__version.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:created {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:creator {self._creator.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:modified {timestamp.toRdf} ;\n'
        sparql += f'{blank:{(indent + 3) * indent_inc}}dcterms:contributor {self._contributor.toRdf} ;\n'
        if self._attributes.get(ResClassAttribute.SUPERCLASS) is not None:
            sc = {x.toRdf for x in self._attributes[ResClassAttribute.SUPERCLASS].keys()}
            if Iri('oldap:Thing', validate=False).toRdf not in sc:
                sc.add(Iri('oldap:Thing', validate=False).toRdf)
        else:
            sc = {Iri('oldap:Thing', validate=False).toRdf}
        valstr = ", ".join(sc)
        sparql += f'{blank:{(indent + 3)*indent_inc}}rdfs:subClassOf {valstr}'
        i = 0
        for iri, hp in self._properties.items():
            sparql += ' ,\n'
            if isinstance(hp.prop, Iri):
                sparql += f'{blank:{(indent + 3) * indent_inc}}[\n'
                sparql += f'{blank:{(indent + 4) * indent_inc}}rdf:type owl:Restriction ;\n'
                sparql += f'{blank:{(indent + 4) * indent_inc}}owl:onProperty {hp.prop.toRdf}'
                sparql += hp.create_owl(4)
                sparql += f' ;\n{blank:{(indent + 3) * indent_inc}}]'
            else:
                sparql += hp.prop.create_owl_part2(haspropdata=hp, indent=(indent + 4))
            i += 1
        sparql += ' .\n'
        return sparql

    def set_creation_metadata(self, timestamp: Xsd_dateTime):
        self._created = timestamp
        self._creator = self._con.userIri
        self._modified = timestamp
        self._contributor = self._con.userIri
        self.__from_triplestore = True


    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        if self.__from_triplestore:
            raise OldapErrorAlreadyExists(f'Cannot create property that was read from triplestore before (property: {self._owlclass_iri}')
        timestamp = Xsd_dateTime.now()
        blank = ''
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += f'{blank:{indent * indent_inc}}INSERT DATA {{\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
        sparql += self.create_shacl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
        sparql += self.create_owl(timestamp=timestamp)
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'

        sparql += f'{blank:{indent * indent_inc}}}}\n'
        self._con.transaction_start()
        if self.read_modified_shacl(context=context, graph=self._graph) is not None:
            self._con.transaction_abort()
            raise OldapErrorAlreadyExists(f'Object "{self._owlclass_iri}" already exists.')
        try:
            self._con.transaction_update(sparql)
        except OldapError:
            lprint(sparql)
            self._con.transaction_abort()
            raise
        modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
        modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self.set_creation_metadata(timestamp=timestamp)
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Creating resource "{self._owlclass_iri}" failed.')
        self.changeset_clear()
        cache = CacheSingleton()
        cache.set(self._owlclass_iri, self)

    def write_as_trig(self, filename: str, indent: int = 0, indent_inc: int = 4) -> None:
        with open(filename, 'w') as f:
            timestamp = Xsd_dateTime.now()
            blank = ''
            context = Context(name=self._con.context_name)
            f.write(context.turtle_context)

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:shacl {{\n')
            f.write(self.create_shacl(timestamp=timestamp))
            f.write(f'\n{blank:{indent * indent_inc}}}}\n')

            f.write(f'{blank:{indent * indent_inc}}{self._graph}:onto {{\n')
            f.write(self.create_owl(timestamp=timestamp))
            f.write(f'{blank:{indent * indent_inc}}}}\n')

    def __add_new_property_ref_shacl(self, *,
                                     iri: Iri,
                                     hasprop: HasProperty | None = None,
                                     indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'INSERT DATA {{#B\n'
        sparql += f'    GRAPH {self._graph}:shacl {{\n'
        sparql += f'{blank:{indent * indent_inc}}{self._owlclass_iri}Shape sh:property [\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}sh:node {iri.toRdf}'
        sparql += hasprop.create_shacl()
        sparql += f' ; \n{blank:{indent * indent_inc}}] .\n'
        sparql += f'    }}\n'
        sparql += f'}}\n'
        return sparql

    def __delete_property_ref_shacl(self,
                                    owlclass_iri: Iri,
                                    propclass_iri: Iri,
                                    indent: int = 0,
                                    indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:shacl\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?propnode sh:node {propclass_iri.toRdf}Shape .\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}} UNION {{\n'
        sparql += f'{blank:{(indent + 2) * indent_inc}}FILTER(?propnode = {propclass_iri.toRdf}Shape)\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __delete_property_ref_onto(self,
                                   owlclass_iri: Iri,
                                   propclass_iri: Iri,
                                   indent: int = 0,
                                   indent_inc: int = 4) -> str:
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri.toRdf} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} rdfs:subClassOf ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode owl:onProperty {propclass_iri.toRdf} .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __update_shacl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset and not self._prop_changeset and not self._hp_prop_changeset:
            return ''
        blank = ''
        sparql_list = []

        #
        # First process attributes
        #
        for item, change in self._changeset.items():
            sparql: str | None = None
            if item == ResClassAttribute.SUPERCLASS:
                #
                # Superclasses are only added to SHACL if they have been supplied as ResourceClass instance.
                # Then the subclass inherits all property definitions!!
                # Other superclasses where we do not have access to a SHACL definition are only added to
                # OWL in order to allow reasoning.
                #
                if change.old_value:
                    old_set = {iri for iri, data in change.old_value.items() if data}
                else:
                    old_set = set()
                if self._attributes[item]:
                    new_set = {iri for iri, data in self._attributes[item].items() if data}
                else:
                    new_set = set()
                to_be_deleted = old_set - new_set
                to_be_added = new_set - old_set
                if to_be_deleted or to_be_added:
                    sparql = f'WITH {self._graph}:shacl\n'
                    if to_be_deleted:
                        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                        for ov in to_be_deleted:
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res sh:node {ov.toRdf}Shape .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    if to_be_added:
                        sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                        for nv in to_be_added:
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res sh:node {nv.toRdf}Shape .\n'
                        sparql += f'{blank:{indent * indent_inc}}}}\n'
                    sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf}Shape as ?res)\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                    sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
                    sparql += f'{blank:{indent * indent_inc}}}}'
            else:
                sparql = RdfModifyRes.shacl(action=change.action,
                                            graph=self._graph,
                                            owlclass_iri=self._owlclass_iri,
                                            ele=RdfModifyItem(item.value,
                                                              change.old_value,
                                                              self._attributes[item]),
                                            last_modified=self._modified)
            if sparql:
                sparql_list.append(sparql)
        #
        # now process properties
        #
        for propiri, change in self._prop_changeset.items():
            sparql: str | None = None
            if change.action == Action.CREATE:
                if isinstance(self._properties[propiri].prop, Iri):
                    # -> reference to an external, foreign property!
                    sparql = self.__add_new_property_ref_shacl(iri=self._properties[propiri].prop,
                                                               hasprop=self._properties[propiri])
                elif isinstance(self._properties[propiri].prop, PropertyClass):
                    # -> we have the PropertyClass available
                    if self._properties[propiri].prop.from_triplestore:
                        # --> the property is already existing...
                        if self._properties[propiri].prop.internal:
                            raise OldapErrorInconsistency(f'Property "{propiri}" is defined as internal and cannot be reused!')
                        sparql = self.__add_new_property_ref_shacl(
                            iri=self._properties[propiri].prop.property_class_iri,
                            hasprop=self._properties[propiri])
                    else:  # -> it's a new property,  not yet in the triple store. First create it...
                        if self._properties[propiri].prop._force_external:
                            # create a standalone property and the reference it!
                            sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#C\n'
                            sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
                            sparql2 += self._properties[propiri].prop.create_shacl(timestamp=timestamp, indent=2)
                            sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                            sparql_list.append(sparql2)
                            sparql = self.__add_new_property_ref_shacl(
                                iri=self._properties[propiri].prop.property_class_iri,
                                hasprop=self._properties[propiri])
                        else:
                            # Create an internal property (Bnode) and add minCount, maxCount
                            sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#D\n'
                            sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:shacl {{\n'
                            sparql2 += self._properties[propiri].prop.create_shacl(timestamp=timestamp,
                                                                                   owlclass_iri=self._properties[propiri].prop.internal,
                                                                                   haspropdata=self._properties[propiri].haspropdata,
                                                                                   indent=2)
                            sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                            sparql2 += f'{blank:{indent* indent_inc}}}}\n'
                            sparql_list.append(sparql2)
            elif change.action == Action.REPLACE:
                raise OldapErrorInconsistency(f'Property can not be replaced!')
            elif change.action == Action.DELETE:
                if change.old_value.prop.internal:
                    sparql = change.old_value.prop.delete_shacl()
                else:
                    sparql = self.__delete_property_ref_shacl(owlclass_iri=self._owlclass_iri,
                                                              propclass_iri=change.old_value.prop.property_class_iri)

            elif change.action == Action.MODIFY:
                sparql = self._properties[propiri].prop.update_shacl(owlclass_iri=self._owlclass_iri,
                                                                     timestamp=timestamp)
            if sparql:
                sparql_list.append(sparql)

        #
        # Now process HasProperty's
        #
        for propiri, change in self._hp_prop_changeset.items():
            sparql = self._properties[propiri].update_shacl(self._graph, self._owlclass_iri, propiri)
            if sparql:
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self._contributor else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:contributor', self._contributor, self._con.userIri),
                                     last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.shacl(action=Action.REPLACE if self._modified else Action.CREATE,
                                     graph=self._graph,
                                     owlclass_iri=self._owlclass_iri,
                                     ele=RdfModifyItem('dcterms:modified', self._modified, timestamp),
                                     last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def __add_new_property_ref_onto(self, *,
                                    prop: PropertyClass | Iri,
                                    hasprop: HasProperty | None,
                                    indent: int = 0, indent_inc: int = 4) -> str:
        blank = ''
        sparql = f'INSERT DATA {{#E\n'
        sparql += f'    GRAPH {self._graph}:onto {{\n'
        sparql += f'{blank:{indent * indent_inc}}{self._owlclass_iri} rdfs:subClassOf [\n'
        if isinstance(prop, Iri):
            sparql += prop.create_owl_part2(haspropdata=hasprop.haspropdata)
        elif isinstance(prop, PropertyClass):
            sparql += f'{blank:{(indent + 1) * indent_inc}}rdf:type owl:Restriction ;\n'
            sparql += f'{blank:{(indent + 1) * indent_inc}}owl:onProperty {prop.property_class_iri.toRdf}'
            sparql += hasprop.create_owl(indent=1)
        else:
            raise OldapErrorInconsistency(f'Property can not be added!')
        sparql += f'{blank:{indent * indent_inc}}] .\n'
        sparql += f'    }}\n'
        sparql += f'}}\n'
        return sparql

    def __delete_property_ref_owl(self,
                                  owlclass_iri: Iri,
                                  propclass_iri: Iri,
                                  indent: int = 0,
                                  indent_inc: int = 4):
        blank = ''
        sparql = ''
        sparql += f'{blank:{indent * indent_inc}}WITH {self._graph}:onto\n'
        sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri} sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}\n'
        sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}{owlclass_iri}Shape sh:property ?propnode .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode sh:node {self.propclass_iri}Shape .\n'
        sparql += f'{blank:{(indent + 1) * indent_inc}}?propnode ?p ?v .\n'
        sparql += f'{blank:{indent * indent_inc}}}}'
        return sparql

    def __update_owl(self, timestamp: Xsd_dateTime, indent: int = 0, indent_inc: int = 4) -> str:
        if not self._changeset and not self._prop_changeset and not self._hp_prop_changeset:
            return ''
        blank = ''
        sparql_list = []
        #
        # Adapt OWL for changing *attributes* (where only rdfs:subClassOf is relevant...)
        #
        for item, change in self._changeset.items():
            sparql: str | None = None
            #
            # we only need to add rdfs:subClassOf to the ontology – all other attributes are irrelevant
            #
            if item == ResClassAttribute.SUPERCLASS:
                #sparql = f'#\n# OWL: Process attribute "{item.value}" with Action "{change.action.value}"\n#\n'
                sparql = f'WITH {self._graph}:onto\n'
                old_set = set(change.old_value) if change.old_value else set()
                new_set = set(self._attributes[item]) if self._attributes[item] else set()
                to_be_deleted = old_set - new_set
                to_be_added = new_set - old_set
                if to_be_deleted:
                    sparql += f'{blank:{indent * indent_inc}}DELETE {{\n'
                    for ov in to_be_deleted:
                        if isinstance(ov, ResourceClass):
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {ov.owl_class_iri.toRdf} .\n'
                        else:
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {ov.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                if to_be_added:
                    sparql += f'{blank:{indent * indent_inc}}INSERT {{\n'
                    for nv in to_be_added:
                        if isinstance(nv, ResourceClass):
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {nv.owl_class_iri.toRdf} .\n'
                        else:
                            sparql += f'{blank:{(indent + 1) * indent_inc}}?res rdfs:subClassOf {nv.toRdf} .\n'
                    sparql += f'{blank:{indent * indent_inc}}}}\n'
                sparql += f'{blank:{indent * indent_inc}}WHERE {{\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}BIND({self.owl_class_iri.toRdf} as ?res)\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}?res dcterms:modified ?modified .\n'
                sparql += f'{blank:{(indent + 1) * indent_inc}}FILTER(?modified = {self._modified.toRdf})\n'
                sparql += f'{blank:{indent * indent_inc}}}}'
            if sparql:
                sparql_list.append(sparql)
        #
        # process properties
        #
        for propiri, change in self._prop_changeset.items():
            sparql: str | None = None
            if change.action == Action.CREATE:
                if isinstance(self._properties[propiri].prop, Iri):
                    # -> reference to an external, foreign property! prop is Iri!
                    sparql = self.__add_new_property_ref_onto(prop=self._properties[propiri].prop,  # is an Iri
                                                              hasprop=self._properties[propiri])
                elif isinstance(self._properties[propiri].prop, PropertyClass):
                    # -> we have the PropertyClass available
                    if self._properties[propiri].prop.from_triplestore:
                        # --> the property is already existing...
                        if self._properties[propiri].prop.internal:
                            raise OldapErrorInconsistency(
                                f'Property "{propiri}" is defined as internal and cannot be reused!')
                        sparql = self.__add_new_property_ref_onto(
                            prop=self._properties[propiri].prop,  # is a PropertyClass already existing...
                            hasprop=self._properties[propiri])
                    else:  # -> it's a new property,  not yet in the triple store. First create it...
                        # create a standalone property and the reference it!
                        sparql2 = f'{blank:{indent * indent_inc}}INSERT DATA {{#F\n'
                        sparql2 += f'{blank:{(indent + 1) * indent_inc}}GRAPH {self._graph}:onto {{\n'
                        sparql2 += self._properties[propiri].prop.create_owl_part1(timestamp=timestamp, indent=2)
                        sparql2 += f'{blank:{(indent + 1) * indent_inc}}}}\n'
                        sparql2 += f'{blank:{indent * indent_inc}}}}\n'
                        sparql_list.append(sparql2)
                        sparql = self.__add_new_property_ref_onto(
                            prop=self._properties[propiri].prop,  # its a PropertyClass we just created
                            hasprop=self._properties[propiri])
            elif change.action == Action.REPLACE:
                raise OldapErrorInconsistency(f'Property can not be replaced!')
            elif change.action == Action.DELETE:
                if change.old_value.prop.internal:
                    # we delete everything
                    sparql = change.old_value.prop.delete_owl()
                    sparql_list.append(sparql)
                    sparql = change.old_value.prop.delete_owl_subclass_str(owlclass_iri=self._owlclass_iri)
                else:
                    # delete only reference
                    sparql = change.old_value.prop.delete_owl_subclass_str(owlclass_iri=self._owlclass_iri)
            elif change.action == Action.MODIFY:
                sparql = self._properties[propiri].prop.update_owl(owlclass_iri=self._owlclass_iri,
                                                                   timestamp=timestamp)
            if sparql:
                sparql_list.append(sparql)

        #
        # Now process HasProperty's
        #

        for propiri, change in self._hp_prop_changeset.items():
            sparql = self._properties[propiri].update_owl(self._graph, self._owlclass_iri, propiri)
            if sparql:
                sparql_list.append(sparql)

        #
        # Updating the timestamp and contributor ID
        #
        sparql = f'#\n# Update/add dcterms:contributor\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self._contributor else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:contributor', self._contributor, self._con.userIri),
                                    last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = f'#\n# Update/add dcterms:modified\n#\n'
        sparql += RdfModifyRes.onto(action=Action.REPLACE if self._modified else Action.CREATE,
                                    graph=self._graph,
                                    owlclass_iri=self._owlclass_iri,
                                    ele=RdfModifyItem('dcterms:modified', self._modified, timestamp),
                                    last_modified=self._modified)
        sparql_list.append(sparql)

        sparql = " ;\n".join(sparql_list)
        return sparql

    def update(self) -> None:
        #
        # First we check if the logged-in user ("actor") has the permission to update resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__update_shacl(timestamp=timestamp)
        sparql += ' ;\n'
        sparql += self.__update_owl(timestamp=timestamp)
        try:
            self._con.transaction_start()
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            self._con.transaction_update(sparql)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        try:
            modtime_shacl = self.read_modified_shacl(context=context, graph=self._graph)
            modtime_owl = self.read_modified_owl(context=context, graph=self._graph)
        except OldapError as err:
            self._con.transaction_abort()
            raise
        if modtime_shacl == timestamp and modtime_owl == timestamp:
            self._con.transaction_commit()
            self.changeset_clear()
            self._modified = timestamp
            self._contributor = self._con.userIri
        else:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Update of {self._owlclass_iri} failed. {modtime_shacl} {modtime_owl} {timestamp}')
        cache = CacheSingleton()
        cache.set(self._owlclass_iri, self)


    def __delete_shacl(self) -> str:
        sparql = f'#\n# SHALC: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:shacl
        DELETE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            ?rvalue ?pattr ?pval .
            ?z rdf:first ?head ;
            rdf:rest ?tail .
        }}
        WHERE {{
            {self._owlclass_iri}Shape ?rattr ?rvalue .
            OPTIONAL {{
                ?rvalue ?pattr ?pval .
                OPTIONAL {{
                    ?pval rdf:rest* ?z .
                    ?z rdf:first ?head ;
                    rdf:rest ?tail .
                }}
                FILTER(isBlank(?rvalue))
            }}
        }}
        """
        return sparql

    def __delete_owl(self) -> str:
        sparql = f'#\n# OWL: Delete "{self._owlclass_iri}" completely\n#\n'
        sparql += f"""
        WITH {self._graph}:onto
        DELETE {{
            ?prop ?p ?v
        }}
        WHERE {{
            ?prop rdfs:domain {self._owlclass_iri.toRdf} .
            ?prop ?p ?v
        }} ;
        WITH {self._graph}:onto
        DELETE {{
            ?res ?prop ?value .
            ?value ?pp ?vv .
        }}
        WHERE {{
            BIND({self._owlclass_iri.toRdf} AS ?res)
            ?res ?prop ?value
            OPTIONAL {{
                ?value ?pp ?vv
                FILTER(isBlank(?value))
            }}
        }}
        """
        return sparql

    def delete(self) -> None:
        #
        # First we check if the logged-in user ("actor") has the permission to create resource for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OldapErrorNoPermission(message)

        timestamp = datetime.now()
        context = Context(name=self._con.context_name)
        sparql = context.sparql_context
        sparql += self.__delete_shacl()
        sparql += ' ;\n'
        sparql += self.__delete_owl()
        self._con.transaction_start()
        self._con.transaction_update(sparql)
        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:shacl WHERE {{ {self._owlclass_iri}Shape ?p ?v }}"
        jsonobj = self._con.transaction_query(sparql)
        res_shacl = QueryProcessor(context, jsonobj)
        sparql = context.sparql_context
        sparql += f"SELECT * FROM {self._graph}:onto WHERE {{ {self._owlclass_iri.toRdf} ?p ?v }}"
        jsonobj = self._con.transaction_query(sparql)
        res_onto = QueryProcessor(context, jsonobj)
        if len(res_shacl) > 0 or len(res_onto) > 0:
            self._con.transaction_abort()
            raise OldapErrorUpdateFailed(f'Could not delete "{self._owlclass_iri}".')
        else:
            self._con.transaction_commit()
        cache = CacheSingleton()
        cache.delete(self._owlclass_iri)



