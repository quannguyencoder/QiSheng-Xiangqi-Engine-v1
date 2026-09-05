"""
XuanWu - quy doi diem danh gia sang thang 0..1000 theo goc nhin Trang.

  500  = can bang
  505  = the co khoi dau (Trang di truoc, +5 diem tempo)
  1000 = Trang chieu het duoc ngay trong luot nay
  0    = nguoc lai cho Den

Tach rieng khoi evaluate.py de sau nay co the hieu chinh (calibrate) thang diem
ma khong dung toi logic danh gia.
"""

import math

MIN_SCORE = 0
MAX_SCORE = 1000
NEUTRAL_SCORE = 500
TEMPO_BONUS = 5

# Chenh lech "tho" bang ngan nay thi coi nhu ap sat bien cua thang diem.
MATERIAL_SCALE = 1600.0


def raw_to_score(raw: float, white_to_move: bool) -> int:
    """Chenh lech tho (duong = loi cho Trang) -> diem 0..1000.

    Ket qua luon nam trong [1, 999]: hai gia tri 0 va 1000 duoc danh rieng cho
    ket qua chieu het da duoc search() xac nhan, de khong nham voi phong doan.
    """
    normalized = math.tanh(raw / MATERIAL_SCALE) * (NEUTRAL_SCORE - TEMPO_BONUS)
    tempo = TEMPO_BONUS if white_to_move else -TEMPO_BONUS
    return max(1, min(999, round(NEUTRAL_SCORE + normalized + tempo)))
