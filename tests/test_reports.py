import asyncio
import copy
import csv
import json
from unittest.mock import AsyncMock, Mock

import pytest

from Vinted_OSINT import OSINT, UserReport, run_main


@pytest.fixture
def user():
    return {'id': 123, 'login': 'seller, "name"', 'about': 'line one\nline two é',
            'photo': {'id': 9, 'url': 'https://example.com/photo', 'is_suspicious': False},
            'bundle_discount': {'enabled': True, 'discounts': [{'minimal_item_count': 2, 'fraction': 0.1}]},
            'accepted_pay_in_methods': [{'id': 1, 'code': 'card'}],
            'feedback_count': 0, 'negative_feedback_count': 0,
            'verification': {'email': {'valid': True}}, 'new_api_field': {'enabled': True}}


@pytest.mark.parametrize('fmt', ['json', 'csv', 'html', 'latex', 'txt'])
def test_exports_four_independent_files(user, tmp_path, fmt):
    original = copy.deepcopy(user)
    report = UserReport(user, fetch_all=True)
    paths = report.export('123', fmt, tmp_path)
    assert len(paths) == 4
    assert {p.name for p in paths} == {f'data_{name}_123.{fmt}' for name in ('main', 'photo', 'discount', 'payment')}
    for path in paths:
        content = path.read_text(encoding='utf-8')
        assert content
        if fmt == 'json':
            assert isinstance(json.loads(content), list)
        elif fmt == 'csv':
            with path.open(newline='', encoding='utf-8') as source:
                rows = list(csv.reader(source))
            assert len(rows) > 1
            assert all(len(row) == len(rows[0]) for row in rows)
        elif fmt == 'html':
            assert '<table' in content and '</table>' in content
        elif fmt == 'latex':
            assert '\\begin{tabular}' in content and '\\end{tabular}' in content
    assert user == original
    if fmt == 'json':
        assert any(row.get('Variable') == 'new_api_field' for row in json.loads(paths[0].read_text()) if isinstance(row, dict))


def test_reports_distinguish_zero_and_missing():
    observations, missing = UserReport.evaluate_seller_risk({'feedback_count': 0, 'is_account_banned': True})
    assert 'Feedback count: 0' in observations
    assert 'Account ban reported' in observations
    assert 'feedback_count' not in missing
    assert 'negative_feedback_count' in missing
    assert UserReport.evaluate_seller_risk({})[0] == []


def test_batch_continues_and_keeps_user_data(user, tmp_path, monkeypatch):
    ids = tmp_path / 'ids.txt'
    ids.write_text('123\n456\n789\n')
    core = Mock(request=AsyncMock(), close=AsyncMock())
    client = OSINT(username_list=ids, core=core, export_format='json', output_dir=tmp_path)
    last = {**user, 'id': 789}
    client.get_information = AsyncMock(side_effect=[user, ValueError('missing user'), last])
    monkeypatch.setattr(UserReport, 'print_everything', lambda self: None)
    result = asyncio.run(client.start())
    assert result.users == {'123': user, '789': last}
    assert result.failures == {'456': 'ValueError: missing user'}
    assert len(list((tmp_path / '123').glob('*.json'))) == 4
    assert len(list((tmp_path / '789').glob('*.json'))) == 4
    assert not (tmp_path / '456').exists()
    core.close.assert_awaited_once()


def test_instance_options_are_independent():
    a = OSINT('123', extension='.fr')
    b = OSINT('456', extension='.de')
    assert a.VINTED_AUTH_URL.endswith('.fr')
    assert b.VINTED_AUTH_URL.endswith('.de')
    assert a.core.session is None and b.core.session is None


@pytest.mark.parametrize('user_id', ['../123', '', 'alice'])
def test_invalid_ids_rejected(user_id):
    with pytest.raises(ValueError):
        OSINT(user_id)


@pytest.mark.parametrize('payload', [None, [], {}, {'id': 456}])
def test_unexpected_response_rejected(payload):
    core = Mock(request=AsyncMock(), close=AsyncMock())
    core.request.return_value = Mock()
    core.request.return_value.json.return_value = {'user': payload}
    client = OSINT('123', core=core)
    with pytest.raises(ValueError):
        asyncio.run(client.get_information('123'))


def test_license_requires_no_user():
    assert asyncio.run(run_main(['--license'])) == 0


def test_cli_returns_failure_status(monkeypatch):
    from Vinted_OSINT import BatchResult
    monkeypatch.setattr(OSINT, 'start', AsyncMock(return_value=BatchResult(failures={'123': 'missing'})))
    assert asyncio.run(run_main(['-u', '123'])) == 1


def test_export_failure_does_not_stop_batch(user, tmp_path, monkeypatch):
    ids = tmp_path / 'ids.txt'
    ids.write_text('123\n789\n')
    core = Mock(close=AsyncMock())
    client = OSINT(username_list=ids, core=core, export_format='csv')
    client.get_information = AsyncMock(side_effect=[user, {**user, 'id': 789}])
    monkeypatch.setattr(UserReport, 'print_everything', lambda self: None)
    monkeypatch.setattr(UserReport, 'export', Mock(side_effect=[OSError('disk full'), []]))
    result = asyncio.run(client.start())
    assert set(result.users) == {'789'}
    assert result.failures == {'123': 'OSError: disk full'}
    core.close.assert_awaited_once()


def test_cancellation_closes_core():
    core = Mock(close=AsyncMock())
    client = OSINT('123', core=core)
    client.get_information = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(client.start())
    core.close.assert_awaited_once()
