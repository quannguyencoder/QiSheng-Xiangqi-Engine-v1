"""
XuanWu - huan luyen mang NNUE voi dac trung THEO VI TRI TUONG (kieu HalfKP).

Vi sao doi: mang hien tai chi biet "con Xe o o nay". NNUE that biet "con Xe o o
nay KHI TUONG TA O O KIA" - cung mot con Xe co gia tri rat khac nhau tuy Tuong
dung dau, va mang cu khong co cach nao bieu dien duoc dieu do.

Bang chung ung ho: gap doi so tham so (331k -> 678k) cho DUNG 0 cai thien. Khi
them suc chua ma khong duoc gi, nut that la CACH BIEU DIEN chu khong phai kich
thuoc.

Dac trung: moi quan tren ban dong gop HAI dac trung, mot theo o Tuong Trang va
mot theo o Tuong Den.
    nhom Trang: (o_tuong_trang 0..8, loai quan 0..13, o 0..89)
    nhom Den  : (o_tuong_den  0..8, loai quan 0..13, o 0..89)
Tong 2 x 9 x 14 x 90 = 22.680 dac trung, moi the co bat khoang 64 cai.

Dung nn.EmbeddingBag(mode="sum") - dung la phep cong don cot cua lop tich luy,
va PyTorch chay no rat nhanh tren dau vao thua.
"""

import argparse
import glob
import json
import math
import os
import random
import sys
import time

import numpy as np
import torch
from torch import nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

QUAN = "RHEAKCPrheakcp"
_IDX = {p: i for i, p in enumerate(QUAN)}
FEN_DOI = {"N": "H", "B": "E", "n": "h", "b": "e"}

SO_O_CUNG = 9
SO_DAC_TRUNG = 2 * SO_O_CUNG * 14 * 90        # 22.680
MAX_QUAN = 32
NHOM_DEN = SO_O_CUNG * 14 * 90                # moc bat dau nhom Den


def _o_cung(sq: int, trang: bool) -> int:
    """O Tuong -> chi so 0..8 trong cung cua ben do."""
    r, c = sq // 9, sq % 9
    r0 = 7 if trang else 0
    return (r - r0) * 3 + (c - 3)


def dac_trung_tu_fen(fen: str):
    """FEN -> danh sach chi so dac trung (khoang 64 cai)."""
    dat, ben = fen.split(" ")[:2]
    o_quan = []
    r = 0
    for hang in dat.split("/"):
        c = 0
        for ch in hang:
            if ch.isdigit():
                c += int(ch)
                continue
            q = FEN_DOI.get(ch, ch)
            o_quan.append((_IDX[q], r * 9 + c))
            c += 1
        r += 1
    kw = kb = None
    for i, sq in o_quan:
        if i == 4:
            kw = sq
        elif i == 11:
            kb = sq
    if kw is None or kb is None:
        return None, None
    bw, bb = _o_cung(kw, True), _o_cung(kb, False)
    if not (0 <= bw < 9 and 0 <= bb < 9):
        return None, None
    ra = []
    for i, sq in o_quan:
        ra.append(bw * 14 * 90 + i * 90 + sq)
        ra.append(NHOM_DEN + bb * 14 * 90 + i * 90 + sq)
    return ra, (1.0 if ben == "w" else 0.0)


class MangHalfKP(nn.Module):
    def __init__(self, so_tich_luy=256, so_an=32):
        super().__init__()
        self.tich_luy = nn.EmbeddingBag(SO_DAC_TRUNG, so_tich_luy, mode="sum")
        self.b1 = nn.Parameter(torch.zeros(so_tich_luy))
        self.w2 = nn.Linear(so_tich_luy + 1, so_an)
        self.w3 = nn.Linear(so_an, 1)

    def forward(self, idx, offsets, ben):
        a = torch.clamp(self.tich_luy(idx, offsets) + self.b1, 0.0, 1.0)
        h = torch.clamp(self.w2(torch.cat([a, ben], dim=1)), 0.0, 1.0)
        return torch.sigmoid(self.w3(h))


def doc_du_lieu(paths, limit, rng, scale):
    rows = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    cp = d.get("cp")
                    y = (max(1, min(999, round(500 + math.tanh(cp / scale) * 495)))
                         if cp is not None else d["score"])
                    rows.append((d["fen"], y))
                except (json.JSONDecodeError, KeyError):
                    continue
        print(f"  {path}: {len(rows):,}", flush=True)
        if len(rows) >= limit * 3:
            break
    seen, uniq = set(), []
    for fen, y in rows:
        if fen not in seen:
            seen.add(fen)
            uniq.append((fen, y))
    rng.shuffle(uniq)
    return uniq[:limit]


