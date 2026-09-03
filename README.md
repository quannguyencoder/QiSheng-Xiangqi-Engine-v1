# QiSheng (棋聖) — Xiangqi Engine v1

> A Xiangqi (Chinese chess) engine written entirely from scratch in Python — own move
> generation, own search, own evaluation, **no chess libraries of any kind**. Every position
> is scored on a **0–1000 scale** from Red/White's perspective.

Engine cờ tướng viết hoàn toàn từ đầu bằng Python. Tự sinh nước đi, tự tìm kiếm, tự đánh giá
thế cờ — **không dùng bất kỳ thư viện cờ nào**. Mạng nơ-ron học từ dữ liệu gán nhãn bởi
nguồn ngoài, không tự chấm điểm cho chính mình.

## Thang điểm

Mọi thế cờ được chấm trên thang **0–1000** theo góc nhìn Trắng:

| Điểm | Ý nghĩa |
|---:|---|
| 1000 | Trắng chiếu hết được **ngay trong nước đi này** |
| 505 | thế cờ khởi đầu (Trắng đi trước, +5 điểm tempo) |
| 500 | cân bằng |
| 0 | ngược lại cho Đen |

Điểm chiếu hết giảm dần theo độ sâu (1000 → 999 → 998…) nên engine luôn ưu tiên đường
chiếu hết **ngắn nhất**.

## Tình trạng hiện tại

Dự án đang phát triển. Nói thẳng những gì đã và **chưa** có:

| Hạng mục | Trạng thái |
|---|---|
| Luật đi quân + sinh nước đi | ✅ Đã kiểm chứng bằng perft, khớp giá trị chuẩn |
| Search (alpha-beta, quiescence, TT, move ordering) | ✅ Hoạt động |
| Đánh giá thủ công (vật chất + cơ động + PST) | ✅ Hoạt động |
| Thu thập dữ liệu từ nguồn ngoài | 🔄 Đang chạy (47.872 thế cờ) |
| Mạng nơ-ron đánh giá | ⚠️ Đã huấn luyện nhưng **chưa nối vào engine** |
| Đo Elo | ❌ Chưa có — cần dựng đối kháng với Pikafish |
| Giao diện web | ❌ Chưa làm |

**Chưa công bố con số Elo nào** vì chưa có bộ đối kháng để đo. Mọi phát biểu về sức cờ
trước khi có số liệu đối kháng đều là phỏng đoán.

## Cấu trúc

```
engine/            lõi engine — Python thuần, không cần thư viện ngoài
  board.py           bàn cờ 10×9, sinh nước đi 7 loại quân, luật kỵ mặt tướng
  evaluate.py        đánh giá tĩnh: vật chất + cơ động + vị trí
  pst.py             bảng điểm vị trí (piece-square table) cho từng loại quân
  search.py          alpha-beta + quiescence + transposition table + move ordering
  scoring.py         quy đổi sang thang 0–1000 (tách riêng để calibrate độc lập)
tools/             script ngoài luồng chạy — chỉ dùng khi thu thập dữ liệu / huấn luyện
  crawl_chessdb.py   cào thế cờ có nhãn từ chessdb.cn theo BFS
  collect_openings.py thu thập khai cuộc bằng self-play walk
  train.py           huấn luyện mạng đánh giá (PyTorch)
tests/             kiểm thử: perft, luật đi quân, thang điểm
data/              dữ liệu huấn luyện (JSONL) + hàng đợi BFS
weights/           trọng số mạng đã huấn luyện
web/               giao diện bàn cờ (chưa làm)
main.py            CLI phân tích thế cờ
```

Engine (`engine/`) chạy bằng Python thuần. `requirements.txt` (PyTorch, NumPy) **chỉ cần
cho việc huấn luyện**, không cần khi chạy engine.

## Dùng thử

```bash
python3 main.py                              # phân tích thế cờ khởi đầu
python3 main.py "<FEN>" --depth 2            # phân tích một thế cờ bất kỳ
python3 tests/test_engine.py                 # chạy toàn bộ kiểm thử
python3 tools/train.py --epochs 60           # huấn luyện lại mạng đánh giá
python3 tools/crawl_chessdb.py --output data/x.jsonl --shard 0 --num-shards 6
```

## Kỹ thuật trong search

