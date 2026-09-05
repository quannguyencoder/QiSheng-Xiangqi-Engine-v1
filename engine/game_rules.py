"""
XuanWu - luat cap VAN CO: lap nuoc, chieu lien tuc, ket thuc van.

Engine tim kiem chi biet mot the co roi rac. Mot van co that con can nhung luat
phu thuoc LICH SU: lap the co, chieu lien tuc, va gioi han so nuoc khong an quan.
Thieu chung thi tren web mot van co the lap vo tan ma khong ai xu duoc.

Diem khac quan trong so voi co vua: trong co tuong, CHIEU LIEN TUC LA THUA cho
ben chieu, khong phai hoa. Ben bi chieu chi can lap lai the co la ben chieu bi
xu thua. Day la luat rat dac trung cua co tuong va de cai sai neu quen.

Luat cai o day theo huong don gian nhung dung o cac tinh huong thuong gap:
  - Het nuoc di          -> ben den luot THUA (khong co hoa vi het nuoc)
  - Lap the co 3 lan     -> xet ai la ben gay ra lap:
                            neu mot ben chieu suot chu ky lap -> ben do THUA
                            nguoc lai -> HOA
  - 120 nuoc khong an quan -> HOA
"""

from typing import List, Optional, Tuple

from engine.board import (
    Board, Move, WHITE, BLACK, start_board, legal_moves, make_move, in_check,
)

DANG_CHOI = "dang_choi"
TRANG_THANG = "trang_thang"
DEN_THANG = "den_thang"
HOA = "hoa"

SO_NUOC_HOA = 120          # 60 nuoc moi ben khong an quan -> hoa
SO_LAN_LAP = 3


def _khoa(board: Board, side: str) -> str:
    return "".join("".join(r) for r in board) + side


class VanCo:
    """Mot van co, co lich su - du de ap dung cac luat phu thuoc lich su."""

    def __init__(self, board: Optional[Board] = None, side: str = WHITE):
        self.board = board if board is not None else start_board()
        self.side = side
        # lich su: (khoa the co, ben vua di co chieu doi phuong khong)
        self.lich_su: List[Tuple[str, bool]] = [(_khoa(self.board, self.side), False)]
        self.tu_lan_an_quan = 0

    # -- truy van -----------------------------------------------------------

    def nuoc_hop_le(self) -> List[Move]:
        return legal_moves(self.board, self.side)

    def dang_bi_chieu(self) -> bool:
        return in_check(self.board, self.side)

    def so_lan_lap(self) -> int:
        k = _khoa(self.board, self.side)
        return sum(1 for x, _ in self.lich_su if x == k)

    # -- di nuoc ------------------------------------------------------------

    def di(self, mv: Move) -> None:
        """Thuc hien mot nuoc di. Nem ValueError neu nuoc khong hop le."""
        if mv not in self.nuoc_hop_le():
            raise ValueError(f"Nuoc di khong hop le: {mv}")
        an_quan = self.board[mv[2]][mv[3]] != "."
        self.board = make_move(self.board, mv)
        self.side = BLACK if self.side == WHITE else WHITE
        # ben vua di co dang chieu doi phuong khong
        co_chieu = in_check(self.board, self.side)
        self.lich_su.append((_khoa(self.board, self.side), co_chieu))
        self.tu_lan_an_quan = 0 if an_quan else self.tu_lan_an_quan + 1

    # -- ket thuc van -------------------------------------------------------

    def trang_thai(self) -> Tuple[str, Optional[str]]:
        """Tra ve (trang thai, ly do). Trang thai la mot trong bon hang so tren."""
        if not self.nuoc_hop_le():
            # Het nuoc di = THUA, khong phai hoa. Day la luat co tuong.
            thua_la_trang = self.side == WHITE
            ly_do = "chieu bi" if self.dang_bi_chieu() else "het nuoc di"
            return (DEN_THANG if thua_la_trang else TRANG_THANG), ly_do

        if self.so_lan_lap() >= SO_LAN_LAP:
            ben_thua = self._ai_chieu_lien_tuc()
            if ben_thua == WHITE:
                return DEN_THANG, "Trang chieu lien tuc"
            if ben_thua == BLACK:
                return TRANG_THANG, "Den chieu lien tuc"
            return HOA, "lap the co 3 lan"

        if self.tu_lan_an_quan >= SO_NUOC_HOA:
            return HOA, f"{SO_NUOC_HOA} nuoc khong an quan"

        return DANG_CHOI, None

    def _ai_chieu_lien_tuc(self) -> Optional[str]:
        """Trong chu ky lap vua roi, co ben nao chieu o MOI nuoc cua minh khong.

        Neu co thi ben do bi xu thua theo luat co tuong. Xet tu lan dau tien
        gap the co hien tai toi bay gio.
        """
        k = _khoa(self.board, self.side)
        dau = next(i for i, (x, _) in enumerate(self.lich_su) if x == k)
        chuoi = self.lich_su[dau + 1:]
        if not chuoi:
            return None
        # Nuoc thu i trong chuoi la cua ben nao: sau the co o vi tri dau, ben di
        # la self.side neu (dau) cung chan le voi hien tai.
        ben_dau = self.side if (len(self.lich_su) - 1 - dau) % 2 == 0 else \
            (BLACK if self.side == WHITE else WHITE)
        chieu = {WHITE: [], BLACK: []}
        ben = ben_dau
        for _, co_chieu in chuoi:
            chieu[ben].append(co_chieu)
            ben = BLACK if ben == WHITE else WHITE
        for b in (WHITE, BLACK):
            if len(chieu[b]) >= 2 and all(chieu[b]):
                return b
        return None
