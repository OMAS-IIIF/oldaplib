"""
This module implements the error clasees
"""
#from pystrict import strict
from traceback import format_exc

#@strict
class OldapError(Exception):
    """
    No special needs besides a special class for errors in OMAS
    """
    pass


#@strict
class OldapErrorValue(OldapError):
    """
    Raised when an invalid value is passed/processed
    """
    pass


#@strict
class OldapErrorType(OldapError):
    """
    Raised when an invalid value is passed/processed
    """
    pass


#@strict
class OldapErrorKey(OldapError):
    pass


#@strict
class OldapErrorNotFound(OldapError):
    """
    Raised when something was not found
    """
    pass


#@strict
class OldapErrorAlreadyExists(OldapError):
    """
    Raised when something should be created which already exists
    """
    pass


#@strict
class OldapErrorInconsistency(OldapError):
    """
    Raised when an inconsistency is encountered
    """
    pass


#@strict
class OldapErrorUpdateFailed(OldapError):
    """
    Updating failed for some reason
    """
    pass

#@strict
class OldapErrorNoPermission(OldapError):
    pass

#@strict
class OldapErrorImmutable(OldapError):
    pass

#@strict
class OldapErrorIndex(OldapError):
    pass

#@strict
class OldapErrorInUse(OldapError):
    pass

class OldapErrorNotImplemented(OldapError):
    pass


class OldapErrorConfiguration(OldapError):
    """Raised when required OLDAP runtime configuration is missing or invalid."""


class OldapErrorToken(OldapError):
    """Base class for purpose-specific token validation failures."""


class OldapErrorTokenExpired(OldapErrorToken):
    """Raised when a correctly structured token has expired."""


class OldapErrorTokenInvalid(OldapErrorToken):
    """Raised when a token cannot be trusted or violates its claim contract."""

