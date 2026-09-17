"""Inline keyboardlar."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings


def open_app_kb() -> InlineKeyboardMarkup:
    """Davomat Mini App'ni ochish tugmasi.

    `web_app` tugmasi Mini App'ga imzolangan `initData` beradi — backend
    foydalanuvchini shu orqali aniqlaydi.
    """
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📱 Davomat ilovasini ochish",
        web_app=WebAppInfo(url=settings.WEBAPP_URL),
    )
    return kb.as_markup()
