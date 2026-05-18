"""Davomatdan olib tashlash flow FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class RemoveAttendance(StatesGroup):
    waiting_jshshir = State()
