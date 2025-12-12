import importlib.util
from pathlib import Path
import json
import pytest

USER_ID_TO_TEST = "238146303"
USER_IDS_TO_TEST = ["49346009", "40333919"]


def _load_target_module():
    """
    Tries to find and import the python file that contains your OSINT class,
    without hard-coding the module name (main.py, vinted_osint.py, etc.).
    """
    repo_root = Path(__file__).resolve().parents[1]

    candidates = []
    for py in repo_root.rglob("*.py"):
        if "tests" in py.parts:
            continue
        try:
            txt = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Strong-ish fingerprints for your file:
        if 'prog="Vinted OSINT"' in txt and "class OSINT" in txt and "/api/v2/users/" in txt:
            candidates.append(py)

    if not candidates:
        pytest.fail(
            "Could not find the module containing class OSINT. "
            "Make sure your main script is in the repo and contains 'class OSINT' "
            "and 'prog=\"Vinted OSINT\"'."
        )

    target = candidates[0]
    spec = importlib.util.spec_from_file_location("vinted_osint_target", target)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _wrap_with_timeout(fn, timeout_seconds=20):
    def inner(*args, **kwargs):
        kwargs.setdefault("timeout", timeout_seconds)
        return fn(*args, **kwargs)

    return inner


@pytest.fixture(scope="session")
def osint_mod():
    mod = _load_target_module()

    # Globals your OSINT class expects (normally set by main()).
    mod.extension = ".com"
    mod.export = False
    mod.fetch_all = False
    mod.export_format = "json"
    mod.username = USER_ID_TO_TEST
    mod.username_list = None

    return mod


def _make_osint_instance(mod, monkeypatch, username, username_list=None):
    # Prevent auto-run during __init__; we want to drive the steps manually in tests.
    monkeypatch.setattr(mod.OSINT, "start", lambda self: None)

    o = mod.OSINT(username=username, username_list=username_list)

    # Keep real network requests, but avoid hanging forever on a server.
    o.session.get = _wrap_with_timeout(o.session.get, 20)
    o.session.post = _wrap_with_timeout(o.session.post, 20)

    return o


def test_live_single_user_returns_user_dict(osint_mod, monkeypatch):
    o = _make_osint_instance(osint_mod, monkeypatch, username=USER_ID_TO_TEST)

    user = o.get_information(USER_ID_TO_TEST)

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


def test_live_tables_can_be_built_and_export_strings_are_valid(osint_mod, monkeypatch):
    o = _make_osint_instance(osint_mod, monkeypatch, username=USER_ID_TO_TEST)

    o.setup_tables()
    o.dictionary = o.get_information(USER_ID_TO_TEST)
    o.create_tables()

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
def test_live_multiple_users_return_data(osint_mod, monkeypatch, uid):
    o = _make_osint_instance(osint_mod, monkeypatch, username=uid)

    user = o.get_information(uid)
    assert isinstance(user, dict) and user, f"Expected non-empty user data for {uid}."
    assert "id" in user and user["id"] is not None, f"Expected an 'id' in user data for {uid}."


def test_user_list_file_is_read_correctly(osint_mod, monkeypatch, tmp_path):
    user_list_path = tmp_path / "users.txt"
    user_list_path.write_text("\n".join(USER_IDS_TO_TEST), encoding="utf-8")

    o = _make_osint_instance(osint_mod, monkeypatch, username=None, username_list=str(user_list_path))
    assert o.usernames == USER_IDS_TO_TEST
