"""Face ID flow uchun FSM holatlari."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class FaceIDManual(StatesGroup):
    """Manual pasport kiritish FSM.

    Pasport seriyasi + raqamini bitta xabarda (masalan `AD2311141`) qabul
    qilamiz — foydalanuvchi uchun bu tezroq va ID-card orqasidagi formatga
    mos keladi.
    """

    waiting_passport = State()   # 2 ta harf + 7 ta raqam
    waiting_jshshir = State()    # 14 ta raqam
    waiting_selfie = State()


class FaceIDQR(StatesGroup):
    waiting_qr_image = State()
    waiting_selfie = State()
