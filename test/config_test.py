#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
# config_test.py: Unit tests for finance_dashboard.config
#
#  Description:
#  Validate the deliberately narrow configuration failure boundary: missing,
#  empty, null and unknown optional configuration remain tolerated, while
#  structurally invalid mappings and selected non-string authentication/session
#  values fail during settings loading.
#
#  Author: id774 (More info: https://id774.net)
#  Source Code: https://github.com/id774/finance-dashboard
#  License: The GPL version 3, or LGPL version 3 (Dual License).
#  Contact: idnanashi@gmail.com
#
#  Usage:
#      pytest test/config_test.py
#
#  Requirements:
#  - Python Version: 3.9 or later
#
#  Test Cases:
#    - Allow a missing or empty configuration file
#    - Reject a non-mapping top level
#    - Reject a non-null non-mapping named section
#    - Reject a selected non-string authentication or session-secret value
#    - Allow null sections and unknown keys
#
#  Version History:
#  v1.0 2026-09-12
#       Initial release.
#
########################################################################

import pytest

from finance_dashboard.config import load_settings


def test_missing_and_empty_configuration_are_allowed(tmp_path):
    missing = tmp_path / "missing.yml"
    load_settings(config_file=str(missing))

    empty = tmp_path / "empty.yml"
    empty.write_text("", encoding="utf-8")
    load_settings(config_file=str(empty))


def test_non_mapping_configuration_fails_at_startup(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text("- auth\n- session\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Configuration file must be a mapping"):
        load_settings(config_file=str(config))


@pytest.mark.parametrize("section_name", ["auth", "session", "data"])
def test_non_mapping_section_fails_at_startup(tmp_path, section_name):
    config = tmp_path / "config.yml"
    config.write_text("{}: invalid\n".format(section_name), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Configuration section must be a mapping: {}".format(section_name),
    ):
        load_settings(config_file=str(config))


@pytest.mark.parametrize(
    "section_name, key, env_name",
    [
        ("auth", "username", "FINANCE_DASHBOARD_USERNAME"),
        ("auth", "password", "FINANCE_DASHBOARD_PASSWORD"),
        ("auth", "password_sha256", "FINANCE_DASHBOARD_PASSWORD_SHA256"),
        ("session", "secret_key", "FINANCE_DASHBOARD_SECRET_KEY"),
    ],
)
def test_non_string_security_setting_fails_at_startup(
    tmp_path, monkeypatch, section_name, key, env_name
):
    monkeypatch.delenv(env_name, raising=False)
    config = tmp_path / "config.yml"
    config.write_text("{}:\n  {}: 123\n".format(section_name, key), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Configuration value must be a string: {}.{}".format(section_name, key),
    ):
        load_settings(config_file=str(config))


def test_null_sections_and_unknown_keys_are_allowed(tmp_path):
    config = tmp_path / "config.yml"
    config.write_text(
        "auth:\n"
        "session:\n"
        "data:\n"
        "unknown_section:\n"
        "  arbitrary: value\n",
        encoding="utf-8",
    )

    load_settings(config_file=str(config))
