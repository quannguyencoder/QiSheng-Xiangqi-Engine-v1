"""
XuanWu - may chu web cuc bo de choi voi engine.

Chay:  python3 web/chay.py
Tat:   Ctrl+C

Dung http.server co san trong Python, khong cai them thu vien nao. Web nay chi
phuc vu MOT nguoi choi tren may cua chinh minh nen khong can may chu chiu tai;
bot mot thu vien la bot mot thu co the hong khi mo lai sau vai tuan.

API duoc thiet ke de mo rong sau nay ma khong phai sua kien truc:
  POST /api/van-moi    tao van moi
  POST /api/di         nguoi di mot nuoc, may tra loi
  POST /api/danh-gia   cham diem the co hien tai (cho thanh danh gia)
  POST /api/goi-y      goi y nuoc di tot nhat (khong di)
  POST /api/phan-tich  (chua lam) phan tich ca van
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import time
import webbrowser

THU_MUC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(THU_MUC))

from engine.board import WHITE, BLACK, start_board
from engine.luat_van import VanCo, DANG_CHOI
from engine import manh_nhat
from tools.collect_openings import board_to_fen

CONG = 8000
MUC_DO = {"de": 0.5, "vua": 3.0, "kho": 10.0}

# Cac van dang choi, theo ma van. Giu trong bo nho vi web chi chay khi can.
_van = {}
_khoa = threading.Lock()


def _ban_co_json(v: VanCo):
    """Ban co dang mang 10x9 ky tu, kem trang thai van."""
    tt, ly_do = v.trang_thai()
    return {
        "ban_co": ["".join(h) for h in v.board],
        "ben_di": "trang" if v.side == WHITE else "den",
        "bi_chieu": v.dang_bi_chieu(),
        "trang_thai": tt,
        "ly_do": ly_do,
        "nuoc_hop_le": [list(m) for m in v.nuoc_hop_le()] if tt == DANG_CHOI else [],
        "so_nuoc": len(v.lich_su) - 1,
    }


def _cham_diem(v: VanCo, giay: float = 0.3):
    """Diem 0..1000 goc nhin Trang, dung cho thanh danh gia."""
    tt, _ = v.trang_thai()
    if tt == "trang_thang":
        return 1000
    if tt == "den_thang":
        return 0
    if tt == "hoa":
        return 500
    diem, _, _, _ = manh_nhat.tim_nuoc_di_theo_gio(v.board, v.side, giay,
                                                   dung_sach=False)
    return diem


class May(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=THU_MUC, **kw)

    def log_message(self, *a):
        pass                                  # khong in log moi yeu cau

    def _tra(self, data, ma=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._tra({"loi": "JSON khong hop le"}, 400)
        duong = self.path.split("?")[0]
        try:
            if duong == "/api/van-moi":
                return self._van_moi(req)
            if duong == "/api/di":
                return self._di(req)
            if duong == "/api/danh-gia":
                return self._danh_gia(req)
            if duong == "/api/goi-y":
                return self._goi_y(req)
            return self._tra({"loi": "khong co duong dan nay"}, 404)
        except Exception as e:                # tra loi ro thay vi treo trang
            return self._tra({"loi": f"{type(e).__name__}: {e}"}, 500)

    # -- cac diem cuoi -----------------------------------------------------

    def _van_moi(self, req):
        ma = str(int(time.time() * 1000))
        with _khoa:
            _van[ma] = VanCo()
        v = _van[ma]
        return self._tra({"ma_van": ma, **_ban_co_json(v), "diem": 505})

    def _di(self, req):
        ma = req.get("ma_van")
        with _khoa:
            v = _van.get(ma)
        if v is None:
            return self._tra({"loi": "khong tim thay van"}, 404)

        # 1. Nguoi di
        mv = tuple(req["nuoc"])
        try:
            v.di(mv)
        except ValueError as e:
            return self._tra({"loi": str(e)}, 400)

        tt, _ = v.trang_thai()
        if tt != DANG_CHOI:
            return self._tra({**_ban_co_json(v), "diem": _cham_diem(v),
                              "nuoc_may": None})

        # Che do tu choi hai ben: nguoi di het, may khong tra loi
        if req.get("tu_choi"):
            return self._tra({**_ban_co_json(v), "diem": _cham_diem(v),
                              "nuoc_may": None})

        # 2. May tra loi
        giay = MUC_DO.get(req.get("muc_do", "vua"), 3.0)
        t0 = time.time()
        diem, nuoc_may, nut, do_sau = manh_nhat.tim_nuoc_di_theo_gio(
            v.board, v.side, giay)
        if nuoc_may is None:
            return self._tra({**_ban_co_json(v), "diem": _cham_diem(v),
                              "nuoc_may": None})
        v.di(nuoc_may)
        return self._tra({
            **_ban_co_json(v),
            "diem": diem,
            "nuoc_may": list(nuoc_may),
            "do_sau": do_sau,
            "so_nut": nut,
            "giay": round(time.time() - t0, 2),
        })

    def _goi_y(self, req):
        """Nuoc di tot nhat cho ben dang di, KHONG thuc hien. Dung ve mui ten."""
        with _khoa:
            v = _van.get(req.get("ma_van"))
        if v is None:
            return self._tra({"loi": "khong tim thay van"}, 404)
        tt, _ = v.trang_thai()
        if tt != DANG_CHOI:
            return self._tra({"nuoc": None, "diem": _cham_diem(v)})
        giay = MUC_DO.get(req.get("muc_do", "vua"), 3.0)
        diem, nuoc, nut, do_sau = manh_nhat.tim_nuoc_di_theo_gio(
            v.board, v.side, giay)
        return self._tra({
            "nuoc": list(nuoc) if nuoc else None,
            "diem": diem, "do_sau": do_sau, "so_nut": nut,
            "ben": "trang" if v.side == WHITE else "den",
        })

    def _danh_gia(self, req):
        with _khoa:
            v = _van.get(req.get("ma_van"))
        if v is None:
            return self._tra({"loi": "khong tim thay van"}, 404)
        return self._tra({"diem": _cham_diem(v, req.get("giay", 0.3))})


def main():
    print("XuanWu - dang khoi dong...")
    ok = manh_nhat.chuan_bi()
    print(f"  engine: {'loi C' if ok else 'Python thuan (cham hon)'}")
    from engine import sach
    print(f"  sach khai cuoc: {sach.so_muc():,} the co" if sach.nap()
          else "  sach khai cuoc: khong co")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", CONG), May) as may:
        dia_chi = f"http://127.0.0.1:{CONG}/"
        print(f"\n  Mo trinh duyet: {dia_chi}")
        print("  Nhan Ctrl+C de tat\n")
        threading.Timer(0.8, lambda: webbrowser.open(dia_chi)).start()
        try:
            may.serve_forever()
        except KeyboardInterrupt:
            print("\nDa tat.")


if __name__ == "__main__":
    main()
