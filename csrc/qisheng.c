/*
 * QiSheng - phan loi viet bang C: sinh nuoc di, phat hien chieu, perft.
 *
 * Vi sao can: ho so chay cho thay sinh nuoc di + phat hien chieu chiem 55%
 * thoi gian tim kiem, va do la cac vong lap Python quet tung o. Bitboard trong
 * Python chi giup 1,6x vi van phai tach tung bit bang vong lap Python.
 *
 * Thiet ke quan trong nhat: qs_gen_legal() tra ve TOAN BO nuoc di hop le trong
 * MOT lan goi. Moi lan goi qua ctypes ton ~1-2 us, neu goi tung quan mot thi
 * chi phi goi se nuot het phan loi. Goi mot lan cho ca nut, ben trong C lam
 * het ~30 lan thu nuoc va kiem tra chieu, thi chi phi do duoc chia deu.
 *
 * Ban co: char[90], chi so = hang*9 + cot. Hang 0 la phia Den, hang 9 phia Trang.
 * Quan Trang viet HOA, quan Den viet thuong, o trong la '.'.
 * Nuoc di ma hoa thanh int: (o_di << 8) | o_den.
 *
 * Luat phai khop TUNG CHI TIET voi engine/board.py - kiem chung bang perft.
 */

#include <string.h>

#define O(r, c) ((r) * 9 + (c))

static inline int la_trang(char p) { return p >= 'A' && p <= 'Z'; }
static inline int co_quan(char p) { return p != '.'; }

static inline int trong_cung(int r, int c, int trang) {
    if (c < 3 || c > 5) return 0;
    return trang ? (r >= 7 && r <= 9) : (r >= 0 && r <= 2);
}

static inline int ben_minh(int r, int trang) {
    return trang ? (r >= 5) : (r <= 4);
}

/* Tim Tuong soai: chi quet 9 o cua cung, khong quet ca ban co */
static int tim_tuong(const char *b, int trang) {
    char k = trang ? 'K' : 'k';
    int r0 = trang ? 7 : 0;
    for (int r = r0; r < r0 + 3; r++)
        for (int c = 3; c <= 5; c++)
            if (b[O(r, c)] == k) return O(r, c);
    return -1;
}

/* Hai Tuong soai nhin thang nhau qua cot trong -> the co khong hop le */
static int tuong_doi_mat(const char *b) {
    int wk = tim_tuong(b, 1), bk = tim_tuong(b, 0);
    if (wk < 0 || bk < 0) return 0;
    int wr = wk / 9, wc = wk % 9, br = bk / 9, bc = bk % 9;
    if (wc != bc) return 0;
    for (int r = br + 1; r < wr; r++)
        if (co_quan(b[O(r, wc)])) return 0;
    return 1;
}

/* O (r,c) co bi ben `tan_cong_trang` tan cong khong.
   Do tia NGUOC tu chinh o do - giong het engine/board.py */
