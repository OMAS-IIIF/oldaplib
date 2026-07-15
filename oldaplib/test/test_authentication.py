"""Unit tests for the purpose-specific OLDAP token core."""

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt

from oldaplib.src.authentication import (
    AuthorizationContext,
    TokenCodec,
    TokenSettings,
)
from oldaplib.src.connection import _bootstrap_token_codec
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.observable_dict import ObservableDict
from oldaplib.src.helpers.oldaperror import (
    OldapErrorConfiguration,
    OldapErrorTokenExpired,
    OldapErrorTokenInvalid,
)
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class TestTokenCodec(unittest.TestCase):
    """Verify strict claims, token separation, and configuration behavior."""

    def setUp(self) -> None:
        self.settings = TokenSettings(
            access_secret="access-secret-for-tests-at-least-32-bytes",
            refresh_secret="refresh-secret-for-tests-at-least-32-bytes",
            media_secret="media-secret-for-tests-at-least-32-bytes",
            issuer="https://issuer.example",
            audience="oldap-test-api",
            access_ttl_seconds=900,
            refresh_ttl_seconds=1200,
            media_ttl_seconds=3600,
        )
        self.codec = TokenCodec(self.settings)
        self.context = AuthorizationContext(
            userIri=Iri("https://example.org/users/alice"),
            userId=Xsd_NCName("alice"),
            inProject=InProjectClass(
                {"oldap:SystemProject": {AdminPermission.ADMIN_USERS}}
            ),
            hasRole=ObservableDict(
                {Xsd_QName("oldap:GenericViewRole"): Xsd_QName("oldap:DATA_VIEW")}
            ),
        )

    def test_access_token_round_trip_uses_minimal_claims(self) -> None:
        token = self.codec.issue_access_token(self.context)
        payload = jwt.decode(
            token,
            self.settings.access_secret,
            algorithms=["HS256"],
            issuer=self.settings.issuer,
            audience=self.settings.access_audience,
        )

        self.assertEqual(payload["typ"], "access")
        self.assertEqual(payload["sub"], "alice")
        self.assertEqual(payload["aud"], "oldap-test-api")
        self.assertEqual(
            payload["auth"]["inProject"]["oldap:SystemProject"],
            ["oldap:ADMIN_USERS"],
        )
        for excluded in (
            "userdata",
            "credentials",
            "email",
            "familyName",
            "givenName",
            "passwordResetRequestAt",
            "authVersion",
        ):
            self.assertNotIn(excluded, payload)

        decoded = self.codec.decode_access_token(token)
        self.assertEqual(decoded.userId, Xsd_NCName("alice"))
        self.assertEqual(decoded.userIri, Iri("https://example.org/users/alice"))
        self.assertIn(
            AdminPermission.ADMIN_USERS,
            decoded.inProject[Iri("oldap:SystemProject")],
        )
        self.assertEqual(
            decoded.hasRole[Xsd_QName("oldap:GenericViewRole")],
            Xsd_QName("oldap:DATA_VIEW"),
        )

    def test_refresh_token_round_trip_uses_only_versioned_identity(self) -> None:
        token = self.codec.issue_refresh_token("alice", 7)
        payload = jwt.decode(
            token,
            self.settings.refresh_secret,
            algorithms=["HS256"],
            issuer=self.settings.issuer,
            audience=self.settings.refresh_audience,
        )
        self.assertEqual(payload["typ"], "refresh")
        self.assertEqual(payload["authVersion"], 7)
        self.assertNotIn("auth", payload)
        self.assertNotIn("userIri", payload)

        decoded = self.codec.decode_refresh_token(token)
        self.assertEqual(decoded.userId, Xsd_NCName("alice"))
        self.assertEqual(decoded.authVersion, 7)

    def test_token_purposes_cannot_be_interchanged(self) -> None:
        access = self.codec.issue_access_token(self.context)
        refresh = self.codec.issue_refresh_token("alice", 3)
        media = self.codec.issue_media_token(
            "alice", {"assetId": "asset-1", "path": "project/image"}
        )

        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.decode_refresh_token(access)
        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.decode_access_token(refresh)
        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.decode_media_token(access)
        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.decode_access_token(media)

        # Prove that type validation is independent of the separate secrets.
        payload = jwt.decode(
            access,
            self.settings.access_secret,
            algorithms=["HS256"],
            options={"verify_signature": False},
        )
        payload["typ"] = "refresh"
        wrong_type = jwt.encode(payload, self.settings.access_secret, algorithm="HS256")
        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.decode_access_token(wrong_type)

    def test_wrong_issuer_audience_and_signature_are_rejected(self) -> None:
        now = datetime.now(timezone.utc)
        base_payload = {
            "typ": "access",
            "sub": "alice",
            "userIri": "https://example.org/users/alice",
            "iss": self.settings.issuer,
            "aud": self.settings.access_audience,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "jti": "ce4b92b7-7334-40f8-aeed-eafbf5c38255",
            "auth": {"inProject": {}, "hasRole": {}},
        }
        variants = (
            ({**base_payload, "iss": "https://wrong.example"}, self.settings.access_secret),
            ({**base_payload, "aud": "wrong-audience"}, self.settings.access_secret),
            (base_payload, "wrong-secret-for-tests-at-least-32-bytes"),
        )
        for payload, secret in variants:
            with self.subTest(payload=payload, secret=secret):
                token = jwt.encode(payload, secret, algorithm="HS256")
                with self.assertRaises(OldapErrorTokenInvalid):
                    self.codec.decode_access_token(token)

    def test_expired_token_has_specific_error(self) -> None:
        token = self.codec.issue_access_token(
            self.context,
            now=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with self.assertRaises(OldapErrorTokenExpired):
            self.codec.decode_access_token(token)

    def test_media_token_round_trip_uses_dedicated_contract(self) -> None:
        token = self.codec.issue_media_token(
            "alice",
            {
                "assetId": "asset-1",
                "path": "project/image/archive",
                "originalName": "source.tif",
            },
        )
        payload = jwt.decode(
            token,
            self.settings.media_secret,
            algorithms=["HS256"],
            issuer=self.settings.issuer,
            audience=self.settings.media_audience,
        )

        self.assertEqual(payload["typ"], "media")
        self.assertEqual(payload["sub"], "alice")
        self.assertEqual(payload["assetId"], "asset-1")
        self.assertEqual(payload["aud"], "oldap-test-api-media")
        self.assertNotIn("auth", payload)

        decoded = self.codec.decode_media_token(token)
        self.assertEqual(decoded["path"], "project/image/archive")

    def test_media_token_rejects_reserved_claims(self) -> None:
        with self.assertRaises(OldapErrorTokenInvalid):
            self.codec.issue_media_token("alice", {"assetId": "asset-1", "exp": 1})

    def test_token_secrets_must_be_distinct(self) -> None:
        with self.assertRaises(OldapErrorConfiguration):
            TokenSettings(
                access_secret="same-secret-for-tests-at-least-32-bytes",
                media_secret="same-secret-for-tests-at-least-32-bytes",
            )

    def test_missing_secret_fails_closed(self) -> None:
        settings = TokenSettings(
            access_secret=None, refresh_secret=None, media_secret=None
        )
        codec = TokenCodec(settings)

        with self.assertRaises(OldapErrorConfiguration):
            codec.issue_access_token(self.context)
        with self.assertRaises(OldapErrorConfiguration):
            codec.issue_refresh_token("alice", 0)
        with self.assertRaises(OldapErrorConfiguration):
            codec.issue_media_token("alice", {"assetId": "asset-1"})

        short_secret_codec = TokenCodec(TokenSettings(access_secret="too-short"))
        with self.assertRaises(OldapErrorConfiguration):
            short_secret_codec.issue_access_token(self.context)

    def test_legacy_secret_is_not_a_fallback(self) -> None:
        environment = {"OLDAP_JWT_SECRET": "legacy-secret"}
        with patch.dict(os.environ, environment, clear=True):
            codec = TokenCodec.from_environment()
            with self.assertRaises(OldapErrorConfiguration):
                codec.issue_access_token(self.context)

    def test_connection_main_bootstrap_needs_no_configured_secret(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            codec = _bootstrap_token_codec()
            secret = codec.settings.require_access_secret()
        self.assertGreaterEqual(len(secret.encode("utf-8")), 32)


if __name__ == "__main__":
    unittest.main()
