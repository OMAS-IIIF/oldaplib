"""Shared non-production configuration for the oldaplib test suite."""

import os


os.environ.setdefault("OLDAP_ACCESS_JWT_SECRET", "oldaplib-test-access-secret-at-least-32-bytes")
os.environ.setdefault("OLDAP_REFRESH_JWT_SECRET", "oldaplib-test-refresh-secret-at-least-32-bytes")
os.environ.setdefault("OLDAP_MEDIA_JWT_SECRET", "oldaplib-test-media-secret-at-least-32-bytes")
