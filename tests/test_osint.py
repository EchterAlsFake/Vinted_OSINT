import sys
import json
import asyncio
from pathlib import Path

import pytest

# Add src to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import Vinted_OSINT

USER_ID_TO_TEST = "238146303"
USER_IDS_TO_TEST = ["49346009", "40333919"]


@pytest.fixture(scope="session")
def osint_mod():
    return Vinted_OSINT


def _make_osint_instance(mod, monkeypatch, username, username_list=None):
    # Prevent auto-run during __init__; we want to drive the steps manually in tests.
    monkeypatch.setattr(mod.OSINT, "start", lambda self: None)

    o = mod.OSINT(username=username, username_list=username_list)
    return o


def _get_information(o, user_id):
    async def fetch_and_close():
        try:
            return await o.get_information(user_id)
        finally:
            await o.core.close()
    return asyncio.run(fetch_and_close())


@pytest.mark.live
def test_live_single_user_returns_user_dict(osint_mod, monkeypatch):
    o = _make_osint_instance(osint_mod, monkeypatch, username=USER_ID_TO_TEST)

    user = _get_information(o, USER_ID_TO_TEST)

    assert isinstance(user, dict), "Expected a dict from get_information()."
    assert user, "Expected non-empty user data."

    # Core fields that should exist if the API still behaves like your code expects:
    assert "id" in user, "Missing 'id' key in returned user object."
    assert str(user["id"]) == USER_ID_TO_TEST, "Returned user id did not match the requested id."
    assert user.get("login") not in (None, ""), "Expected a non-empty 'login' field."
    assert (
        isinstance(user.get("profile_url") or user.get("share_profile_url"), str)
        and "vinted" in (user.get("profile_url") or user.get("share_profile_url")).lower()
    ), "Expected a Vinted profile URL."


@pytest.mark.live
def test_live_tables_can_be_built_and_export_strings_are_valid(osint_mod, monkeypatch):
    o = _make_osint_instance(osint_mod, monkeypatch, username=USER_ID_TO_TEST)

    o = Vinted_OSINT.UserReport(_get_information(o, USER_ID_TO_TEST))

    assert len(o.main_table.rows) > 0, "Expected main_table to have rows."

    # Ensure PrettyTable outputs exist (basic “data returned” / “formatting works” check)
    main_json = o.main_table.get_json_string()
    assert isinstance(main_json, str) and len(main_json) > 10
    # Should be parseable JSON
    json.loads(main_json)

    # Photo / discount / payment tables can legitimately be empty depending on user/account,
    # so we only require they can produce strings without crashing.
    json.loads(o.photo_table.get_json_string())
    json.loads(o.discount_table.get_json_string())
    json.loads(o.payment_table.get_json_string())


@pytest.mark.parametrize("uid", USER_IDS_TO_TEST)
@pytest.mark.live
def test_live_multiple_users_return_data(osint_mod, monkeypatch, uid):
    o = _make_osint_instance(osint_mod, monkeypatch, username=uid)

    user = _get_information(o, uid)
    assert isinstance(user, dict) and user, f"Expected non-empty user data for {uid}."
    assert "id" in user and user["id"] is not None, f"Expected an 'id' in user data for {uid}."


def test_user_list_file_is_read_correctly(osint_mod, monkeypatch, tmp_path):
    user_list_path = tmp_path / "users.txt"
    user_list_path.write_text("\n".join(USER_IDS_TO_TEST), encoding="utf-8")

    o = _make_osint_instance(osint_mod, monkeypatch, username=None, username_list=str(user_list_path))
    try:
        assert o.usernames == USER_IDS_TO_TEST
    finally:
        asyncio.run(o.core.close())
