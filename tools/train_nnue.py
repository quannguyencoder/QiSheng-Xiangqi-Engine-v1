"""
QiSheng - huan luyen mang kieu NNUE (thay cho CNN trong tools/train.py).

Vi sao doi kien truc: do thuc te tren may nay cho thay CNN mat 312 us moi lan
danh gia, ham thu cong 89 us, con mang NNUE nay chi mat 20 us khi tinh lai tu
dau va 7,8 us khi cap nhat tang dan. Trong search - noi ham danh gia bi goi
hang chuc nghin lan - khac biet do la rat lon.

Kien truc:
    1260 dac trung nhi phan (14 loai quan x 90 o)
      -> W1: lop "tich luy" 256 chieu    <-- cap nhat tang dan duoc
      -> clipped ReLU [0,1]
      -> ghep them 1 bit ben di          -> 257
      -> W2: 32 chieu, clipped ReLU
      -> W3: 1 chieu -> sigmoid -> thang 0..1000

Diem mau chot la lop W1: khi mot quan di tu o A sang o B, vec-to tich luy chi
can TRU cot ung voi (quan, A) va CONG cot ung voi (quan, B). Khong phai tinh
lai gi khac. Do la ly do NNUE nhanh.

Clipped ReLU (kep trong [0,1]) chu khong phai ReLU thuong: gia tri bi chan tren
nen sau nay luong hoa ve so nguyen duoc ma khong tran so.

Du lieu dung chung voi tools/train_big.py - cung file, cung cach nen bit.
"""

import argparse
import glob
import json
import os
import random
import sys
import time

import math

import numpy as np
import torch
from torch import nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.train_big import fen_to_uint8, load_rows

SO_DAC_TRUNG = 1260          # 14 loai quan x 90 o
SO_TICH_LUY = 256
SO_AN = 32