int qs_bi_tan_cong(const char *b, int r, int c, int tan_cong_trang) {
    char here = b[O(r, c)];
    if (co_quan(here) && la_trang(here) == tan_cong_trang) return 0;

    const char *m = tan_cong_trang ? "RHEAKCP" : "rheakcp";
    char R = m[0], H = m[1], E = m[2], A = m[3], K = m[4], C = m[5], P = m[6];

    static const int dr4[4] = {1, -1, 0, 0};
    static const int dc4[4] = {0, 0, 1, -1};

    /* --- Xe, Phao, Tuong soai: 4 tia thang --- */
    for (int i = 0; i < 4; i++) {
        int dr = dr4[i], dc = dc4[i];
        int tr = r + dr, tc = c + dc;
        while (tr >= 0 && tr < 10 && tc >= 0 && tc < 9 && !co_quan(b[O(tr, tc)])) {
            tr += dr; tc += dc;
        }
        if (tr < 0 || tr >= 10 || tc < 0 || tc >= 9) continue;
        char first = b[O(tr, tc)];
        if (first == R) return 1;
        int d = (tr > r ? tr - r : r - tr) + (tc > c ? tc - c : c - tc);
        if (first == K && d == 1 && trong_cung(r, c, tan_cong_trang)) return 1;
        if (first == C && !co_quan(here)) return 1;   /* Phao khong ngoi: chi vao o trong */
        if (co_quan(here)) {                          /* Phao co ngoi: chi AN duoc */
            tr += dr; tc += dc;
            while (tr >= 0 && tr < 10 && tc >= 0 && tc < 9 && !co_quan(b[O(tr, tc)])) {
                tr += dr; tc += dc;
            }
            if (tr >= 0 && tr < 10 && tc >= 0 && tc < 9 && b[O(tr, tc)] == C) return 1;
        }
    }

    /* --- Ma: 8 o, kem kiem tra chan chan --- */
    static const int mdr[8] = {2, 2, -2, -2, 1, 1, -1, -1};
    static const int mdc[8] = {1, -1, 1, -1, 2, -2, 2, -2};
    for (int i = 0; i < 8; i++) {
        int hr = r + mdr[i], hc = c + mdc[i];
        if (hr < 0 || hr >= 10 || hc < 0 || hc >= 9) continue;
        if (b[O(hr, hc)] != H) continue;
        int lr, lc;
        if (mdr[i] == 2 || mdr[i] == -2) { lr = hr - (mdr[i] > 0 ? 1 : -1); lc = hc; }
        else { lr = hr; lc = hc - (mdc[i] > 0 ? 1 : -1); }
        if (!co_quan(b[O(lr, lc)])) return 1;
    }

    /* --- Tot: phia truoc, va hai ben neu da qua song --- */
    int lui = tan_cong_trang ? 1 : -1;
    int pr = r + lui;
    if (pr >= 0 && pr < 10 && b[O(pr, c)] == P) return 1;
    for (int k = 0; k < 2; k++) {
        int pc = c + (k ? -1 : 1);
        if (pc < 0 || pc >= 9) continue;
        if (b[O(r, pc)] != P) continue;
        int qua_song = tan_cong_trang ? (r <= 4) : (r >= 5);
        if (qua_song) return 1;
    }

    /* --- Si: cheo mot buoc, ca hai o deu trong cung --- */
    static const int ddr[4] = {1, 1, -1, -1};
    static const int ddc[4] = {1, -1, 1, -1};
    if (trong_cung(r, c, tan_cong_trang)) {
        for (int i = 0; i < 4; i++) {
            int ar = r + ddr[i], ac = c + ddc[i];
            if (ar < 0 || ar >= 10 || ac < 0 || ac >= 9) continue;
            if (b[O(ar, ac)] == A && trong_cung(ar, ac, tan_cong_trang)) return 1;
        }
    }

    /* --- Tuong (voi): cheo hai buoc, khong bi can mat, khong qua song --- */
    if (ben_minh(r, tan_cong_trang)) {
        for (int i = 0; i < 4; i++) {
            int er = r + ddr[i] * 2, ec = c + ddc[i] * 2;
            if (er < 0 || er >= 10 || ec < 0 || ec >= 9) continue;
            if (b[O(er, ec)] != E) continue;
            if (!co_quan(b[O(r + ddr[i], c + ddc[i])])) return 1;
        }
    }
    return 0;
}

int qs_bi_chieu(const char *b, int trang) {
    int k = tim_tuong(b, trang);
    if (k < 0) return 1;
    return qs_bi_tan_cong(b, k / 9, k % 9, !trang) || tuong_doi_mat(b);
}

