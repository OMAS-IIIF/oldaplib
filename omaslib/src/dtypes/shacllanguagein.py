from omaslib.src.enums.language import Language
from omaslib.src.helpers.omaserror import OmasErrorValue


class ShaclLanguageIn(set):
    """
    This class implements the SHACL sh:languageIn datatype. It completely validates the input.
    If the validations failes, an OmasErrorValue is raised.
    """

    def __init__(self, *args):
        """
        Constructor for the LanguageIn
        :param args: Either the languages as 2-letter short strings, or a set of
        """
        elements = set()
        try:
            if len(args) > 1:
                for arg in args:
                    if isinstance(arg, Language):
                        elements.add(arg)
                    elif isinstance(arg, str):
                        elements.add(Language[arg.upper()])
            elif len(args) == 1:
                if isinstance(args[0], Language):
                    elements.add(args[0])
                elif isinstance(args[0], str):
                    elements.add(Language[args[0].upper()])
                else:
                    try:
                        iter(args[0])
                    except:
                        raise OmasErrorValue("Parameter must be iterable.")
                    for arg in args[0]:
                        if isinstance(arg, Language):
                            elements.add(arg)
                        elif isinstance(arg, str):
                            elements.add(Language[arg.upper()])
        except KeyError:
            raise OmasErrorValue("Non valid language in set.")
        super().__init__(elements)

    def __str__(self):
        l = {f'"{x.name.lower()}"' for x in self}
        return '(' + ", ".join(l) + ')'

    def __repr__(self):
        l = {f'"{x.name.lower()}"^^xsd:string' for x in self}
        return '(' + " ".join(l) + ')'

    def _as_dict(self):
        pass
