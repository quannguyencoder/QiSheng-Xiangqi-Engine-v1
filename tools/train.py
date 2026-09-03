"""
Huan luyen mang danh gia the co (CNN nho) tren du lieu thu thap tu chessdb.cn
(xem collect_xiangqi_data.py). Day la lop "hoc sau" bo sung cho ham danh gia
thu cong trong qisheng.py - khong dung engine co ngoai luc chay/thi dau,
chi dung PyTorch (thu vien ML tong quat) de train mang cua rieng minh.

Input: 15 mat phang 10x9 (7 loai quan x 2 mau + 1 mat phang "ben nao di").
Output: diem 0..1000 (goc nhin Trang), khop thang diem cua qisheng.py.
"""

import argparse
import json
import os
import random

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.collect_openings import FEN_TO_INTERNAL

PIECE_ORDER = "RHEAKCP"  # Xe, Ma, Tuong(elephant), Si, Tuong soai, Phao, Tot


def fen_to_tensor(fen: str) -> torch.Tensor:
    placement, side = fen.split(" ")
    planes = torch.zeros(15, 10, 9)
    for r, row in enumerate(placement.split("/")):
        c = 0
        for ch in row:
            if ch.isdigit():
                c += int(ch)
                continue
            upper = ch.upper()
            internal = FEN_TO_INTERNAL.get(upper, upper)
            plane_idx = PIECE_ORDER.index(internal)
            offset = 0 if ch.isupper() else 7
            planes[offset + plane_idx, r, c] = 1.0
            c += 1
    planes[14, :, :] = 1.0 if side == "w" else 0.0
    return planes


class XiangqiDataset(Dataset):
    def __init__(self, paths):
        if isinstance(paths, str):
            paths = [paths]
        self.examples = []
        self.by_phase = {}
        for path in paths:
            if not os.path.exists(path):
                print(f"  (bo qua {path}: khong ton tai)")
                continue
            n = 0
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    self.examples.append((d["fen"], d["score"]))
                    phase = d.get("phase", "khai_cuoc")
                    self.by_phase[phase] = self.by_phase.get(phase, 0) + 1
                    n += 1
            print(f"  {path}: {n} mau")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int):
        fen, score = self.examples[idx]
        return fen_to_tensor(fen), torch.tensor([score / 1000.0], dtype=torch.float32)


class EvalNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(15, 32, 3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 10 * 9, 128), nn.ReLU(),
            nn.Linear(128, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.fc(self.conv(x)))


def run_epoch(model, loader, device, optimizer=None) -> float:
    training = optimizer is not None
    model.train(training)
    total_loss, total_n = 0.0, 0
    loss_fn = nn.MSELoss(reduction="sum")
    with torch.set_grad_enabled(training):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            loss = loss_fn(pred, y)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item()
            total_n += x.size(0)
    return total_loss / total_n


def main() -> None:
    parser = argparse.ArgumentParser(description="Huan luyen mang danh gia the co")
    parser.add_argument("--data", type=str, nargs="+",
                        default=["data/data_openings_chessdb.jsonl", "data/training_set.jsonl"]
                                + sorted(__import__("glob").glob("data/data_crawl_s*.jsonl")),
                        help="Mot hoac nhieu file JSONL du lieu")
    parser.add_argument("--epochs", type=int, default=200, help="So epoch toi da (co early stopping)")
    parser.add_argument("--patience", type=int, default=20, help="Dung neu val loss khong giam sau tung nay epoch")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--checkpoint", type=str, default="weights/eval_net.pt")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    random.seed(args.seed)

    dataset = XiangqiDataset(args.data)
    print(f"Tong so the co: {len(dataset)}")
    if dataset.by_phase:
        print("  Phan bo giai doan: " + ", ".join(
            f"{k}={v}" for k, v in sorted(dataset.by_phase.items())))
    if len(dataset) < 20:
        print("Qua it du lieu de train co y nghia - script van chay de kiem tra pipeline,"
              " nhung ket qua chi la smoke test, chua phai model that.")

    val_size = max(1, int(len(dataset) * args.val_split)) if len(dataset) > 1 else 0
    train_size = len(dataset) - val_size
    train_set, val_set = random_split(
        dataset, [train_size, val_size], generator=torch.Generator().manual_seed(args.seed)
    )
    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=args.batch_size) if val_size > 0 else None

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Dung thiet bi: {device}")

    model = EvalNet().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_val = float("inf")
    epochs_without_improve = 0
    for epoch in range(1, args.epochs + 1):
        train_loss = run_epoch(model, train_loader, device, optimizer)
        val_loss = run_epoch(model, val_loader, device) if val_loader else train_loss
        improved = val_loss < best_val
        if improved:
            best_val = val_loss
            epochs_without_improve = 0
            torch.save(model.state_dict(), args.checkpoint)
        else:
            epochs_without_improve += 1

        if epoch == 1 or epoch % 10 == 0 or improved:
            marker = " *" if improved else ""
            print(f"Epoch {epoch:3d}: train_loss={train_loss:.5f} val_loss={val_loss:.5f}{marker}")

        if epochs_without_improve >= args.patience:
            print(f"Dung som o epoch {epoch} (val loss khong cai thien sau {args.patience} epoch).")
            break

    print(f"Da luu model tot nhat (val_loss={best_val:.5f}) vao {args.checkpoint}")


if __name__ == "__main__":
    main()
