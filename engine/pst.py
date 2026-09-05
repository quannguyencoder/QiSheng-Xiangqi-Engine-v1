"""
XuanWu - piece-square table: gia tri cong them theo VI TRI cua tung quan.

Bang viet theo goc nhin TRANG (hang 9 = hau phuong Trang, hang 0 = hau phuong Den,
Trang tien len phia hang 0). Voi quan Den, bang duoc lat nguoc theo chieu doc.

Don vi cung thang voi PIECE_VALUES (Xe=900, Phao=450, Ma=400, Si/Tuong=200, Tot=100).
"""

# Tot: cang tien sau cang manh, dinh cao o hang 1-2 gan cung doi phuong.
# (Sang hang 0 lai kem hon vi chi con di ngang duoc.)
PST_P = [
    [  0,   3,   6,   9,  12,   9,   6,   3,   0],
    [ 18,  36,  56,  80, 120,  80,  56,  36,  18],
    [ 14,  26,  42,  60,  80,  60,  42,  26,  14],
    [ 10,  20,  30,  34,  40,  34,  30,  20,  10],
    [  6,  12,  18,  18,  20,  18,  18,  12,   6],
    [  2,   0,   8,   0,   8,   0,   8,   0,   2],
    [  0,   0,  -2,   0,   4,   0,  -2,   0,   0],
    [  0,   0,   0,   0,   0,   0,   0,   0,   0],
    [  0,   0,   0,   0,   0,   0,   0,   0,   0],
    [  0,   0,   0,   0,   0,   0,   0,   0,   0],
]

# Ma: manh o trung tam, yeu o bien va goc (bi can chan nhieu huong).
PST_H = [
    [  0,  -4,   0,   0,   0,   0,   0,  -4,   0],
    [  4,   2,   8,   8,  10,   8,   8,   2,   4],
    [  4,  10,  14,  16,  16,  16,  14,  10,   4],
    [  6,  12,  18,  22,  22,  22,  18,  12,   6],
    [  6,  14,  20,  24,  26,  24,  20,  14,   6],
    [  4,  12,  18,  22,  24,  22,  18,  12,   4],
    [  2,   8,  14,  16,  18,  16,  14,   8,   2],
    [  0,   6,  10,  12,  12,  12,  10,   6,   0],
    [  0,   2,   6,   8,   8,   8,   6,   2,   0],
    [  0,  -4,   4,   0,   0,   0,   4,  -4,   0],
]

# Xe: manh o moi noi, hoi thien ve cot giua va hang tien.
PST_R = [
    [  6,  10,  12,  14,  14,  14,  12,  10,   6],
    [  8,  12,  14,  16,  16,  16,  14,  12,   8],
    [  6,  10,  12,  14,  14,  14,  12,  10,   6],
    [  6,  10,  12,  14,  14,  14,  12,  10,   6],
    [  6,   8,  10,  12,  12,  12,  10,   8,   6],
    [  4,   8,  10,  12,  12,  12,  10,   8,   4],
    [  4,   6,   8,  10,  10,  10,   8,   6,   4],
    [  2,   6,   8,  10,  10,  10,   8,   6,   2],
    [  2,   4,   6,   8,   8,   8,   6,   4,   2],
    [  0,   4,   6,   8,   8,   8,   6,   4,   0],
]

# Phao: thich cot giua; o nha van manh vi can ngoi de ban.
PST_C = [
    [  0,   0,   2,   6,   6,   6,   2,   0,   0],
    [  0,   2,   4,   6,   8,   6,   4,   2,   0],
    [  2,   4,   6,   8,  10,   8,   6,   4,   2],
    [  0,   2,   4,   6,   8,   6,   4,   2,   0],
    [  0,   0,   2,   4,   6,   4,   2,   0,   0],
    [  0,   0,   2,   4,   6,   4,   2,   0,   0],
    [  0,   2,   4,   6,   8,   6,   4,   2,   0],
    [  0,   2,   4,   6,   8,   6,   4,   2,   0],
    [  0,   0,   2,   4,   4,   4,   2,   0,   0],
    [  0,   0,   0,   2,   2,   2,   0,   0,   0],
]

_0 = [[0] * 9 for _ in range(10)]

# Si va Tuong gan nhu co dinh trong vai tro phong thu: thuong nho khi dung cho.
PST_A = [row[:] for row in _0]
for r, c in ((9, 3), (9, 5), (8, 4)):
    PST_A[r][c] = 6

PST_E = [row[:] for row in _0]
for r, c in ((9, 2), (9, 6), (7, 0), (7, 4), (7, 8)):
    PST_E[r][c] = 6

# Tuong soai: an toan nhat khi o day cung.
PST_K = [row[:] for row in _0]
PST_K[9][4], PST_K[8][4], PST_K[7][4] = 8, 0, -12

TABLES = {"P": PST_P, "H": PST_H, "R": PST_R, "C": PST_C,
          "A": PST_A, "E": PST_E, "K": PST_K}


def pst_value(kind: str, row: int, col: int, is_white: bool) -> int:
    """Diem vi tri cua mot quan. Quan Den dung bang lat nguoc theo chieu doc."""
    table = TABLES[kind]
    return table[row][col] if is_white else table[9 - row][col]
