from pystrict import strict
from traceback import format_exc

@strict
class OmasError(Exception):
    """
    No special needs besides a special class for errors in OMAS
    """
    pass
