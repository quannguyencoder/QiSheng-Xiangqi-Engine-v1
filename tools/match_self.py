"""
QiSheng - cho HAI PHIEN BAN QiSheng danh truc tiep voi nhau.

Vi sao can cai nay thay vi chi do qua Pikafish: cau hoi that su la "ham danh
gia nao manh hon", ma do qua doi thu thu ba chi tra loi gian tiep. Cho hai
phien ban chi khac nhau O HAM DANH GIA danh truc tiep thi moi chenh lech deu
quy ve dung mot nguyen nhan - khong con bien so nao khac.

Moi the co khai cuoc duoc danh HAI lan, doi mau quan, de triet tieu loi the
cua rieng the co do. Ca hai ben deu tat dinh nen khong can lap lai.

  python3 tools/match_self.py --a thu-cong --b nnue:weights/nnue_net.npz
"""

import argparse
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.board import WHITE, BLACK, start_board, legal_moves, make_move
from engine import search as search_mod
from engine.evaluate import material_score
from tools.collect_openings import fen_to_board


def tao_ham_danh_gia(spec: str):
    """'thu-cong' | 'nnue:<duong dan>' | 'cnn:<duong dan>' -> (ham, ten)."""
    if spec == "thu-cong":
        from engine.evaluate import evaluate
        return evaluate, "ham thu cong"
    kieu, _, path = spec.partition(":")
    if kieu == "nnue":
        from engine.nnue_net import MangNnue
        return MangNnue(path).evaluate, f"mang NNUE ({os.path.basename(path)})"
    if kieu == "tron-nhanh":
        # Giong "tron" nhung TAT tinh co dong trong nua thu cong - nhanh 1,54x.
        # Gia thiet: mang da hoc duoc tinh co dong tu du lieu nen khong can tinh lai.
        duong, _, w = path.rpartition(":")
        from engine import evaluate as ev
        from engine.ket_hop import tao_ham_tron
        from engine.nnue_net import MangNnue
        tso = float(w)
        def thu_cong_nhanh(b, s):
            ev.dat_co_dong(False)
            return ev.evaluate(b, s)
        return (tao_ham_tron(thu_cong_nhanh, MangNnue(duong).evaluate, tso),
                f"tron {int((1-tso)*100)}/{int(tso*100)} KHONG co dong")
    if kieu == "tron-c":
        # Duong nhanh: ca ham thu cong, mang, va tron deu chay trong C.
        duong, _, w = path.rpartition(":")
        from engine.ket_hop import tao_ham_tron_c
        f = tao_ham_tron_c(duong, float(w))
        if f is None:
            raise SystemExit("Khong co thu vien C - chay csrc/build.sh truoc")
        return f, f"tron {int((1-float(w))*100)}/{int(float(w)*100)} (C)"
    if kieu == "tron":
        # tron:<duong dan mang>:<trong so>   vi du tron:weights/x.npz:0.5
        duong, _, w = path.rpartition(":")
        from engine import evaluate as ev
        from engine.ket_hop import tao_ham_tron
        from engine.nnue_net import MangNnue
        tso = float(w)
        def thu_cong_day_du(b, s):
            ev.dat_co_dong(True)
            return ev.evaluate(b, s)
        return (tao_ham_tron(thu_cong_day_du, MangNnue(duong).evaluate, tso),
                f"tron {int((1-tso)*100)}% thu cong + {int(tso*100)}% mang "
                f"({os.path.basename(duong)})")
    if kieu == "cnn":
        from engine.nnue import NnueEvaluator
        return NnueEvaluator(path).evaluate, f"mang CNN ({os.path.basename(path)})"
    raise SystemExit(f"Khong hieu '{spec}'. Dung: thu-cong | nnue:<path> | cnn:<path>")


