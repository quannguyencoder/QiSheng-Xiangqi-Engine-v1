"""
QiSheng - xuat mang da huan luyen tu PyTorch (.pt) sang NumPy (.npz).

Sau khi xuat, engine danh gia bang engine/nnue.py ma khong can PyTorch -
luc choi chi can NumPy.
"""

import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.train import EvalNet


def main() -> None:
    ap = argparse.ArgumentParser(description="Xuat .pt -> .npz cho engine/nnue.py")
    ap.add_argument("--checkpoint", default="weights/eval_net.pt")
    ap.add_argument("--output", default="weights/eval_net.npz")
    args = ap.parse_args()

    model = EvalNet()
    model.load_state_dict(torch.load(args.checkpoint, map_location="cpu"))
    model.eval()

    sd = model.state_dict()
    np.savez_compressed(
        args.output,
        c0w=sd["conv.0.weight"].numpy(), c0b=sd["conv.0.bias"].numpy(),
        c1w=sd["conv.2.weight"].numpy(), c1b=sd["conv.2.bias"].numpy(),
        c2w=sd["conv.4.weight"].numpy(), c2b=sd["conv.4.bias"].numpy(),
        f0w=sd["fc.1.weight"].numpy(), f0b=sd["fc.1.bias"].numpy(),
        f1w=sd["fc.3.weight"].numpy()[0], f1b=sd["fc.3.bias"].numpy()[0],
    )
    size = os.path.getsize(args.output) / 1e6
    print(f"Da xuat {args.checkpoint} -> {args.output} ({size:.1f} MB)")

    # Kiem tra hai cai dat cho cung ket qua
    from engine.board import start_board
    from engine.nnue import NnueEvaluator
    from tools.train import fen_to_tensor

    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"
    with torch.no_grad():
        ref = float(model(fen_to_tensor(fen).unsqueeze(0))[0, 0]) * 1000
    got = NnueEvaluator(args.output).evaluate(start_board(), "w")
    print(f"Kiem tra doi chieu: PyTorch {ref:.1f} vs NumPy {got} "
          f"-> {'KHOP' if abs(ref - got) < 2 else 'LECH!'}")


if __name__ == "__main__":
    main()
