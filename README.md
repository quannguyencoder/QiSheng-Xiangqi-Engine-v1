# QiSheng (棋聖) — Xiangqi Engine v1

Engine cờ tướng (Chinese chess) viết hoàn toàn từ đầu bằng Python — tự sinh nước đi,
tự tìm kiếm, tự đánh giá thế cờ, **không dùng bất kỳ thư viện cờ nào**.

Mọi thế cờ được chấm trên **thang 0–1000** theo góc nhìn Trắng:

| Điểm | Ý nghĩa |
|---|---|
| 500 | cân bằng |
| **505** | thế cờ khởi đầu (Trắng đi trước, +5 điểm tempo) |
| 1000 | Trắng chiếu hết được ngay trong lượt này |
| 0 | ngược lại cho Đen |

## Cấu trúc

```
engine/       lõi engine, chạy bằng Python thuần (không cần thư viện ngoài)
  board.py      bàn cờ 10x9, sinh nước đi 7 loại quân, luật kỵ mặt tướng
  evaluate.py   đánh giá tĩnh: vật chất + cơ động + piece-square table
  pst.py        bảng điểm vị trí cho 7 loại quân
  search.py     alpha-beta + quiescence + transposition table + move ordering
  scoring.py    quy đổi sang thang 0–1000
tools/        script ngoài luồng chạy (chỉ dùng khi thu thập dữ liệu / huấn luyện)
  crawl_chessdb.py    cào thế cờ có nhãn từ chessdb.cn theo BFS
  collect_openings.py thu thập khai cuộc bằng self-play walk
  train.py            huấn luyện mạng đánh giá (PyTorch)
data/         dữ liệu huấn luyện (JSONL) + hàng đợi BFS
weights/      trọng số mạng đã huấn luyện
tests/        kiểm thử: perft (44 / 1.920 / 79.666), luật đi quân, thang điểm
web/          giao diện bàn cờ (giai đoạn sau)
```

## Dùng thử

```bash
python3 main.py                                   # phân tích thế cờ khởi đầu
python3 main.py "<FEN>" --depth 2                 # phân tích một thế cờ bất kỳ
python3 tests/test_engine.py                      # chạy toàn bộ kiểm thử
python3 tools/train.py --epochs 60                # huấn luyện lại mạng đánh giá
python3 tools/crawl_chessdb.py --output data/x.jsonl --shard 0 --num-shards 6
```

Engine chỉ cần Python thuần. `requirements.txt` (PyTorch, NumPy) chỉ cần cho việc huấn luyện.

## Dữ liệu

Nhãn được lấy từ **nguồn ngoài**, không tự chấm:

| Nguồn | Số mẫu |
|---|---|
| chessdb.cn — khai cuộc (winrate từ ván người thật) | 5297 |
| chessdb.cn — cào BFS | 7360 |
| Bộ huấn luyện gộp (lịch sử) | 37419 |

## Kỹ thuật trong search

| Kỹ thuật | Tác dụng |
|---|---|
| Alpha-beta | cắt nhánh không cần xét |
| Move ordering MVV-LVA | thử nước ăn quân giá trị cao bằng quân rẻ trước → cắt sâu hơn nhiều |
| Transposition table (Zobrist) | cùng thế cờ đến từ nhiều thứ tự nước đi chỉ tính một lần |
| Quiescence search | không dừng giữa pha đổi quân (chống hiệu ứng chân trời) |
| Điểm chiếu hết giảm dần theo độ sâu | ưu tiên đường chiếu hết ngắn nhất |

## Tình trạng

Đang phát triển. Chưa có số đo Elo — cần dựng bộ đối kháng với Pikafish trước khi
công bố bất kỳ con số sức cờ nào.