class NnueNet(nn.Module):
    def __init__(self, so_tich_luy: int = SO_TICH_LUY, so_an: int = SO_AN):
        super().__init__()
        self.w1 = nn.Linear(SO_DAC_TRUNG, so_tich_luy)
        self.w2 = nn.Linear(so_tich_luy + 1, so_an)   # +1 la bit ben di
        self.w3 = nn.Linear(so_an, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """x: (batch, 1261) - 1260 dac trung quan co + 1 bit ben di."""
        quan, ben = x[:, :SO_DAC_TRUNG], x[:, SO_DAC_TRUNG:]
        a = torch.clamp(self.w1(quan), 0.0, 1.0)
        h = torch.clamp(self.w2(torch.cat([a, ben], dim=1)), 0.0, 1.0)
        return torch.sigmoid(self.w3(h))


def giai_nen(batch: np.ndarray) -> np.ndarray:
    """169 byte -> (n, 1261) float32.

    Bit da nen la 15 mat phang 10x9 = 1350 bit. 1260 bit dau la 14 loai quan,
    90 bit cuoi la mat phang "ben di" (toan 1 neu Trang di, toan 0 neu Den).
    Ta chi lay 1 bit dai dien cho mat phang do.
    """
    bits = np.unpackbits(batch, axis=1)[:, :1350].astype(np.float32)
    return np.concatenate([bits[:, :SO_DAC_TRUNG], bits[:, 1260:1261]], axis=1)


def doc_rows_tanh(paths, limit, rng, scale):
    """Doc du lieu va TINH LAI nhan theo thang tanh giong engine.

    Nhan goc trong file duoc tao bang sigmoid(cp/200), thang do bao hoa rat
    som: hon 1 Xe cham 989 diem, hon 2 Xe cham 999,9 - cach nhau 10,9 diem
    trong khi sai so cua mang la 100 diem. Mang khong the phan biet noi, nen
    trong search no cham moi the co lech quan deu ~1000 va het co so chon nuoc.

    Thang tanh(cp/1600) - dung thang engine/scoring.py dang dung - giu khoang
    cach 149 diem giua hon 1 Xe va hon 2 Xe. Do la thang co the hoc duoc.
    """
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
                    cp = d.get("cp")
                    if cp is None:          # du lieu chessdb khong co cp
                        rows.append((d["fen"], d["score"]))
                    else:
                        v = math.tanh(cp / scale) * 495.0
                        rows.append((d["fen"], max(1, min(999, round(500 + v)))))
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"  {path}: tong {len(rows):,} mau", flush=True)
    seen, uniq = set(), []
    for fen, sc in rows:
        if fen not in seen:
            seen.add(fen)
            uniq.append((fen, sc))
    rng.shuffle(uniq)
    return uniq[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="Huan luyen mang kieu NNUE")
    ap.add_argument("--data", nargs="+", default=None)
    ap.add_argument("--limit", type=int, default=16_000_000)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--batch-size", type=int, default=8192)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--val-split", type=float, default=0.05)
    ap.add_argument("--accum", type=int, default=SO_TICH_LUY)
    ap.add_argument("--hidden", type=int, default=SO_AN)
    ap.add_argument("--checkpoint", default="weights/nnue_net.pt")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--thang-tanh", type=float, default=None,
                    help="Tinh lai nhan bang tanh(cp/SCALE) thay vi dung nhan\n"
                         "sigmoid(cp/200) co san. Dung 1600 de khop engine.")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    paths = args.data or (sorted(glob.glob("data/data_pikafish_s*.jsonl"))
                          + sorted(glob.glob("data/data_crawl_s*.jsonl"))
                          + ["data/data_openings_chessdb.jsonl", "data/training_set.jsonl"])
    print("Doc du lieu...", flush=True)
    if args.thang_tanh:
        print(f"Tinh lai nhan theo thang tanh(cp/{args.thang_tanh:.0f})", flush=True)
        rows = doc_rows_tanh(paths, args.limit, rng, args.thang_tanh)
    else:
        rows = load_rows(paths, args.limit, rng)
    n = len(rows)
    print(f"Dung {n:,} mau doc nhat", flush=True)

    print("Trich dac trung (mot lan duy nhat)...", flush=True)
    t0 = time.time()
    X = np.zeros((n, 169), dtype=np.uint8)
    y = np.zeros((n, 1), dtype=np.float32)
    for i, (fen, sc) in enumerate(rows):
        X[i] = np.packbits(fen_to_uint8(fen).reshape(-1))
        y[i, 0] = sc / 1000.0
        if (i + 1) % 1_000_000 == 0:
            print(f"  {i+1:,}/{n:,} ({time.time()-t0:.0f}s)", flush=True)
    del rows
    print(f"Xong: {time.time()-t0:.0f}s, {X.nbytes/1e9:.2f} GB", flush=True)

    n_val = max(1, int(n * args.val_split))
    Xtr, ytr = X[n_val:], y[n_val:]
    Xva, yva = X[:n_val], y[:n_val]
    print(f"train {len(Xtr):,} | val {len(Xva):,}", flush=True)

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = NnueNet(args.accum, args.hidden).to(device)
    so_tham_so = sum(p.numel() for p in model.parameters())
    print(f"Mang NNUE: {so_tham_so:,} tham so "
          f"(CNN cu: 797.313)", flush=True)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    def chay_val():
        model.eval()
        tot, cnt = 0.0, 0
        with torch.no_grad():
            for i in range(0, len(Xva), 16384):
                xb = torch.from_numpy(giai_nen(Xva[i:i+16384])).to(device)
                yb = torch.from_numpy(yva[i:i+16384]).to(device)
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
            xb = torch.from_numpy(giai_nen(Xtr[idx])).to(device)
            yb = torch.from_numpy(ytr[idx]).to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            tot += loss.item() * len(idx)
            cnt += len(idx)
        vl = chay_val()
        mark = ""
        if vl < best:
            best, bad, mark = vl, 0, " *"
            os.makedirs(os.path.dirname(args.checkpoint) or ".", exist_ok=True)
            torch.save({"state_dict": model.state_dict(),
                        "accum": args.accum, "hidden": args.hidden}, args.checkpoint)
        else:
            bad += 1
        print(f"Epoch {ep:2d}: train {tot/cnt:.5f} val {vl:.5f}"
              f"  (RMSE {vl**0.5*1000:.0f} diem, {time.time()-t:.0f}s){mark}", flush=True)
        if bad >= args.patience:
            print(f"Dung som o epoch {ep}", flush=True)
            break

    print(f"Tot nhat: val {best:.5f} (RMSE {best**0.5*1000:.0f} diem) -> {args.checkpoint}")


if __name__ == "__main__":
    main()
