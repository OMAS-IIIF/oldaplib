from omaslib.src.helpers.omaserror import OmasError


class SemanticVersion:
    __major: int
    __minor: int
    __patch: int

    def __init__(self, major: int = 1, minor: int = 0, patch: int = 0):
        self.__major = major
        self.__minor = minor
        self.__patch = patch

    def __str__(self):
        return f"{self.__major}.{self.__minor}.{self.__patch}"

    @classmethod
    def fromString(cls, versionstring: str) -> 'SemanticVersion':
        try:
            major, minor, patch = versionstring.split(".")
            cls.__major = int(major)
            cls.__minor = int(minor)
            cls.__patch = int(patch)
        except ValueError as err:
            raise OmasError(f'Invalid version string: "{versionstring}": {err}')

    def increment_patch(self):
        self.__patch += 1

    def increment_minor(self):
        self.__minor += 1
        self.__patch = 0

    def increment_major(self):
        self.__major += 1
        self.__minor = 0
        self.__patch = 0

