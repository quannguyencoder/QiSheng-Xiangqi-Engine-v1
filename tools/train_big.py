"""
QiSheng - huan luyen mang danh gia tren tap du lieu lon.

Khac tools/train.py o mot diem quan trong: trich dac trung MOT LAN roi giu
trong bo nho dang uint8, thay vi goi fen_to_tensor lai o moi epoch. Voi hang
trieu mau, viec trich dac trung bang Python la nut that lon nhat - lam mot
lan roi tai su dung giup moi epoch sau do nhanh gap nhieu lan.

Bo nho: dac trung la one-hot (chi 0 va 1) nen duoc NEN THANH BIT - moi the co
chi ton 1350 bit = 169 byte thay vi 1350 byte, nho di 8 lan. Nho vay ca 8 trieu
mau chi chiem ~1,35 GB thay vi 10,8 GB, vua voi may 16 GB. Moi batch duoc giai
nen bang np.unpackbits (vector hoa, rat nhanh).
"""

import argparse
import glob
import json
import os
import random
import sys
import time

import numpy as np
import torch
from torch import nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.train import EvalNet

PIECE_ORDER = "RHEAKCP"
FEN_TO_INTERNAL = {"N": "H", "B": "E"}
_IDX = {p: i for i, p in enumerate(PIECE_ORDER)}


def fen_to_uint8(fen: str) -> np.ndarray:
    planes = np.zeros((15, 10, 9), dtype=np.uint8)
    placement, side = fen.split(" ")[:2]
    for r, row_str in enumerate(placement.split("/")):
        c = 0
        for ch in row_str:
            if ch.isdigit():
                c += int(ch)
                continue
            upper = ch.upper()
            idx = _IDX[FEN_TO_INTERNAL.get(upper, upper)]
            planes[idx if ch.isupper() else 7 + idx, r, c] = 1
            c += 1
    if side == "w":
        planes[14, :, :] = 1
    return planes


def load_rows(paths, limit, rng):
    rows = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    rows.append((d["fen"], d["score"]))
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"  {path}: tong {len(rows):,} mau", flush=True)
    # khu trung lap the co
    seen, uniq = set(), []
    for fen, sc in rows:
        if fen not in seen:
            seen.add(fen)
            uniq.append((fen, sc))
    rng.shuffle(uniq)
    return uniq[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="Huan luyen tren tap du lieu lon")
    ap.add_argument("--data", nargs="+", default=None)
    ap.add_argument("--limit", type=int, default=1_000_000, help="So mau toi da dua vao huan luyen")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-split", type=float, default=0.05)
    ap.add_argument("--checkpoint", default="weights/eval_net.pt")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    paths = args.data or (sorted(glob.glob("data/data_pikafish_s*.jsonl"))
                          + sorted(glob.glob("data/data_crawl_s*.jsonl"))
                          + ["data/data_openings_chessdb.jsonl", "data/training_set.jsonl"])
    print("Doc du lieu...", flush=True)
    rows = load_rows(paths, args.limit, rng)
    n = len(rows)
    print(f"Dung {n:,} mau doc nhat", flush=True)

    print("Trich dac trung (mot lan duy nhat)...", flush=True)
    t0 = time.time()
    X = np.zeros((n, 169), dtype=np.uint8)          # 1350 bit -> 169 byte
    y = np.zeros((n, 1), dtype=np.float32)
    for i, (fen, sc) in enumerate(rows):
        X[i] = np.packbits(fen_to_uint8(fen).reshape(-1))
        y[i, 0] = sc / 1000.0
        if (i + 1) % 200_000 == 0:
            print(f"  {i+1:,}/{n:,} ({time.time()-t0:.0f}s)", flush=True)
    print(f"Xong trich dac trung: {time.time()-t0:.0f}s, {X.nbytes/1e9:.2f} GB "
          f"(da nen bit; neu khong nen se la {n*1350/1e9:.1f} GB)", flush=True)


    def unpack(batch: np.ndarray) -> np.ndarray:
        """169 byte -> 15x10x9 float32, giai nen theo ca lo mot luc."""
        bits = np.unpackbits(batch, axis=1)[:, :1350]
        return bits.reshape(-1, 15, 10, 9).astype(np.float32)

    n_val = max(1, int(n * args.val_split))
    Xtr, ytr = X[n_val:], y[n_val:]
    Xva, yva = X[:n_val], y[:n_val]
    print(f"train {len(Xtr):,} | val {len(Xva):,}", flush=True)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = EvalNet().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    def run_val():
        model.eval()
        tot, cnt = 0.0, 0
        with torch.no_grad():
            for i in range(0, len(Xva), 4096):
                xb = torch.from_numpy(unpack(Xva[i:i+4096])).to(device)
                yb = torch.from_numpy(yva[i:i+4096]).to(device)
                tot += loss_fn(model(xb), yb).item() * len(xb)
                cnt += len(xb)
        return tot / cnt

    best, bad = float("inf"), 0
    order = np.arange(len(Xtr))
    for ep in range(1, args.epochs + 1):
        model.train()
        np.random.shuffle(order)
        t = time.time()
        tot, cnt = 0.0, 0
        for i in range(0, len(order), args.batch_size):
            idx = order[i:i+args.batch_size]
            xb = torch.from_numpy(unpack(Xtr[idx])).to(device)
            yb = torch.from_numpy(ytr[idx]).to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
            cnt += len(idx)
        vl = run_val()
        mark = ""
        if vl < best:
            best, bad, mark = vl, 0, " *"
            os.makedirs(os.path.dirname(args.checkpoint) or ".", exist_ok=True)
            torch.save(model.state_dict(), args.checkpoint)
        else:
            bad += 1
        print(f"Epoch {ep:2d}: train {tot/cnt:.5f} val {vl:.5f}"
              f"  (RMSE {vl**0.5*1000:.0f} diem, {time.time()-t:.0f}s){mark}", flush=True)
        if bad >= args.patience:
            print(f"Dung som o epoch {ep}", flush=True)
            break

    print(f"Model tot nhat: val {best:.5f} (RMSE {best**0.5*1000:.0f} diem) -> {args.checkpoint}")


if __name__ == "__main__":
    main()
