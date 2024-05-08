from dataclasses import dataclass
from enum import Enum, unique
from functools import partial
from typing import Self

from omaslib.src.enums.action import Action
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.context import Context
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.omaserror import OmasErrorValue, OmasErrorInconsistency, OmasErrorImmutable, OmasError, OmasErrorNoPermission
from omaslib.src.iconnection import IConnection
from omaslib.src.model import Model
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_datetime import Xsd_dateTime
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName

OldapListAttrTypes = LangString | Iri | None

@dataclass
class OldapListAttrChange:
    """
    A dataclass used to represent the changes made to a field.
    """
    old_value: OldapListAttrTypes
    action: Action


@unique
class OldapListAttr(Enum):
    """
    This enum class represents the fields used in the project model
    """
    OLDAPLIST_IRI = 'omas:oldapListIri'  # virtual property, repents the RDF subject
    PREF_LABEL = 'skos:prefLabel'
    DEFINITION = 'skos:definition'

class OldapList(Model):

    __datatypes = {
        OldapListAttr.OLDAPLIST_IRI: Iri,
        OldapListAttr.PREF_LABEL: LangString,
        OldapListAttr.DEFINITION: LangString,
    }

    __creator: Iri | None
    __created: Xsd_dateTime | None
    __contributor: Iri | None
    __modified: Xsd_dateTime | None

    __fields: dict[OldapListAttr, OldapListAttrTypes]

    __changeset: dict[OldapListAttr, OldapListAttrChange]

    def __init__(self, *,
                 con: IConnection,
                 creator: Iri | None = None,
                 created: Xsd_dateTime | None = None,
                 contributor: Iri | None = None,
                 modified: Xsd_dateTime | None = None,
                 oldapListIri: Iri | str | None = None,
                 prefLabel: LangString | str | None = None,
                 definition: LangString | str | None = None):
        super().__init__(con)
        self.__creator = creator if creator is not None else con.userIri
        if created and not isinstance(created, Xsd_dateTime):
            raise OmasErrorValue(f'Created must be "Xsd_dateTime", not "{type(created)}".')
        self.__created = created
        self.__contributor = contributor if contributor is not None else con.userIri
        if modified and not isinstance(modified, Xsd_dateTime):
            raise OmasErrorValue(f'Modified must be "Xsd_dateTime", not "{type(modified)}".')
        self.__modified = modified
        self.__attributes = {}

        if oldapListIri:
            if not isinstance(oldapListIri, Iri):
                self.__attributes[OldapListAttr.OLDAPLIST_IRI] = Iri(oldapListIri)
            else:
                self.__attributes[OldapListAttr.OLDAPLIST_IRI] = oldapListIri
        else:
            self.__attributes[OldapListAttr.OLDAPLIST_IRI] = Iri()

        self.__attributes[OldapListAttr.PREF_LABEL] = prefLabel if isinstance(prefLabel, LangString) else LangString(prefLabel)
        self.__attributes[OldapListAttr.PREF_LABEL].set_notifier(self.notifier, Iri(OldapListAttr.PREF_LABEL.value))
        self.__attributes[OldapListAttr.DEFINITION] = definition if isinstance(definition, LangString) else LangString(definition)
        self.__attributes[OldapListAttr.DEFINITION].set_notifier(self.notifier, Iri(OldapListAttr.DEFINITION.value))

        #
        # Consistency checks
        #
        if not self.__attributes[OldapListAttr.PREF_LABEL]:
            raise OmasErrorInconsistency(f'Project must have at least one skos:prefLabel, none given.')

        #
        # create all the attributes of the class according to the OldapListAttr definition
        #
        for attr in OldapListAttr:
            prefix, name = attr.value.split(':')
            setattr(OldapList, name, property(
                partial(OldapList.__get_value, field=attr),
                partial(OldapList.__set_value, field=attr),
                partial(OldapList.__del_value, field=attr)))
        self.__changeset = {}

    def check_for_permissions(self) -> (bool, str):
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        actor = self._con.userdata
        sysperms = actor.inProject.get(Iri('omas:SystemProject'))
        if sysperms and AdminPermission.ADMIN_OLDAP in sysperms:
            #
            # user has root privileges!
            #
            return True, "OK – IS ROOT"
        else:
            if len(self.inProject) == 0:
                return False, f'Actor has no ADMIN_LISTS permission for user {self.userId}.'
            allowed: list[Iri] = []
            for proj in self.inProject.keys():
                if actor.inProject.get(proj) is None:
                    return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
                else:
                    if AdminPermission.ADMIN_LISTS not in actor.inProject.get(proj):
                        return False, f'Actor has no ADMIN_LISTS permission for project {proj}'
            return True, "OK..."

    def __get_value(self: Self, field: OldapListAttr) -> OldapListAttrTypes | None:
        tmp = self.__attributes.get(field)
        if not tmp:
            return None
        return tmp

    def __set_value(self: Self, value: OldapListAttrTypes, field: OldapListAttr) -> None:
        self.__change_setter(field, value)

    def __del_value(self: Self, field: OldapListAttr) -> None:
        del self.__attributes[field]

    def __change_setter(self, attr: OldapListAttr, value: OldapListAttrTypes) -> None:
        if self.__attributes.get(attr) == value:
            return
        if attr == OldapListAttr.OLDAPLIST_IRI:
            raise OmasErrorImmutable(f'Field {attr.value} is immutable.')
        if self.__fields.get(attr) is None:
            if self.__changeset.get(attr) is None:
                self.__changeset[attr] = OldapListAttrChange(None, Action.CREATE)
        else:
            if value is None:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListAttrChange(self.__fields[attr], Action.DELETE)
            else:
                if self.__changeset.get(attr) is None:
                    self.__changeset[attr] = OldapListAttrChange(self.__fields[attr], Action.REPLACE)
        if value is None:
            del self.__fields[attr]
        else:
            if not isinstance(value, self.__datatypes[attr]):
                self.__fields[attr] = self.__datatypes[attr](value)
            else:
                self.__fields[attr] = value

    def __str__(self):
        res = f'OldapList: {self.__attributes[OldapListAttr.OLDAPLIST_IRI]}\n'\
              f'  Creation: {self.__created} by {self.__creator}\n'\
              f'  Modified: {self.__modified} by {self.__contributor}\n'\
              f'  Preferred label: {self.__attributes.get(OldapListAttr.PREF_LABEL)}\n'\
              f'  Definition: {self.__attributes.get(OldapListAttr.DEFINITION)}'
        return res

    @property
    def creator(self) -> Iri | None:
        """
        The creator of the OldapList.
        :return: Iri of the creator of the OldapList.
        :rtype: Iri | None
        """
        return self.__creator

    @property
    def created(self) -> Xsd_dateTime | None:
        """
        The creation date of the OldapList.
        :return: Creation date of the OldapList.
        :rtype: Xsd_dateTime | None
        """
        return self.__created

    @property
    def contributor(self) -> Iri | None:
        """
        The contributor of the OldapList as Iri.
        :return: Iri of the contributor of the OldapList.
        :rtype: Iri | None
        """
        return self.__contributor

    @property
    def modified(self) -> Xsd_dateTime | None:
        """
        Modification date of the OldapList.
        :return: Modification date of the OldapList.
        :rtype: Xsd_dateTime | None
        """
        return self.__modified

    @property
    def changeset(self) -> dict[OldapListAttr, OldapListAttrChange]:
        """
        Return the changeset, that is dicst with information about all properties that have benn changed.
        This method is only for internal use or debugging...
        :return: A dictionary of all changes
        :rtype: Dict[ProjectAttr, ProjectAttrChange]
        """
        return self.__changeset

    def clear_changeset(self) -> None:
        """
        Clear the changeset. This method is only for internal use or debugging...
        :return: None
        """
        self.__changeset = {}

    def notifier(self, attrname: Iri) -> None:
        """
        This method is called when a field is being changed.
        :param fieldname: Fieldname of the field being modified
        :return: None
        """
        attr = OldapListAttr(attrname)
        self.__changeset[attr] = OldapListAttrChange(self.__fields[attr], Action.MODIFY)

    @classmethod
    def read(cls, con: IConnection, projectIri: Iri | str) -> Self:
        return cls(con=con)

    @staticmethod
    def search(con: IConnection,
               prefLabel: str | None = None,
               comment: str | None = None) -> list[Iri]:
        return []

    def create(self, indent: int = 0, indent_inc: int = 4) -> None:
        if self._con is None:
            raise OmasError("Cannot create: no connection")
        #
        # First we check if the logged-in user ("actor") has the permission to create a user for
        # the given project!
        #
        result, message = self.check_for_permissions()
        if not result:
            raise OmasErrorNoPermission(message)

        timestamp = Xsd_dateTime.now()
        indent: int = 0
        indent_inc: int = 4

        context = Context(name=self._con.context_name)