def doc_khai_cuoc(path: str, so_van: int, seed: int):
    fens = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    fens.append(json.loads(line)["fen"])
                except (json.JSONDecodeError, KeyError):
                    continue
    if not fens:
        return [None] * so_van
    random.Random(seed).shuffle(fens)
    can = (so_van + 1) // 2
    ra = []
    for f in (fens * (can // len(fens) + 1))[:can]:
        ra.extend([f, f])
    return ra[:so_van]


NGUONG_XU = 400          # hon nhau tu mot con Ma tro len thi xu thang


def xu_the_co(board, a_cam_trang: bool) -> float:
    """Het so nuoc cho phep -> xu theo VAT CHAT thay vi tuyen bo hoa het.

    Neu khong co buoc nay, gan nhu moi van deu cham tran so nuoc va bi tinh la
    hoa, khien ti le diem luon ~50% du mot ben manh hon han - phep do tro nen
    vo nghia. Cac giai engine deu xu theo vat chat o tinh huong nay.
    """
    chenh = material_score(board)           # duong = Trang loi
    chenh_cua_a = chenh if a_cam_trang else -chenh
    if chenh_cua_a >= NGUONG_XU:
        return 1.0
    if chenh_cua_a <= -NGUONG_XU:
        return 0.0
    return 0.5


def danh_mot_van(ham_a, ham_b, a_cam_trang: bool, depth: int,
                 max_plies: int, fen_dau, depth_b: int = 0):
    """Tra ve 1.0 neu A thang, 0.5 hoa, 0.0 thua."""
    board, side = (fen_to_board(fen_dau) if fen_dau else (start_board(), WHITE))
    for _ in range(max_plies):
        if not legal_moves(board, side):
            a_den_luot = (side == WHITE) == a_cam_trang
            return 0.0 if a_den_luot else 1.0
        a_den_luot = (side == WHITE) == a_cam_trang
        search_mod.set_evaluator(ham_a if a_den_luot else ham_b)
        d = depth if a_den_luot else (depth_b or depth)
        _, mv = search_mod.evaluate_current_position(board, side, depth=d)
        if mv is None:
            return 0.0 if a_den_luot else 1.0
        board = make_move(board, mv)
        side = BLACK if side == WHITE else WHITE
    return xu_the_co(board, a_cam_trang)


def main() -> None:
    ap = argparse.ArgumentParser(description="QiSheng vs QiSheng, khac ham danh gia")
    ap.add_argument("--a", default="thu-cong")
    ap.add_argument("--b", required=True)
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--depth-b", type=int, default=0,
                    help="Do sau rieng cho ben B (0 = giong ben A). Dung de kiem "
                         "chung cat tia: tim sau hon PHAI manh hon, neu khong thi "
                         "cat tia dang bo sot nuoc hay.")
    ap.add_argument("--max-plies", type=int, default=120)
    ap.add_argument("--khai-cuoc", default="data/data_openings_chessdb.jsonl")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    ham_a, ten_a = tao_ham_danh_gia(args.a)
    ham_b, ten_b = tao_ham_danh_gia(args.b)
    khai = doc_khai_cuoc(args.khai_cuoc, args.games, args.seed)
    print(f"A = {ten_a}")
    print(f"B = {ten_b}")
    print(f"{args.games} van, A depth {args.depth} vs B depth "
          f"{args.depth_b or args.depth}, tu "
          f"{len({f for f in khai if f})} the co khai cuoc khac nhau\n", flush=True)

    diem, kq = 0.0, []
    t0 = time.time()
    for g in range(args.games):
        a_trang = (g % 2 == 0)
        r = danh_mot_van(ham_a, ham_b, a_trang, args.depth, args.max_plies,
                         khai[g], args.depth_b)
        diem += r
        kq.append(r)
        ten = {1.0: "A THANG", 0.5: "hoa", 0.0: "B thang"}[r]
        print(f"  van {g+1}/{args.games}: A cam {'Trang' if a_trang else 'Den'}"
              f" -> {ten}  (A: {diem}/{g+1})", flush=True)

    n = len(kq)
    ti_le = diem / n
    print(f"\nA duoc {diem}/{n} = {ti_le:.1%} "
          f"({kq.count(1.0)} thang, {kq.count(0.5)} hoa, {kq.count(0.0)} thua)")
    print(f"Thoi gian: {(time.time()-t0)/60:.1f} phut")
    # sai so chuan cua ti le diem, de khong doc qua nhieu vao ket qua it van
    se = math.sqrt(max(ti_le * (1 - ti_le), 1e-9) / n)
    print(f"Sai so chuan: +/-{se*100:.1f} diem phan tram")
    if 0.0 < ti_le < 1.0:
        elo = -400 * math.log10(1 / ti_le - 1)
        lo = -400 * math.log10(1 / max(min(ti_le - 1.96*se, 0.999), 0.001) - 1)
        hi = -400 * math.log10(1 / max(min(ti_le + 1.96*se, 0.999), 0.001) - 1)
        print(f"Chenh lech Elo cua A so voi B: {elo:+.0f} "
              f"(khoang tin cay 95%: {lo:+.0f} den {hi:+.0f})")
    else:
        print("Mot ben thang tuyet doi - can them van de do chinh xac.")


if __name__ == "__main__":
    main()
