"""Typed authorization context and purpose-specific OLDAP JWT codecs.

This module deliberately contains only the token-domain primitives shared by
``oldaplib`` and ``oldap-api``. HTTP cookie handling and endpoint behavior
remain responsibilities of the API layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Protocol, TYPE_CHECKING
from uuid import UUID, uuid4

import jwt

from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import (
    OldapError,
    OldapErrorConfiguration,
    OldapErrorTokenExpired,
    OldapErrorTokenInvalid,
)
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

if TYPE_CHECKING:
    from oldaplib.src.userdataclass import UserData


ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
MEDIA_TOKEN_TYPE = "media"
JWT_ALGORITHM = "HS256"


class AuthorizationSubject(Protocol):
    """Structural input contract for authorization-context creation."""

    @property
    def userIri(self) -> Iri: ...

    @property
    def userId(self) -> Xsd_NCName: ...

    @property
    def inProject(self) -> InProjectClass | None: ...

    @property
    def hasRole(self) -> ObservableDict | None: ...


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Minimal identity and permission data required for authorization.

    The context intentionally excludes credentials, profile attributes,
    password-reset state, arbitrary user properties, and ``authVersion``.
    Instances reconstructed from access tokens therefore have the same shape
    as contexts created immediately after credential authentication.
    """

    userIri: Iri
    userId: Xsd_NCName
    inProject: InProjectClass
    hasRole: ObservableDict

    @classmethod
    def from_user_data(cls, userdata: UserData) -> AuthorizationContext:
        """Create an authorization context from a fully loaded user record."""
        return cls.from_user(userdata)

    @classmethod
    def from_user(cls, user: AuthorizationSubject) -> AuthorizationContext:
        """Create a context from a user-like OLDAP model object.

        Both :class:`UserData` and :class:`User` expose the identity and
        permission attributes needed here. Keeping this conversion in the
        authentication domain avoids duplicating claim shaping in the API.
        """
        roles = user.hasRole.copy() if user.hasRole else ObservableDict()
        projects = user.inProject.copy() if user.inProject else InProjectClass()
        return cls(
            userIri=Iri(user.userIri),
            userId=Xsd_NCName(user.userId),
            inProject=projects,
            hasRole=roles,
        )

    def to_claims(self) -> dict[str, dict[str, Any]]:
        """Return the explicit, JSON-compatible authorization claim payload."""
        projects = {
            str(project): sorted(permission.value for permission in permissions)
            for project, permissions in self.inProject.items()
        }
        roles = {
            str(role): str(permission.value) if permission is not None else None
            for role, permission in self.hasRole.items()
        }
        return {"inProject": projects, "hasRole": roles}

    @classmethod
    def from_claims(
        cls,
        *,
        user_id: Any,
        user_iri: Any,
        claims: Any,
    ) -> AuthorizationContext:
        """Validate JWT authorization claims and reconstruct typed values.

        Raises:
            OldapErrorTokenInvalid: If identity or authorization claims do not
                have the required shape or contain invalid OLDAP values.
        """
        try:
            if not isinstance(user_id, str) or not isinstance(user_iri, str):
                raise TypeError("Identity claims must be strings")
            if not isinstance(claims, Mapping):
                raise TypeError("The auth claim must be an object")
            projects_claim = claims.get("inProject")
            roles_claim = claims.get("hasRole")
            if not isinstance(projects_claim, Mapping) or not isinstance(roles_claim, Mapping):
                raise TypeError("Authorization collections must be objects")

            projects: dict[str, set[str]] = {}
            for project, permissions in projects_claim.items():
                if not isinstance(project, str) or not isinstance(permissions, list):
                    raise TypeError("Invalid inProject claim")
                if any(not isinstance(permission, str) for permission in permissions):
                    raise TypeError("Project permissions must be strings")
                projects[project] = set(permissions)

            roles: dict[Xsd_QName, Xsd_QName | None] = {}
            for role, permission in roles_claim.items():
                if not isinstance(role, str) or (permission is not None and not isinstance(permission, str)):
                    raise TypeError("Invalid hasRole claim")
                roles[Xsd_QName(role, validate=True)] = (
                    Xsd_QName(permission, validate=True) if permission is not None else None
                )

            return cls(
                userIri=Iri(user_iri, validate=True),
                userId=Xsd_NCName(user_id, validate=True),
                inProject=InProjectClass(projects, validate=True),
                hasRole=ObservableDict(roles),
            )
        except OldapErrorTokenInvalid:
            raise
        except (OldapError, TypeError, ValueError) as err:
            raise OldapErrorTokenInvalid("Invalid access-token authorization claims") from err


