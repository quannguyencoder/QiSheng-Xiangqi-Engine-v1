"""
QiSheng - dung SACH KHAI CUOC tu du lieu da co.

Khi thu thap 16 trieu the co, moi lan goi Pikafish deu tra ve CA diem CA nuoc
di tot nhat, va ta da luu ca hai. Truong best_move do tu truoc toi nay chua
dung den. Day la mot cuon sach khai cuoc do Pikafish depth 10 soan san, khong
ton them mot lan goi engine nao.

Loi cua sach khai cuoc:
  - Nhung nuoc dau di theo Pikafish thay vi theo search nong cua ta
  - Khong ton thoi gian nghi o khai cuoc, danh het thoi gian cho trung cuoc
  - Tranh cac bay khai cuoc ma search depth 6 khong nhin thay

Luu gon: khong luu chuoi FEN (dai, cham) ma luu ma bam Zobrist 64 bit va nuoc
di nen trong 16 bit. Moi muc 10 byte thay vi ~90 byte. Tra cuu bang tim kiem
nhi phan tren mang da sap xep.
"""

import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.search import board_hash
from tools.collect_openings import fen_to_board, iccs_to_move


def nen_nuoc_di(mv) -> int:
    """(r0,c0,r1,c1) -> 16 bit: 7 bit o di + 7 bit o den."""
    r0, c0, r1, c1 = mv
    return ((r0 * 9 + c0) << 7) | (r1 * 9 + c1)


def giai_nuoc_di(ma: int):
    di, den = (ma >> 7) & 127, ma & 127
    return (di // 9, di % 9, den // 9, den % 9)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dung sach khai cuoc tu du lieu da co")
    ap.add_argument("--min-quan", type=int, default=30,
                    help="So quan toi thieu de coi la khai cuoc (32 = rat som)")
    ap.add_argument("--output", default="weights/sach_khai_cuoc.npz")
    ap.add_argument("--max-muc", type=int, default=3_000_000)
    args = ap.parse_args()

    paths = (sorted(glob.glob("data/data_pikafish_s*.jsonl"))
             + ["data/data_openings_chessdb.jsonl"])
    sach = {}
    doc = bo_qua = loi = 0
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                doc += 1
                mv_iccs = d.get("best_move")
                if not mv_iccs:
                    continue
                fen = d["fen"]
                if sum(1 for ch in fen.split()[0] if ch.isalpha()) < args.min_quan:
                    bo_qua += 1
                    continue
                try:
                    board, side = fen_to_board(fen)
                    mv = iccs_to_move(mv_iccs)
                except Exception:
                    loi += 1
                    continue
                sach[board_hash(board, side)] = nen_nuoc_di(mv)
                if len(sach) >= args.max_muc:
                    break
        print(f"  {p}: sach co {len(sach):,} muc", flush=True)
        if len(sach) >= args.max_muc:
            break

    khoa = np.fromiter(sach.keys(), dtype=np.uint64, count=len(sach))
    gia_tri = np.fromiter(sach.values(), dtype=np.uint16, count=len(sach))
    thu_tu = np.argsort(khoa)          # sap xep de tra cuu nhi phan
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    np.savez_compressed(args.output, khoa=khoa[thu_tu], nuoc=gia_tri[thu_tu])

    mb = os.path.getsize(args.output) / 1e6
    print(f"\nDoc {doc:,} dong | bo qua {bo_qua:,} (khong phai khai cuoc) | loi {loi:,}")
    print(f"Sach: {len(sach):,} the co -> {args.output} ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
