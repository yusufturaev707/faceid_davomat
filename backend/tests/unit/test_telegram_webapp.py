"""Telegram Mini App initData imzo tekshiruvi."""

import json
import time
from urllib.parse import parse_qsl, urlencode

import pytest

from app.core.telegram_webapp import InitDataError, sign_init_data, validate_init_data

BOT_TOKEN = "123456:TEST-token-for-unit-tests"
NOW = 1_780_000_000


def _fields(**overrides) -> dict[str, str]:
    fields = {
        "auth_date": str(NOW - 60),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {"id": 279058397, "first_name": "Ali", "username": "ali", "language_code": "uz"},
            separators=(",", ":"),
        ),
        "signature": "c2lnbmF0dXJl",
    }
    fields.update(overrides)
    return fields


def _validate(init_data: str, **kwargs):
    kwargs.setdefault("max_age_seconds", 3600)
    kwargs.setdefault("now", NOW)
    return validate_init_data(init_data, BOT_TOKEN, **kwargs)


def test_valid_init_data_returns_signed_user():
    user = _validate(sign_init_data(_fields(), BOT_TOKEN))
    assert user.id == 279058397
    assert user.first_name == "Ali"
    assert user.username == "ali"


def test_tampered_user_id_is_rejected():
    pairs = dict(parse_qsl(sign_init_data(_fields(), BOT_TOKEN)))
    pairs["user"] = pairs["user"].replace("279058397", "111111111")
    with pytest.raises(InitDataError, match="imzosi mos kelmadi"):
        _validate(urlencode(pairs))


def test_signature_from_another_bot_is_rejected():
    init_data = sign_init_data(_fields(), "999:another-bot")
    with pytest.raises(InitDataError):
        _validate(init_data)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError, match="imzosi yo'q"):
        _validate(urlencode(_fields()))


def test_duplicate_keys_are_rejected():
    init_data = sign_init_data(_fields(), BOT_TOKEN) + "&user=%7B%22id%22%3A1%7D"
    with pytest.raises(InitDataError, match="takroriy"):
        _validate(init_data)


def test_expired_init_data_is_flagged():
    init_data = sign_init_data(_fields(auth_date=str(NOW - 7200)), BOT_TOKEN)
    with pytest.raises(InitDataError) as exc:
        _validate(init_data, max_age_seconds=3600)
    assert exc.value.expired is True


def test_auth_date_in_future_is_rejected():
    init_data = sign_init_data(_fields(auth_date=str(NOW + 3600)), BOT_TOKEN)
    with pytest.raises(InitDataError) as exc:
        _validate(init_data)
    assert exc.value.expired is False


def test_init_data_without_user_is_rejected():
    fields = _fields()
    del fields["user"]
    with pytest.raises(InitDataError, match="foydalanuvchi"):
        _validate(sign_init_data(fields, BOT_TOKEN))


def test_empty_bot_token_never_validates():
    init_data = sign_init_data(_fields(), "")
    with pytest.raises(InitDataError, match="sozlanmagan"):
        validate_init_data(init_data, "", max_age_seconds=3600, now=NOW)


def test_uses_wall_clock_when_now_not_given():
    fields = _fields(auth_date=str(int(time.time())))
    user = validate_init_data(sign_init_data(fields, BOT_TOKEN), BOT_TOKEN, max_age_seconds=60)
    assert user.id == 279058397