@dataclass(frozen=True, slots=True)
class RefreshTokenClaims:
    """Validated identity and revocation state carried by a refresh token."""

    userId: Xsd_NCName
    authVersion: int
    issuedAt: datetime
    expiresAt: datetime
    tokenId: str


@dataclass(frozen=True, slots=True)
class TokenSettings:
    """Configuration for OLDAP access, refresh, and media JWTs.

    Secrets have no defaults and are checked only when the corresponding token
    operation is used. This lets access-token consumers run without gaining
    access to the refresh-token signing secret.
    """

    access_secret: str | None = None
    refresh_secret: str | None = None
    media_secret: str | None = None
    issuer: str = "https://oldap.org"
    audience: str = "oldap-api"
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 1_209_600
    media_ttl_seconds: int = 3_600

    def __post_init__(self) -> None:
        """Reject invalid settings independently of their configuration source."""
        if not isinstance(self.issuer, str) or not self.issuer.strip():
            raise OldapErrorConfiguration("OLDAP_JWT_ISSUER must not be empty")
        if not isinstance(self.audience, str) or not self.audience.strip():
            raise OldapErrorConfiguration("OLDAP_JWT_AUDIENCE must not be empty")
        if (
            isinstance(self.access_ttl_seconds, bool)
            or not isinstance(self.access_ttl_seconds, int)
            or self.access_ttl_seconds <= 0
        ):
            raise OldapErrorConfiguration("OLDAP_ACCESS_TOKEN_TTL_SECONDS must be positive")
        if (
            isinstance(self.refresh_ttl_seconds, bool)
            or not isinstance(self.refresh_ttl_seconds, int)
            or self.refresh_ttl_seconds <= 0
        ):
            raise OldapErrorConfiguration("OLDAP_REFRESH_TOKEN_TTL_SECONDS must be positive")
        if (
            isinstance(self.media_ttl_seconds, bool)
            or not isinstance(self.media_ttl_seconds, int)
            or self.media_ttl_seconds <= 0
        ):
            raise OldapErrorConfiguration("OLDAP_MEDIA_TOKEN_TTL_SECONDS must be positive")
        configured_secrets = [
            secret
            for secret in (self.access_secret, self.refresh_secret, self.media_secret)
            if secret
        ]
        if len(configured_secrets) != len(set(configured_secrets)):
            raise OldapErrorConfiguration("Access, refresh, and media JWT secrets must be distinct")

    @classmethod
    def from_environment(cls) -> TokenSettings:
        """Load token configuration from the documented environment variables."""
        return cls(
            access_secret=os.getenv("OLDAP_ACCESS_JWT_SECRET"),
            refresh_secret=os.getenv("OLDAP_REFRESH_JWT_SECRET"),
            media_secret=os.getenv("OLDAP_MEDIA_JWT_SECRET"),
            issuer=os.getenv("OLDAP_JWT_ISSUER", "https://oldap.org"),
            audience=os.getenv("OLDAP_JWT_AUDIENCE", "oldap-api"),
            access_ttl_seconds=cls._read_positive_int("OLDAP_ACCESS_TOKEN_TTL_SECONDS", 900),
            refresh_ttl_seconds=cls._read_positive_int("OLDAP_REFRESH_TOKEN_TTL_SECONDS", 1_209_600),
            media_ttl_seconds=cls._read_positive_int("OLDAP_MEDIA_TOKEN_TTL_SECONDS", 3_600),
        )

    @staticmethod
    def _read_positive_int(name: str, default: int) -> int:
        raw_value = os.getenv(name)
        try:
            value = default if raw_value is None else int(raw_value)
        except ValueError as err:
            raise OldapErrorConfiguration(f"{name} must be a positive integer") from err
        if value <= 0:
            raise OldapErrorConfiguration(f"{name} must be a positive integer")
        return value

    @property
    def access_audience(self) -> str:
        """Return the audience reserved for access tokens."""
        return self.audience

    @property
    def refresh_audience(self) -> str:
        """Return the audience reserved for refresh tokens."""
        return f"{self.audience}-refresh"

    @property
    def media_audience(self) -> str:
        """Return the audience reserved for media capability tokens."""
        return f"{self.audience}-media"

    def require_access_secret(self) -> str:
        """Return the access secret or fail closed if it is not configured."""
        return self._require_secret(self.access_secret, "OLDAP_ACCESS_JWT_SECRET")

    def require_refresh_secret(self) -> str:
        """Return the refresh secret or fail closed if it is not configured."""
        return self._require_secret(self.refresh_secret, "OLDAP_REFRESH_JWT_SECRET")

    def require_media_secret(self) -> str:
        """Return the media secret or fail closed if it is not configured."""
        return self._require_secret(self.media_secret, "OLDAP_MEDIA_JWT_SECRET")

    @staticmethod
    def _require_secret(secret: str | None, variable: str) -> str:
        if not isinstance(secret, str) or not secret.strip():
            raise OldapErrorConfiguration(f"Required token secret {variable} is not configured")
        if len(secret.encode("utf-8")) < 32:
            raise OldapErrorConfiguration(f"{variable} must contain at least 32 bytes")
        return secret


