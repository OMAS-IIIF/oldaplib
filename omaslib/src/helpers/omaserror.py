"""
This module implements the error clasees
"""
from pystrict import strict
from traceback import format_exc

@strict
class OmasError(Exception):
    """
    No special needs besides a special class for errors in OMAS
    """
    pass


@strict
class OmasErrorValue(OmasError):
    """
    Raised when an invalid value is passed/processed
    """
    pass


@strict
class OmasErrorType(OmasError):
    """
    Raised when an invalid value is passed/processed
    """
    pass


@strict
class OmasErrorKey(OmasError):
    pass


@strict
class OmasErrorNotFound(OmasError):
    """
    Raised when something was not found
    """
    pass


@strict
class OmasErrorAlreadyExists(OmasError):
    """
    Raised when something should be created which already exists
    """
    pass


@strict
class OmasErrorInconsistency(OmasError):
    """
    Raised when an inconsistency is encountered
    """
    pass


@strict
class OmasErrorUpdateFailed(OmasError):
    """
    Updating failed for some reason
    """
    pass

@strict
class OmasErrorNoPermission(OmasError):
    pass

@strict
class OmasErrorImmutable(OmasError):
    pass

@strict
class OmasErrorIndex(OmasError):
    pass
