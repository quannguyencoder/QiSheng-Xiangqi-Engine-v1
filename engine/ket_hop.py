"""
QiSheng - tron ham danh gia thu cong voi mang no-ron.

Vi sao can: do doi khang cho thay mang NNUE cham diem chinh xac hon (sai so
100 diem so voi Pikafish) va chay nhanh hon, nhung DANH CO KEM HON ham thu
cong. Ly do khong phai mang dot, ma la khi chon nuoc di thi cai can la XEP
HANG DUNG giua cac nuoc anh em, khong phai do chinh xac tuyet doi.

Ham thu cong sai nhieu nhung sai CO HE THONG (luon dem vat chat cung mot
kieu), nen thu tu giua hai nuoc di van dung. Mang sai it hon nhung sai NGAU
NHIEN, va chenh lech that giua hai nuoc di o do sau nong thuong nho hon nhieu
so voi nhieu cua mang.

Cach tron nay giu tin hieu vat chat nhat quan cua ham thu cong, dong thoi them
tri thuc vi tri ma mang hoc duoc tu 16 trieu the co Pikafish cham diem.
"""

from typing import Callable

from engine.board import Board


def tao_ham_tron(ham_thu_cong: Callable, ham_mang: Callable,
                 trong_so_mang: float = 0.5, hieu_chinh: bool = True) -> Callable:
    """Tra ve ham danh gia = (1-w) * thu_cong + w * mang.

    trong_so_mang = 0.0 -> hoan toan thu cong
    trong_so_mang = 1.0 -> hoan toan mang

    hieu_chinh: dich ket qua sao cho THE CO KHOI DAU dung bang 505 diem.
    Can buoc nay vi mang khong hoc duoc chinh xac moc do - no cham the co khoi
    dau 545, tron 50/50 ra 525 - trong khi 505 la moc chuan cua thang diem
    (500 can bang + 5 diem tempo cho ben Trang). Do lech nay la mot HANG SO
    cong vao moi the co, nen tru di khong lam thay doi thu tu giua cac nuoc di,
    tuc khong anh huong luc co, chi dua thang diem ve dung chuan.
    """
    w = max(0.0, min(1.0, trong_so_mang))
    mot_tru_w = 1.0 - w

    lech = 0.0
    if hieu_chinh:
        from engine.board import start_board
        b = start_board()
        tho = mot_tru_w * ham_thu_cong(b, "w") + w * ham_mang(b, "w")
        lech = 505.0 - tho

    def danh_gia(board: Board, side_to_move: str) -> int:
        a = ham_thu_cong(board, side_to_move)
        b = ham_mang(board, side_to_move)
        # Giu trong [1, 999]: 0 va 1000 danh rieng cho chieu het da xac nhan
        return max(1, min(999, int(round(mot_tru_w * a + w * b + lech))))

    return danh_gia