| Kỹ thuật | Tác dụng |
|---|---|
| Alpha-beta | cắt nhánh không cần xét |
| Move ordering MVV-LVA | thử nước ăn quân giá trị cao bằng quân rẻ trước → cắt sâu hơn nhiều |
| Transposition table (băm Zobrist) | cùng thế cờ đến từ nhiều thứ tự nước đi chỉ tính một lần |
| Quiescence search | không dừng giữa pha đổi quân (chống hiệu ứng chân trời) |

**Quiescence giải quyết được lỗi gì:** ở thế cờ khởi đầu, Pháo Trắng có thể nhảy qua Pháo Đen
ăn Mã. Engine không có quiescence chấm nước này **610 điểm** (tưởng thắng lớn) vì không nhìn
thấy Đen ăn lại ngay. Có quiescence, nước đó chấm **481 điểm** — đúng bản chất.

## Dữ liệu

Nhãn lấy từ **nguồn ngoài**, engine không tự chấm điểm cho dữ liệu huấn luyện của chính nó:

| Nguồn | Số thế cờ | Ghi chú |
|---|---:|---|
| chessdb.cn | 10.481 | winrate từ ván người thật + engine mạnh, đang tăng |
| engine nội bộ (đã đóng băng) | 37.391 | dữ liệu cũ, giữ lại vì dạy đúng về vật chất |
| **Tổng** | **47.872** | |

`crawl_chessdb.py` duyệt **BFS trên chính cây thế cờ chessdb đã phân tích**: mỗi lần hỏi một
thế cờ, chessdb trả về mọi nước đi nó biết → mỗi nước sinh một thế cờ con chắc chắn vẫn nằm
trong vùng đã phân tích. Nhờ vậy gần như mọi request đều thu được một mẫu có nhãn, thay vì đi
ngẫu nhiên rồi trượt ra ngoài vùng dữ liệu.

**Vì sao vẫn giữ 37.391 mẫu nhãn engine:** đã đo bằng thực nghiệm. Mạng chỉ học dữ liệu
chessdb đạt MAE tốt hơn trên khai cuộc (36,1 vs 53,1) nhưng **hiểu ngược hoàn toàn về vật
chất** — xoá một quân Xe của Đen mà nó tưởng Đen *lợi* hơn, sai 81% số lần. Dữ liệu chessdb
hiện có toàn thế cờ cân bằng nên mạng không bao giờ thấy thế lệch quân.

## Kiểm thử

```
perft(1) =     44   ✓
perft(2) =  1.920   ✓
perft(3) = 79.666   ✓
```

Perft (đếm số thế cờ lá ở độ sâu N) khớp tuyệt đối giá trị chuẩn của cờ tướng — chỉ cần một
lỗi nhỏ trong luật đi quân là con số lệch ngay. Ngoài ra có kiểm thử cho luật ngòi Pháo, cản
chân Mã, Tượng không qua sông, Tốt đi ngang sau khi qua sông, và luật kỵ mặt tướng.

## Hiệu năng

| Độ sâu | Thời gian |
|---:|---|
| 1 | 0,2 s |
| 2 | 2,1 s |
| 3 | 13,6 s |

Nút thắt hiện nằm ở `is_square_attacked()`: mỗi lần kiểm tra chiếu tướng phải quét cả 90 ô
rồi sinh toàn bộ nước đi của quân địch. Thay bằng dò tia từ ô Tướng sẽ nhanh hơn nhiều lần
mà không đổi kết quả — đây là việc tối ưu đáng làm nhất tiếp theo.

## Hướng đi tiếp

- [ ] Tối ưu `is_square_attacked()` — tăng độ sâu tìm kiếm
- [ ] Nối mạng nơ-ron vào hàm đánh giá của engine (hiện đã huấn luyện nhưng chưa dùng)
- [ ] Thêm Pikafish làm nguồn nhãn thứ hai (chấm được cả thế lệch quân, không như chessdb)
- [ ] Dựng bộ đối kháng để **đo Elo thật**
- [ ] Giao diện web: bàn cờ tương tác, thanh đánh giá, mũi tên nước đi tốt nhất

## Giấy phép

Chưa chọn. Dữ liệu trong `data/` lấy từ chessdb.cn — xem điều khoản của họ trước khi
dùng lại vào mục đích khác.
