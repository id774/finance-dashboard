#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# config.py: Settings loader for Finance Dashboard
#
#  Description:
#  Build application settings from environment variables and an optional
#  YAML configuration file. Environment variables take precedence so that
#  credentials can be supplied without writing them to disk.
#
#  Basic authentication is enabled only when credentials are configured,
#  which keeps the historical behavior of running without authentication
#  when no configuration file exists.
#
#  Author: id774 (More info: http://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
########################################################################

import hashlib
import hmac
import logging
import os
import secrets
from typing import Any, Dict, Optional

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENV_PREFIX = "FINANCE_DASHBOARD_"

DEFAULT_SESSION_MAX_AGE = 1209600

logger = logging.getLogger(__name__)


class Settings:
    """Hold runtime settings resolved from the environment and a YAML file."""

    def __init__(
        self,
        data_dir: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        password_sha256: Optional[str] = None,
        secret_key: Optional[str] = None,
        root_path: str = "",
        session_max_age: int = DEFAULT_SESSION_MAX_AGE,
    ) -> None:
        self.data_dir = data_dir
        self.username = username
        self.password = password
        self.password_sha256 = password_sha256
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.root_path = root_path
        self.session_max_age = session_max_age

    @property
    def auth_required(self) -> bool:
        """Report whether Basic authentication must be enforced."""
        return bool(self.username) and bool(self.password or self.password_sha256)

    def verify_credentials(self, username: str, password: str) -> bool:
        """Compare supplied credentials with the configured ones."""
        if not self.auth_required:
            return True
        if not hmac.compare_digest(username, self.username or ""):
            return False
        if self.password_sha256:
            digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(digest, self.password_sha256.strip().lower())
        return hmac.compare_digest(password, self.password or "")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Read an application environment variable."""
    value = os.environ.get(ENV_PREFIX + name)
    if not value:
        return default
    return value


def _load_file(path: str) -> Dict[str, Any]:
    """Load a YAML configuration file, returning an empty mapping when absent."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        logger.warning("Ignoring malformed configuration file: %s", path)
        return {}
    return loaded


def _section(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Return a mapping section of the configuration."""
    section = config.get(name)
    return section if isinstance(section, dict) else {}


def load_settings(config_file: Optional[str] = None) -> Settings:
    """Resolve settings from the environment and the configuration file."""
    path = config_file or _env("CONFIG") or os.path.join(BASE_DIR, "config.yml")
    config = _load_file(path)
    auth = _section(config, "auth")
    session = _section(config, "session")
    data = _section(config, "data")

    data_dir = _env("DATA_DIR") or data.get("directory") or os.path.join(BASE_DIR, "public", "data")
    secret_key = _env("SECRET_KEY") or session.get("secret_key")
    if not secret_key:
        logger.warning("Session secret key is not configured, generating a temporary one")

    settings = Settings(
        data_dir=os.path.abspath(os.path.expanduser(str(data_dir))),
        username=_env("USERNAME") or auth.get("username"),
        password=_env("PASSWORD") or auth.get("password"),
        password_sha256=_env("PASSWORD_SHA256") or auth.get("password_sha256"),
        secret_key=secret_key,
        root_path=_env("ROOT_PATH", "") or "",
        session_max_age=int(_env("SESSION_MAX_AGE") or DEFAULT_SESSION_MAX_AGE),
    )
    if not settings.auth_required:
        logger.warning("Basic authentication is disabled because no credentials are configured")
    return settings
