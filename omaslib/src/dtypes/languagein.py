from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasErrorValue


class LanguageIn(set):
    """
    This class implements the SHACL sh:languageIn datatype. It completely validates the input.
    If the validations failes, an OmasErrorValue is raised.
    """

    def __init__(self, *args):
        __data: set[Language]
        """
        Constructor for the LanguageIn
        :param args: Either the languages as 2-letter short strings, or a set of
        """
        self.__data: set[Language] = set()
        try:
            if len(args) > 1:
                for arg in args:
                    if isinstance(arg, Language):
                        self.__data.add(arg)
                    elif isinstance(arg, str):
                        self.__data.add(Language[arg.upper()])
            elif len(args) == 1:
                if isinstance(args[0], Language):
                    self.__data.add(args[0])
                elif isinstance(args[0], str):
                    self.__data.add(Language[args[0].upper()])
                else:
                    try:
                        iter(args[0])
                    except:
                        raise OmasErrorValue("Parameter must be iterable.")
                    for arg in args[0]:
                        if isinstance(arg, Language):
                            self.__data.add(arg)
                        elif isinstance(arg, str):
                            self.__data.add(Language[arg.upper()])
        except KeyError:
            raise OmasErrorValue("Non valid language in set.")

    def __str__(self):
        langlist = {f'"{x.name.lower()}"' for x in self}
        return f'({", ".join(langlist)})'

    def __repr__(self):
        langlist = {f'"{x.name.lower()}"^^xsd:string' for x in self}
        return 'LanguageIn(' + ", ".join(langlist) + ')'

    @property
    def toRdf(self) -> str:
        langlist = {f'"{x.name.lower()}"^^xsd:string' for x in self}
        return f'({" ".join(langlist)})'

    def _as_dict(self):
        return {'value': [x for x in self.__data]}

    @property
    def value(self) -> set[Language]:
        return self.__data