/* Sinh nuoc di theo luat, CHUA loc nuoc lam lo Tuong */
int qs_gen_pseudo(const char *b, int trang, int *out) {
    int n = 0;
    static const int dr4[4] = {1, -1, 0, 0};
    static const int dc4[4] = {0, 0, 1, -1};
    static const int ddr[4] = {1, 1, -1, -1};
    static const int ddc[4] = {1, -1, 1, -1};
    static const int hleg_r[8] = {1, 1, -1, -1, 0, 0, 0, 0};
    static const int hleg_c[8] = {0, 0, 0, 0, 1, 1, -1, -1};
    static const int hdr[8] = {2, 2, -2, -2, 1, -1, 1, -1};
    static const int hdc[8] = {1, -1, 1, -1, 2, 2, -2, -2};

    for (int r = 0; r < 10; r++) for (int c = 0; c < 9; c++) {
        char p = b[O(r, c)];
        if (!co_quan(p) || la_trang(p) != trang) continue;
        char k = (p >= 'a') ? (char)(p - 32) : p;
        int from = O(r, c);

        #define THEM(tr, tc) do { \
            if ((tr) >= 0 && (tr) < 10 && (tc) >= 0 && (tc) < 9) { \
                char t = b[O(tr, tc)]; \
                if (!co_quan(t) || la_trang(t) != trang) \
                    out[n++] = (from << 8) | O(tr, tc); \
            } } while (0)

        if (k == 'K') {
            for (int i = 0; i < 4; i++) {
                int tr = r + dr4[i], tc = c + dc4[i];
                if (trong_cung(tr, tc, trang)) THEM(tr, tc);
            }
        } else if (k == 'A') {
            for (int i = 0; i < 4; i++) {
                int tr = r + ddr[i], tc = c + ddc[i];
                if (trong_cung(tr, tc, trang)) THEM(tr, tc);
            }
        } else if (k == 'E') {
            for (int i = 0; i < 4; i++) {
                int tr = r + ddr[i] * 2, tc = c + ddc[i] * 2;
                if (tr < 0 || tr >= 10 || tc < 0 || tc >= 9) continue;
                if (!ben_minh(tr, trang)) continue;
                if (co_quan(b[O(r + ddr[i], c + ddc[i])])) continue;
                THEM(tr, tc);
            }
        } else if (k == 'H') {
            for (int i = 0; i < 8; i++) {
                int lr = r + hleg_r[i], lc = c + hleg_c[i];
                if (lr < 0 || lr >= 10 || lc < 0 || lc >= 9) continue;
                if (co_quan(b[O(lr, lc)])) continue;
                THEM(r + hdr[i], c + hdc[i]);
            }
        } else if (k == 'R') {
            for (int i = 0; i < 4; i++) {
                int tr = r + dr4[i], tc = c + dc4[i];
                while (tr >= 0 && tr < 10 && tc >= 0 && tc < 9) {
                    char t = b[O(tr, tc)];
                    if (!co_quan(t)) out[n++] = (from << 8) | O(tr, tc);
                    else {
                        if (la_trang(t) != trang) out[n++] = (from << 8) | O(tr, tc);
                        break;
                    }
                    tr += dr4[i]; tc += dc4[i];
                }
            }
        } else if (k == 'C') {
            for (int i = 0; i < 4; i++) {
                int tr = r + dr4[i], tc = c + dc4[i], ngoi = 0;
                while (tr >= 0 && tr < 10 && tc >= 0 && tc < 9) {
                    char t = b[O(tr, tc)];
                    if (!ngoi) {
                        if (!co_quan(t)) out[n++] = (from << 8) | O(tr, tc);
                        else ngoi = 1;
                    } else if (co_quan(t)) {
                        if (la_trang(t) != trang) out[n++] = (from << 8) | O(tr, tc);
                        break;
                    }
                    tr += dr4[i]; tc += dc4[i];
                }
            }
        } else if (k == 'P') {
            int tien = trang ? -1 : 1;
            THEM(r + tien, c);
            int qua_song = trang ? (r <= 4) : (r >= 5);
            if (qua_song) { THEM(r, c + 1); THEM(r, c - 1); }
        }
        #undef THEM
    }
    return n;
}

/* Sinh nuoc di HOP LE: sinh pseudo roi thu tung nuoc, loai nuoc lam lo Tuong.
   Toan bo lam trong C, chi mot lan goi tu Python cho ca nut. */
int qs_gen_legal(const char *b, int trang, int *out) {
    int tmp[256];
    int n = qs_gen_pseudo(b, trang, tmp);
    char sao[90];
    int m = 0;
    for (int i = 0; i < n; i++) {
        memcpy(sao, b, 90);
        int from = (tmp[i] >> 8) & 127, to = tmp[i] & 127;
        sao[to] = sao[from];
        sao[from] = '.';
        if (!qs_bi_chieu(sao, trang)) out[m++] = tmp[i];
    }
    return m;
}

/* Perft - dem so la o do sau N. Dung de kiem chung luat khop voi ban Python. */
long long qs_perft(const char *b, int trang, int depth) {
    if (depth == 0) return 1;
    int mv[256];
    int n = qs_gen_legal(b, trang, mv);
    if (depth == 1) return n;
    long long tong = 0;
    char sao[90];
    for (int i = 0; i < n; i++) {
        memcpy(sao, b, 90);
        int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
        sao[to] = sao[from];
        sao[from] = '.';
        tong += qs_perft(sao, !trang, depth - 1);
    }
    return tong;
}

/* --- Danh gia thu cong: vat chat + vi tri, tinh trong C ---
   Bang vi tri sinh tu engine/pst.py de khong lech giua hai ban.
   Tra ve diem THO (duong = loi cho Trang); Python quy doi sang thang 0..1000. */
