from typing import Self, Dict

from pystrict import strict

from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.xsd.xsd_anyuri import Xsd_anyURI
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName


#@strict
@serializer
class NamespaceIRI(Xsd_anyURI):
    """
    Represents an IRI that denotes a namespace.

    A NamespaceIRI is a specialized form of `Xsd_anyURI` that ensures the IRI
    ends with a fragment separator, either a `"#"` or a `"/"`. This class validates the IRI
    structure during instantiation and provides utility methods for usage.

    :ivar value: The IRI value that this instance represents.
    :type value: str
    """

    def __init__(self, value: Self | Xsd_anyURI | str, validate: bool = False):
        """
        Constructor for the NamespaceIRI class.

        This constructor initializes a NamespaceIRI object with the given value and
        validation flag. The value represents the namespace and can be a string,
        `NamespaceIRI` object, or `Xsd_anyURI`. The validate flag determines whether
        validation is performed on the provided value. If the value does not comply
        with the expected format, an exception is raised. NamespaceIRI instances must
        always end with '/' or '#'.

        :param value: A string, `NamespaceIRI` object, or `Xsd_anyURI` representing
            the namespace.
        :param validate: A boolean flag indicating whether to validate the given value.
        :raises OldapErrorValue: If the provided value does not end with '/' or '#'.
        """
        super().__init__(value, validate)
        if not self._append_allowed:
            raise OldapErrorValue("NamespaceIRI must end with '/' or '#'!")

    def __repr__(self) -> str:
        return f'NamespaceIRI("{self.value}")'

    def __add__(self, other: str) -> Xsd_anyURI:
        return Xsd_anyURI(self._value + other)


    @property
    def toRdf(self) -> str:
        return f'<{self._value}>'

    def expand(self, name: Xsd_NCName | str):
        """
        Expands the current namespace URI by appending a name to it, separated by a '/'
        and followed by a '#'. The expanded URI is then returned as a new NamespaceIRI
        object.

        :param name: An object of type `Xsd_NCName` whose value will be appended to
            the current namespace's URI.
        :return: A new NamespaceIRI object with the expanded URI.
        """
        if not isinstance(name, Xsd_NCName):
            name = Xsd_NCName(name)
        return NamespaceIRI(self.value[:-1] + '/' + name.value + '#')


if __name__ == '__main__':
    ns = NamespaceIRI('http://example.com/ns/')
    print(ns)
    print(ns + 'foo')
    print(ns.expand('foo'))
    print(ns.toRdf)