class TokenCodec:
    """Issue and validate access, refresh, and media JWTs with strict separation."""

    def __init__(self, settings: TokenSettings | None = None) -> None:
        self._settings = settings or TokenSettings.from_environment()

    @classmethod
    def from_environment(cls) -> TokenCodec:
        """Construct a codec using the current process environment."""
        return cls(TokenSettings.from_environment())

    @property
    def settings(self) -> TokenSettings:
        """Return the immutable token settings used by this codec."""
        return self._settings

    def issue_access_token(
        self,
        context: AuthorizationContext,
        *,
        now: datetime | None = None,
    ) -> str:
        """Create a short-lived access token for an authorization context."""
        issued_at = self._normalized_time(now)
        payload = {
            "typ": ACCESS_TOKEN_TYPE,
            "sub": str(context.userId),
            "userIri": str(context.userIri),
            "iss": self._settings.issuer,
            "aud": self._settings.access_audience,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=self._settings.access_ttl_seconds)).timestamp()),
            "jti": str(uuid4()),
            "auth": context.to_claims(),
        }
        return jwt.encode(payload, self._settings.require_access_secret(), algorithm=JWT_ALGORITHM)

    def decode_access_token(self, token: str) -> AuthorizationContext:
        """Validate an access token and return its typed authorization context."""
        payload = self._decode(
            token=token,
            secret=self._settings.require_access_secret(),
            issuer=self._settings.issuer,
            audience=self._settings.access_audience,
            token_type=ACCESS_TOKEN_TYPE,
            required_claims=("userIri", "auth"),
        )
        return AuthorizationContext.from_claims(
            user_id=payload["sub"],
            user_iri=payload["userIri"],
            claims=payload["auth"],
        )

    def issue_refresh_token(
        self,
        user_id: str | Xsd_NCName,
        auth_version: int,
        *,
        now: datetime | None = None,
    ) -> str:
        """Create an absolute-lifetime refresh token for a user version."""
        if isinstance(auth_version, bool) or not isinstance(auth_version, int) or auth_version < 0:
            raise OldapErrorTokenInvalid("auth_version must be a non-negative integer")
        normalized_user_id = Xsd_NCName(user_id, validate=True)
        issued_at = self._normalized_time(now)
        payload = {
            "typ": REFRESH_TOKEN_TYPE,
            "sub": str(normalized_user_id),
            "authVersion": auth_version,
            "iss": self._settings.issuer,
            "aud": self._settings.refresh_audience,
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=self._settings.refresh_ttl_seconds)).timestamp()),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, self._settings.require_refresh_secret(), algorithm=JWT_ALGORITHM)

    def decode_refresh_token(self, token: str) -> RefreshTokenClaims:
        """Validate a refresh token and return its typed stable claims."""
        payload = self._decode(
            token=token,
            secret=self._settings.require_refresh_secret(),
            issuer=self._settings.issuer,
            audience=self._settings.refresh_audience,
            token_type=REFRESH_TOKEN_TYPE,
            required_claims=("authVersion",),
        )
        try:
            auth_version = payload["authVersion"]
            if isinstance(auth_version, bool) or not isinstance(auth_version, int) or auth_version < 0:
                raise TypeError("authVersion must be a non-negative integer")
            user_id = Xsd_NCName(payload["sub"], validate=True)
            token_id = payload["jti"]
            UUID(token_id)
            return RefreshTokenClaims(
                userId=user_id,
                authVersion=auth_version,
                issuedAt=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expiresAt=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                tokenId=token_id,
            )
        except (TypeError, ValueError, KeyError, OldapError) as err:
            raise OldapErrorTokenInvalid("Invalid refresh-token claims") from err

    def issue_media_token(
        self,
        subject: str | Xsd_NCName,
        claims: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> str:
        """Create a short-lived media capability token.

        Args:
            subject: User identifier receiving the media capability.
            claims: Asset-specific claims such as ``assetId``, ``path``, and
                derivative/original names. Registered JWT claims are managed by
                the codec and may not be overridden.
            now: Optional timezone-aware issuance time for deterministic tests.

        Returns:
            A signed JWT with the dedicated media type, audience, and secret.

        Raises:
            OldapErrorTokenInvalid: If custom claims are malformed or attempt
                to override registered claims.
            OldapErrorConfiguration: If the media secret is unavailable.
        """
        if not isinstance(claims, Mapping):
            raise OldapErrorTokenInvalid("Media token claims must be an object")
        reserved = {"typ", "sub", "iss", "aud", "iat", "exp", "jti"}
        if reserved.intersection(claims):
            raise OldapErrorTokenInvalid("Media token claims contain reserved names")
        try:
            normalized_subject = Xsd_NCName(subject, validate=True)
        except OldapError as err:
            raise OldapErrorTokenInvalid("Invalid media-token subject") from err
        issued_at = self._normalized_time(now)
        payload = dict(claims)
        payload.update(
            {
                "typ": MEDIA_TOKEN_TYPE,
                "sub": str(normalized_subject),
                "iss": self._settings.issuer,
                "aud": self._settings.media_audience,
                "iat": int(issued_at.timestamp()),
                "exp": int(
                    (
                        issued_at
                        + timedelta(seconds=self._settings.media_ttl_seconds)
                    ).timestamp()
                ),
                "jti": str(uuid4()),
            }
        )
        return jwt.encode(
            payload,
            self._settings.require_media_secret(),
            algorithm=JWT_ALGORITHM,
        )

    def decode_media_token(self, token: str) -> dict[str, Any]:
        """Validate and return a media capability token's claims."""
        return self._decode(
            token=token,
            secret=self._settings.require_media_secret(),
            issuer=self._settings.issuer,
            audience=self._settings.media_audience,
            token_type=MEDIA_TOKEN_TYPE,
            required_claims=(),
        )

    @staticmethod
    def _normalized_time(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            raise ValueError("Token timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _decode(
        *,
        token: str,
        secret: str,
        issuer: str,
        audience: str,
        token_type: str,
        required_claims: tuple[str, ...],
    ) -> dict[str, Any]:
        required = ["typ", "sub", "iss", "aud", "iat", "exp", "jti", *required_claims]
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[JWT_ALGORITHM],
                audience=audience,
                issuer=issuer,
                options={"require": required},
            )
        except jwt.ExpiredSignatureError as err:
            raise OldapErrorTokenExpired("Token has expired") from err
        except jwt.InvalidTokenError as err:
            raise OldapErrorTokenInvalid("Invalid token") from err

        if payload.get("typ") != token_type:
            raise OldapErrorTokenInvalid(f"Expected a {token_type} token")
        try:
            if not isinstance(payload["sub"], str):
                raise TypeError("Token subject must be a string")
            if payload["aud"] != audience:
                raise TypeError("Token audience must be purpose-specific")
            for timestamp_claim in ("iat", "exp"):
                timestamp = payload[timestamp_claim]
                if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                    raise TypeError(f"{timestamp_claim} must be an integer timestamp")
            UUID(payload["jti"])
        except (TypeError, ValueError, AttributeError, KeyError) as err:
            raise OldapErrorTokenInvalid("Invalid token claims") from err
        return payload