def main() -> None:
    ap = argparse.ArgumentParser(description="Huan luyen NNUE dac trung theo Tuong")
    ap.add_argument("--limit", type=int, default=8_000_000)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--patience", type=int, default=4)
    ap.add_argument("--batch-size", type=int, default=8192)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--accum", type=int, default=256)
    ap.add_argument("--hidden", type=int, default=32)
    ap.add_argument("--thang-tanh", type=float, default=1600.0)
    ap.add_argument("--checkpoint", default="weights/halfkp.pt")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)
    paths = (sorted(glob.glob("data/data_pikafish_s*.jsonl"))
             + sorted(glob.glob("data/data_xuanwu_s*.jsonl")))
    print("Doc du lieu...", flush=True)
    rows = doc_du_lieu(paths, args.limit, rng, args.thang_tanh)
    print(f"Dung {len(rows):,} mau", flush=True)

    print("Trich dac trung...", flush=True)
    t0 = time.time()
    n = len(rows)
    IDX = np.zeros((n, MAX_QUAN * 2), dtype=np.int16)  # 22.680 < 32.767
    SO = np.zeros(n, dtype=np.int16)
    BEN = np.zeros((n, 1), dtype=np.float32)
    Y = np.zeros((n, 1), dtype=np.float32)
    hop_le = 0
    for i, (fen, y) in enumerate(rows):
        dt, ben = dac_trung_tu_fen(fen)
        if dt is None or len(dt) > MAX_QUAN * 2:
            continue
        IDX[hop_le, :len(dt)] = dt
        SO[hop_le] = len(dt)
        BEN[hop_le, 0] = ben
        Y[hop_le, 0] = y / 1000.0
        hop_le += 1
        if (i + 1) % 2_000_000 == 0:
            print(f"  {i+1:,}/{n:,} ({time.time()-t0:.0f}s)", flush=True)
    IDX, SO, BEN, Y = IDX[:hop_le], SO[:hop_le], BEN[:hop_le], Y[:hop_le]
    print(f"Xong: {hop_le:,} mau hop le, {time.time()-t0:.0f}s, "
          f"{IDX.nbytes/1e9:.2f} GB", flush=True)

    n_val = max(1, hop_le // 20)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = MangHalfKP(args.accum, args.hidden).to(device)
    print(f"Tham so: {sum(p.numel() for p in model.parameters()):,}", flush=True)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    loss_fn = nn.MSELoss()

    def lo(i0, i1):
        so = SO[i0:i1].astype(np.int64)
        off = np.zeros(len(so), dtype=np.int64)
        off[1:] = np.cumsum(so)[:-1]
        phang = np.concatenate([IDX[i0 + k, :so[k]] for k in range(len(so))])
        return (torch.from_numpy(phang.astype(np.int64)).to(device),
                torch.from_numpy(off).to(device),
                torch.from_numpy(BEN[i0:i1]).to(device),
                torch.from_numpy(Y[i0:i1]).to(device))

    best, bad = float("inf"), 0
    for ep in range(1, args.epochs + 1):
        model.train()
        t = time.time()
        tot = cnt = 0
        for i in range(n_val, hop_le, args.batch_size):
            j = min(i + args.batch_size, hop_le)
            idx, off, ben, y = lo(i, j)
            opt.zero_grad()
            loss = loss_fn(model(idx, off, ben), y)
            loss.backward()
            opt.step()
            tot += loss.item() * (j - i)
            cnt += j - i
        sched.step()
        model.eval()
        vt = vc = 0
        with torch.no_grad():
            for i in range(0, n_val, 16384):
                j = min(i + 16384, n_val)
                idx, off, ben, y = lo(i, j)
                vt += loss_fn(model(idx, off, ben), y).item() * (j - i)
                vc += j - i
        vl = vt / vc
        mark = ""
        if vl < best:
            best, bad, mark = vl, 0, " *"
            os.makedirs(os.path.dirname(args.checkpoint) or ".", exist_ok=True)
            torch.save({"state_dict": model.state_dict(), "accum": args.accum,
                        "hidden": args.hidden}, args.checkpoint)
        else:
            bad += 1
        print(f"Epoch {ep:2d}: train {tot/cnt:.5f} val {vl:.5f} "
              f"(RMSE {vl**0.5*1000:.0f} diem, {time.time()-t:.0f}s){mark}", flush=True)
        if bad >= args.patience:
            print(f"Dung som o epoch {ep}", flush=True)
            break
    print(f"Tot nhat: val {best:.5f} (RMSE {best**0.5*1000:.0f}) -> {args.checkpoint}")


if __name__ == "__main__":
    main()
