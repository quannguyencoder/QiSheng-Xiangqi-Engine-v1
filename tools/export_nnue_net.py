"""
XuanWu - xuat mang NNUE tu PyTorch (.pt) sang NumPy (.npz).

Sau khi xuat, engine chay bang NumPy, khong can PyTorch luc choi.
Script tu doi chieu PyTorch va NumPy tren nhieu the co ngau nhien - neu hai
cai dat lech nhau thi bao loi ngay chu khong de lot ra ban choi that.
"""

import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.train_nnue import NnueNet, SO_DAC_TRUNG


def main() -> None:
    ap = argparse.ArgumentParser(description="Xuat NNUE .pt -> .npz")
    ap.add_argument("--checkpoint", default="weights/nnue_net.pt")
    ap.add_argument("--output", default="weights/nnue_net.npz")
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu")
    model = NnueNet(ck["accum"], ck["hidden"])
    model.load_state_dict(ck["state_dict"])
    model.eval()
    sd = model.state_dict()

    # PyTorch luu Linear la (ra, vao); NumPy o day nhan (vao, ra) nen phai chuyen vi
    np.savez_compressed(
        args.output,
        w1=sd["w1.weight"].numpy().T, b1=sd["w1.bias"].numpy(),
        w2=sd["w2.weight"].numpy().T, b2=sd["w2.bias"].numpy(),
        w3=sd["w3.weight"].numpy()[0], b3=sd["w3.bias"].numpy()[0],
    )
    print(f"Da xuat {args.checkpoint} -> {args.output} "
          f"({os.path.getsize(args.output)/1e6:.1f} MB)")

    # --- doi chieu hai cai dat tren the co ngau nhien ---
    from engine.board import start_board, legal_moves, make_move, WHITE, BLACK
    from engine.nnue_net import MangNnue, cac_dac_trung

    net = MangNnue(args.output)
    rng = np.random.default_rng(0)
    board, side = start_board(), WHITE
    lech_max = 0.0
    for i in range(60):
        mvs = legal_moves(board, side)
        if not mvs:
            break
        board = make_move(board, mvs[rng.integers(len(mvs))])
        side = BLACK if side == WHITE else WHITE

        x = torch.zeros(1, SO_DAC_TRUNG + 1)
        x[0, cac_dac_trung(board)] = 1.0
        x[0, SO_DAC_TRUNG] = 1.0 if side == WHITE else 0.0
        with torch.no_grad():
            ref = float(model(x)[0, 0]) * 1000
        got = net.evaluate(board, side)
        lech_max = max(lech_max, abs(ref - got))
    print(f"Doi chieu PyTorch vs NumPy tren {i+1} the co: lech lon nhat "
          f"{lech_max:.2f} diem -> {'KHOP' if lech_max < 2 else 'LECH!'}")

    # --- doi chieu cap nhat tang dan vs tinh lai tu dau ---
    board, side = start_board(), WHITE
    acc = net.tich_luy(board)
    lech_inc = 0.0
    for _ in range(60):
        mvs = legal_moves(board, side)
        if not mvs:
            break
        mv = mvs[rng.integers(len(mvs))]
        bo, them = net.thay_doi(board, mv)
        acc = net.cap_nhat(acc, bo, them)
        board = make_move(board, mv)
        side = BLACK if side == WHITE else WHITE
        lech_inc = max(lech_inc, float(np.abs(acc - net.tich_luy(board)).max()))
    print(f"Doi chieu tang dan vs tinh lai: lech lon nhat {lech_inc:.6f} "
          f"-> {'KHOP' if lech_inc < 1e-3 else 'LECH!'}")


if __name__ == "__main__":
    main()
