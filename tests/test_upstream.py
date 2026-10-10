"""Offline regressions for the eaf_base_api v4 request and lifecycle contract."""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from base_api import BaseCore
from base_api.modules.errors import AccessDeniedError
from curl_cffi.requests import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import Vinted_OSINT as mod


@pytest.fixture
def osint(monkeypatch):
    obj = mod.OSINT('123', None)
    asyncio.run(obj.core.close())
    obj.core = Mock()
    obj.core.request = AsyncMock()
    obj.core.close = AsyncMock()
    return obj


def response(user):
    import json
    result = Response()
    result.status_code = 200
    result.content = json.dumps({'user': user}).encode()
    return result


def test_request_returns_user(osint):
    osint.core.request.return_value = response({'id': 123})
    assert asyncio.run(osint.get_information('123')) == {'id': 123}
    osint.core.request.assert_awaited_once_with(url='https://www.vinted.com/api/v2/users/123')


def test_access_denied_authenticates_then_retries(osint):
    osint.core.request.side_effect = [AccessDeniedError('HTTP 401'), response({}), response({'id': 123})]
    assert asyncio.run(osint.get_information('123')) == {'id': 123}
    assert osint.core.request.await_count == 3
    osint.core.session.cookies.clear.assert_called_once()
    assert osint.core.request.await_args_list[1].kwargs == {'method': 'POST', 'url': 'https://www.vinted.com'}


def test_access_denied_is_bounded(osint):
    denied = AccessDeniedError('HTTP 403')
    osint.core.request.side_effect = [denied, response({})] * 4 + [denied]
    with pytest.raises(AccessDeniedError):
        asyncio.run(osint.get_information('123'))
    assert osint.core.request.await_count == 9


def test_authentication_failure_propagates(osint):
    osint.core.request.side_effect = [AccessDeniedError('HTTP 401'), RuntimeError('authentication failed')]
    with pytest.raises(RuntimeError, match='authentication failed'):
        asyncio.run(osint.get_information('123'))


@pytest.mark.parametrize('fails', [False, True])
def test_start_closes_core(osint, fails):
    osint.get_information = AsyncMock(return_value={'id': 123})
    if fails:
        osint.get_information.side_effect = RuntimeError('request failed')
    result = asyncio.run(osint.start())
    assert bool(result.failures) == fails
    assert bool(result.users) != fails
    osint.core.close.assert_awaited_once()


def test_real_v4_core_raises_access_denied_without_network():
    async def check():
        async with BaseCore() as core:
            denied = Response()
            denied.status_code = 401
            denied.headers = {'content-type': 'application/json'}
            denied.content = b'{}'
            core.session.request = AsyncMock(return_value=denied)
            with pytest.raises(AccessDeniedError):
                await core.request('https://www.vinted.com/api/v2/users/123')
        assert core.session is None
    asyncio.run(check())
