from pystrict import strict
from traceback import format_exc

@strict
class OmasError(Exception):
    """
    No special needs besides a special class for errors in OMAS
    """
    pass


@strict
class OmasValueError(OmasError):
    pass


@strict
class OmasErrorNotFound(OmasError):
    pass


@strict
class OmasErrorAlreadyExists(OmasError):
    pass


@strict
class OmasErrorInconsistency(OmasError):
    pass


@strict
class OmasErrorUpdateFailed(OmasError):
    pass