static const short PST[7][90] = {
    {6,10,12,14,14,14,12,10,6,8,12,14,16,16,16,14,12,8,6,10,12,14,14,14,12,10,6,6,10,12,14,14,14,12,10,6,6,8,10,12,12,12,10,8,6,4,8,10,12,12,12,10,8,4,4,6,8,10,10,10,8,6,4,2,6,8,10,10,10,8,6,2,2,4,6,8,8,8,6,4,2,0,4,6,8,8,8,6,4,0},
    {0,-4,0,0,0,0,0,-4,0,4,2,8,8,10,8,8,2,4,4,10,14,16,16,16,14,10,4,6,12,18,22,22,22,18,12,6,6,14,20,24,26,24,20,14,6,4,12,18,22,24,22,18,12,4,2,8,14,16,18,16,14,8,2,0,6,10,12,12,12,10,6,0,0,2,6,8,8,8,6,2,0,0,-4,4,0,0,0,4,-4,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0,0,0,6,0,0,0,6,0,0,0,0,0,0,0,0,0,0,0,6,0,0,0,6,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,0,0,0,0,0,0,0,6,0,6,0,0,0},
    {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-12,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0,0,0,0},
    {0,0,2,6,6,6,2,0,0,0,2,4,6,8,6,4,2,0,2,4,6,8,10,8,6,4,2,0,2,4,6,8,6,4,2,0,0,0,2,4,6,4,2,0,0,0,0,2,4,6,4,2,0,0,0,2,4,6,8,6,4,2,0,0,2,4,6,8,6,4,2,0,0,0,2,4,4,4,2,0,0,0,0,0,2,2,2,0,0,0},
    {0,3,6,9,12,9,6,3,0,18,36,56,80,120,80,56,36,18,14,26,42,60,80,60,42,26,14,10,20,30,34,40,34,30,20,10,6,12,18,18,20,18,18,12,6,2,0,8,0,8,0,8,0,2,0,0,-2,0,4,0,-2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
};
static const short GIA_TRI[7] = {900,400,200,200,0,450,100};
#define TOT_QUA_SONG 100

static inline int chi_so_quan(char k) {
    switch (k) {
        case 'R': return 0; case 'H': return 1; case 'E': return 2;
        case 'A': return 3; case 'K': return 4; case 'C': return 5;
        case 'P': return 6;
    }
    return -1;
}

int qs_danh_gia_tho(const char *b) {
    int diem = 0;
    for (int r = 0; r < 10; r++) for (int c = 0; c < 9; c++) {
        char p = b[O(r, c)];
        if (!co_quan(p)) continue;
        int trang = la_trang(p);
        char k = trang ? p : (char)(p - 32);
        int i = chi_so_quan(k);
        if (i < 0) continue;
        int v = GIA_TRI[i];
        if (k == 'P') {
            int qua = trang ? (r <= 4) : (r >= 5);
            if (qua) v += TOT_QUA_SONG;
        }
        /* Bang viet theo goc nhin Trang; quan Den lat nguoc theo chieu doc */
        v += PST[i][trang ? O(r, c) : O(9 - r, c)];
        diem += trang ? v : -v;
    }
    return diem;
}

/* --- Trich dac trung cho mang NNUE ---
   Thu tu quan "RHEAKCPrheakcp" phai khop voi luc huan luyen:
   chi so dac trung = so_thu_tu_quan * 90 + hang * 9 + cot. */
static inline int chi_so_nnue(char p) {
    switch (p) {
        case 'R': return 0;  case 'H': return 1;  case 'E': return 2;
        case 'A': return 3;  case 'K': return 4;  case 'C': return 5;
        case 'P': return 6;
        case 'r': return 7;  case 'h': return 8;  case 'e': return 9;
        case 'a': return 10; case 'k': return 11; case 'c': return 12;
        case 'p': return 13;
    }
    return -1;
}

int qs_dac_trung(const char *b, int *out) {
    int n = 0;
    for (int sq = 0; sq < 90; sq++) {
        char p = b[sq];
        if (p == '.') continue;
        int i = chi_so_nnue(p);
        if (i >= 0) out[n++] = i * 90 + sq;
    }
    return n;
}

/* --- Bam Zobrist ---
   Bang do Python nap vao mot lan (14 loai quan x 90 o + 1 cho luot di), de hai
   ben dung dung mot bang va ma bam khop nhau. */
static unsigned long long ZOB[14 * 90];
static unsigned long long ZOB_DEN;

void qs_dat_zobrist(const unsigned long long *bang, unsigned long long den) {
    for (int i = 0; i < 14 * 90; i++) ZOB[i] = bang[i];
    ZOB_DEN = den;
}

unsigned long long qs_bam(const char *b, int trang) {
    unsigned long long h = 0;
    for (int sq = 0; sq < 90; sq++) {
        char p = b[sq];
        if (p == '.') continue;
        int i = chi_so_nnue(p);
        if (i >= 0) h ^= ZOB[i * 90 + sq];
    }
    if (!trang) h ^= ZOB_DEN;
    return h;
}
