"""
XuanWu - kiem tra ham danh gia co HIEU DUNG VE VAT CHAT khong.

Vi sao can bai nay: mo hinh chi hoc tu chessdb tung hieu NGUOC - khi Den mat
mot Xe, no cham cho Trang THAP di 38,6 diem, va chi doan dung huong 19% so lan.
Ly do la chessdb gan nhu chi chua the co khai cuoc CAN BANG, mang khong bao gio
thay canh mot ben hon quan nen khong hoc duoc quan he do.

Cach kiem tra: lay the co that, xoa mot quan cua Den, roi xem diem cua Trang co
TANG khong (va nguoc lai voi quan cua Trang). Day la quan he so dang nhat trong
co tuong - ham danh gia nao khong nam duoc thi khong dung duoc.

  python3 tools/test_vat_chat.py                       # ham thu cong
  python3 tools/test_vat_chat.py --nnue weights/nnue_net.npz
  python3 tools/test_vat_chat.py --cnn  weights/eval_net.npz
"""

import argparse
import glob
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.collect_openings import fen_to_board

TEN_QUAN = {"R": "Xe", "H": "Ma", "C": "Phao", "E": "Tuong", "A": "Si", "P": "Tot"}


def doc_the_co(paths, n, rng):
    """Doc mot so the co ngau nhien tu du lieu da thu thap."""
    ra = []
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ra.append(json.loads(line)["fen"])
                except (json.JSONDecodeError, KeyError):
                    continue
                if len(ra) >= n * 30:
                    break
        if len(ra) >= n * 30:
            break
    rng.shuffle(ra)
    return ra[:n * 3]


def xoa_quan(board, quan):
    """Tra ve ban co moi da xoa mot quan 'quan', hoac None neu khong co."""
    for r in range(10):
        for c in range(9):
            if board[r][c] == quan:
                moi = [row[:] for row in board]
                moi[r][c] = "."
                return moi
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Kiem tra hieu biet ve vat chat")
    ap.add_argument("--nnue", default=None, help="Duong dan .npz mang NNUE")
    ap.add_argument("--cnn", default=None, help="Duong dan .npz mang CNN")
    ap.add_argument("--so-the", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if args.nnue:
        from engine.nnue_net import MangNnue
        danh_gia = MangNnue(args.nnue).evaluate
        ten = f"mang NNUE ({args.nnue})"
    elif args.cnn:
        from engine.nnue import NnueEvaluator
        danh_gia = NnueEvaluator(args.cnn).evaluate
        ten = f"mang CNN ({args.cnn})"
    else:
        from engine.evaluate import evaluate as danh_gia
        ten = "ham danh gia thu cong"

    rng = random.Random(args.seed)
    paths = (sorted(glob.glob("data/data_pikafish_s*.jsonl"))
             + ["data/data_openings_chessdb.jsonl"])
    fens = doc_the_co(paths, args.so_the, rng)
    if not fens:
        print("LOI: khong doc duoc the co nao"); return

    print(f"Danh gia: {ten}")
    print(f"Kiem tra tren toi da {args.so_the} the co moi loai quan\n")
    print(f"{'Quan bi xoa':<22}{'Doi diem TB':>13}{'Dung huong':>13}{'So the':>9}")
    print("-" * 57)

    tong_dung = tong_ca = 0
    for quan_hoa in ("R", "H", "C"):
        for ben, chu in (("Den", quan_hoa.lower()), ("Trang", quan_hoa)):
            # xoa quan cua Den -> Trang loi -> diem PHAI TANG
            # xoa quan cua Trang -> Trang thiet -> diem PHAI GIAM
            mong_doi_tang = (ben == "Den")
            tong, dung, dem = 0.0, 0, 0
            for fen in fens:
                if dem >= args.so_the:
                    break
                board, side = fen_to_board(fen)
                sau = xoa_quan(board, chu)
                if sau is None:
                    continue
                truoc_d = danh_gia(board, side)
                sau_d = danh_gia(sau, side)
                delta = sau_d - truoc_d
                tong += delta
                if (delta > 0) == mong_doi_tang and delta != 0:
                    dung += 1
                dem += 1
            if dem == 0:
                continue
            tong_dung += dung
            tong_ca += dem
            nhan = f"{TEN_QUAN[quan_hoa]} cua {ben}"
            dau = "+" if tong / dem >= 0 else ""
            print(f"{nhan:<22}{dau}{tong/dem:>12.1f}{dung/dem*100:>12.0f}%{dem:>9}")

    print("-" * 57)
    ti_le = tong_dung / tong_ca * 100 if tong_ca else 0
    print(f"{'TONG':<22}{'':>13}{ti_le:>12.0f}%{tong_ca:>9}")
    print()
    if ti_le >= 95:
        print("KET LUAN: hieu dung ve vat chat.")
    elif ti_le >= 70:
        print("KET LUAN: hieu phan lon nhung con nham dang ke.")
    else:
        print("KET LUAN: KHONG nam duoc quan he vat chat - khong dung duoc.")


if __name__ == "__main__":
    main()
