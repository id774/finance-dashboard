#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# finance_dashboard/config.py: Settings loader of Finance Dashboard
#
#  Description:
#  Resolve every runtime setting of the dashboard in one place: which
#  directory the generated files are read from, whether Basic
#  authentication is enforced and against which credentials, the key that
#  signs the session cookie, and the path prefix the application is
#  published under.
#
#  Settings come from environment variables first and from an optional
#  YAML file second, so that a credential can be supplied to the systemd
#  unit without being written into a file in the deployment directory.
#  This is the only module that reads os.environ; main.py resolves a
#  Settings once at startup and passes it down, which is what lets a test
#  build an application against a temporary directory without touching
#  the environment of the process.
#
#  Authentication is enforced only when a user name and either a password
#  or its SHA-256 digest are configured. Without them the dashboard is
#  served to anyone who can reach it, which is the behaviour the previous
#  Sinatra version had when no configuration file existed. Comparisons go
#  through hmac.compare_digest rather than ==, so a wrong password costs
#  the same time as a right one.
#
#  Nothing here reads a data file or reaches the network. A missing or empty
#  YAML file is not an error. A syntactically valid file whose top level or
#  a non-null named section has an incompatible structure stops startup.
#  Authentication credentials and the session secret are required to be
#  strings only when their YAML values are actually selected after
#  environment precedence. Unknown keys, omitted or null optional values,
#  digest syntax, and data-directory existence are not made strict merely
#  for validation.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Requirements:
#  - Python Version: 3.9 or later
#  - PyYAML
#
#  Environment Variables:
#  Every name below is prefixed with FINANCE_DASHBOARD_ and takes
#  precedence over the corresponding key of the YAML file.
#  - CONFIG
#      Path of the YAML file. Defaults to config.yml in the repository
#      root. A missing file is not an error.
#  - DATA_DIR
#      Directory holding the files finance generates. YAML key
#      data.directory. Defaults to public/data, and is expanded and made
#      absolute so that the application runs from any working directory.
#  - USERNAME / PASSWORD / PASSWORD_SHA256
#      Basic authentication credentials. YAML keys auth.username,
#      auth.password and auth.password_sha256. The digest is preferred
#      where both are set, so that no plain password need be stored.
#  - SECRET_KEY
#      Key signing the session cookie that carries the recently viewed
#      codes. YAML key session.secret_key. A temporary key is generated
#      and a warning logged when unset, which logs every viewer out on a
#      restart; set it in any deployment that outlives one process.
#  - SESSION_MAX_AGE
#      Lifetime of that cookie in seconds. Defaults to 1209600, two weeks.
#  - ROOT_PATH
#      Path prefix when the application is published under a sub
#      directory, for example /finance-dashboard behind Apache. Empty by
#      default.
#
#  Version History:
#  v1.1 2026-09-12
#       Reject structurally invalid configuration and non-string selected
#       authentication or session-secret values at startup.
#  v1.0 2026-07-25
#       Initial release.
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
    """Load an optional YAML configuration file."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("Configuration file must be a mapping: {}".format(path))
    return loaded


def _section(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Return an optional mapping section of the configuration."""
    section = config.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError("Configuration section must be a mapping: {}".format(name))
    return section


def _optional_string(section: Dict[str, Any], section_name: str, key: str) -> Optional[str]:
    """Return an optional string setting without coercing other YAML types."""
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(
            "Configuration value must be a string: {}.{}".format(section_name, key)
        )
    return value


def load_settings(config_file: Optional[str] = None) -> Settings:
    """Resolve settings from the environment and the configuration file."""
    path = config_file or _env("CONFIG") or os.path.join(BASE_DIR, "config.yml")
    config = _load_file(path)
    auth = _section(config, "auth")
    session = _section(config, "session")
    data = _section(config, "data")

    data_dir = _env("DATA_DIR") or data.get("directory") or os.path.join(BASE_DIR, "public", "data")
    secret_key = _env("SECRET_KEY") or _optional_string(session, "session", "secret_key")
    if not secret_key:
        logger.warning("Session secret key is not configured, generating a temporary one")

    settings = Settings(
        data_dir=os.path.abspath(os.path.expanduser(str(data_dir))),
        username=_env("USERNAME") or _optional_string(auth, "auth", "username"),
        password=_env("PASSWORD") or _optional_string(auth, "auth", "password"),
        password_sha256=_env("PASSWORD_SHA256")
        or _optional_string(auth, "auth", "password_sha256"),
        secret_key=secret_key,
        root_path=_env("ROOT_PATH", "") or "",
        session_max_age=int(_env("SESSION_MAX_AGE") or DEFAULT_SESSION_MAX_AGE),
    )
    if not settings.auth_required:
        logger.warning("Basic authentication is disabled because no credentials are configured")
    return settings
