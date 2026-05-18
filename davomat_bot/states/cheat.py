"""Chetlatish flow FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CheatFlow(StatesGroup):
    waiting_jshshir = State()
