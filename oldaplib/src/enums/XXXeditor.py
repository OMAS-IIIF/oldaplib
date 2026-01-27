from enum import Enum, unique, EnumMeta

from oldaplib.src.helpers.serializer import serializer

class _ValidateEnumMeta(EnumMeta):
    def __call__(cls, value, *args, **kwargs):
        validate = kwargs.pop("validate", True)  # accept validate kwarg
        try:
            return super().__call__(value, *args, **kwargs)
        except ValueError:
            if validate:
                raise
            return None  # or: return a default, or keep ValueError

@unique
@serializer
class Editor(Enum, metaclass=_ValidateEnumMeta):
    AUTO_COMPLETE = "dash:AutoCompleteEditor"
    BLANK_NODE = "dash:BlankNodeEditor"
    BOOLEAN_SELECT = "dash:BooleanSelectEditor"
    DATE_PICKER = "dash:DatePickerEditor"
    DATE_TIME_PICKER = "dash:DateTimePickerEditor"
    DETAILS = "dash:DetailsEditor"
    ENUM_SELECT = "dash:EnumSelectEditor"
    INSTANCES_SELECT = "dash:InstancesSelectEditor"
    RICH_TEXT_EDITOR = "dash:RichTextEditor"
    SUB_CLASS = "dash:SubClassEditor"
    TEXT_AREA = "dash:TextAreaEditor"
    TEXT_AREA_WITH_LANG = "dash:TextAreaWithLangEditor"
    TEXT_FIELD = "dash:TextFieldEditor"
    TEXT_FIELD_WITH_LANG = "dash:TextFieldWithLangEditor"
    URI = "dash:UriEditor"



    @classmethod
    def _missing_(cls, value):
        if not isinstance(value, str):
            return None

        v = value.strip()

        # 1) normalize dash: prefix
        if not v.startswith("dash:"):
            v = f"dash:{v}"

        # 2) try value match (dash:TextAreaEditor)
        for member in cls:
            if member.value == v:
                return member

        # 3) try enum-name match (AUTO_COMPLETE)
        key = v.removeprefix("dash:").replace("-", "_").upper()
        if key in cls.__members__:
            return cls[key]

        return None

    @classmethod
    def get_editor_by_name(cls, name):
        if not name.startswith("dash:"):
            name = f"dash:{name}"
        for editor in cls:
            if editor.name == name:
                return editor
        return None

    @property
    def toRdf(self):
        return self.value

    def _as_dict(self):
        return {"value": self.value }


if __name__ == "__main__":
    print(Editor(value="dash:TextFieldWithLangEditor"))

