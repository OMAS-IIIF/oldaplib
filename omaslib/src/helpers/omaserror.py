from pystrict import strict
from traceback import format_exc

@strict
class OmasError(Exception):
    _message: str

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def __str__(self) -> str:
        return "ERROR: " + self._message + "!\n\n" + format_exc()

    @property
    def message(self) -> str:
        return self._message
