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
/* Ban trong: sua truc tiep tren ban co roi LUI lai, thay vi sao chep 90 byte
   cho tung nuoc. Moi nut co ~40 nuoc, o 7 trieu nut la ~25 GB sao chep tiet
   kiem duoc. Ban co duoc tra ve nguyen trang truoc khi ham ket thuc. */
static int gen_legal_tai_cho(char *b, int trang, int *out) {
    int tmp[256];
    int n = qs_gen_pseudo(b, trang, tmp);
    int m = 0;

    /* Chi kiem tra nhung nuoc CO THE lam lo Tuong.
     *
     * Truoc day moi nut goi qs_bi_chieu ~40 lan (moi nuoc mot lan) - do la ~75%
     * chi phi mot nut. Nhung phan lon nuoc di khong the nao lam lo Tuong.
     *
     * Trong co tuong, Tuong chi bi lo qua HANG hoac COT (Xe, Phao, va luat
     * Tuong doi mat). Ma va Tuong (voi) khong the ghim quan.
     *   - Roi mot o tren hang/cot cua Tuong minh -> co the mo duong. Phai kiem.
     *   - Di VAO mot o tren hang/cot cua Tuong minh -> co the thanh ngoi cho
     *     Phao doi phuong, tao ra chieu. Cung phai kiem.
     *   - Nuoc di cua chinh Tuong -> luon phai kiem.
     *   - Dang bi chieu -> phai kiem het.
     *
     * CON MOT TRUONG HOP NUA, va no da lam 18/4.000 the co sai khi thieu:
     * quan dang CAN CHAN MA cua doi phuong. Neu no di khoi, con Ma do chieu
     * duoc Tuong ngay - ma o can chan KHONG nam tren hang hay cot cua Tuong.
     * Tinh ra thi moi o can chan cua Ma nham vao Tuong deu la mot trong 4 o
     * CHEO KE Tuong. Nen phai kiem them cac nuoc roi khoi 4 o do.
     */
    int k = tim_tuong(b, trang);
    int dang_bi_chieu = qs_bi_chieu(b, trang);
    int kr = k / 9, kc = k % 9;

    for (int i = 0; i < n; i++) {
        int from = (tmp[i] >> 8) & 127, to = tmp[i] & 127;
        int fr = from / 9, fc = from % 9;
        int dr = fr - kr, dc = fc - kc;
        if (dr < 0) dr = -dr;
        if (dc < 0) dc = -dc;
        int cheo_ke_tuong = (dr == 1 && dc == 1);      /* o can chan Ma */
        int can_kiem = dang_bi_chieu || k < 0 || from == k
                       || fr == kr || fc == kc || cheo_ke_tuong
                       || (to / 9) == kr || (to % 9) == kc;
        if (!can_kiem) { out[m++] = tmp[i]; continue; }
        char q_di = b[from], q_bi_an = b[to];
        b[to] = q_di;
        b[from] = '.';
        if (!qs_bi_chieu(b, trang)) out[m++] = tmp[i];
        b[from] = q_di;
        b[to] = q_bi_an;
    }
    return m;
}

/* Ban ngoai cho Python: sao mot lan roi goi ban trong. */
int qs_gen_legal(const char *b, int trang, int *out) {
    char sao[90];
    memcpy(sao, b, 90);
    return gen_legal_tai_cho(sao, trang, out);
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
static int ZOB_SAN_SANG = 0;

/* C tu sinh bang bam bang mot bo sinh so co dinh.
   TRUOC DAY bang chi duoc nap tu Python, nen neu quen nap thi qs_bam tra ve 0
   cho MOI the co - moi the co dung chung mot o bang chuyen vi va engine tra ve
   diem rac. Loi do khong lam chuong trinh chet, chi lam ket qua sai am tham.
   Nay C tu lo, Python chi ghi de khi can hai ben cho cung ma bam. */
static void tu_sinh_zobrist(void) {
    unsigned long long x = 0x9E3779B97F4A7C15ULL;
    for (int i = 0; i < 14 * 90; i++) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        ZOB[i] = x;
    }
    x ^= x << 13; x ^= x >> 7; x ^= x << 17;
    ZOB_DEN = x;
    ZOB_SAN_SANG = 1;
}

void qs_dat_zobrist(const unsigned long long *bang, unsigned long long den) {
    for (int i = 0; i < 14 * 90; i++) ZOB[i] = bang[i];
    ZOB_DEN = den;
    ZOB_SAN_SANG = 1;
}

unsigned long long qs_bam(const char *b, int trang) {
    if (!ZOB_SAN_SANG) tu_sinh_zobrist();
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

/* ==========================================================================
 * Mang NNUE va ham danh gia tron, tinh tron ven trong C.
 *
 * Vi sao: mang chi co 1260->256->32->1, khoang 9.000 phep nhan cong, trong C
 * mat ~2-3 us. Nhung NumPy phai goi 6 lenh nho lien tiep, moi lenh ton 1-5 us
 * CHI PHI GOI bat ke phep tinh to hay nho - thanh ra ~30 us cho viec dang le
 * 3 us. Do la cho lang phi lon nhat con lai sau khi da chuyen 4 phan sang C.
 *
 * Gop luon ham tron vao day: mot lan goi tra ve diem cuoi cung, thay vi Python
 * goi ham thu cong roi goi mang roi tron - ba lan qua cau noi.
 * ========================================================================== */

#include <math.h>
#include <stdlib.h>

#define NNUE_DAC_TRUNG 1260

static float *W1 = 0, *B1 = 0, *W2 = 0, *B2 = 0, *W3 = 0;
static float B3 = 0.0f;
static int SO_TICH_LUY = 0, SO_AN = 0;
static float *ACC = 0, *H2 = 0;

/* Nap trong so tu Python. w1 xep theo [dac_trung][no_ron], w2 theo [vao][ra]. */
int qs_nnue_nap(const float *w1, const float *b1,
                const float *w2, const float *b2,
                const float *w3, float b3,
                int so_tich_luy, int so_an) {
    free(W1); free(B1); free(W2); free(B2); free(W3); free(ACC); free(H2);
    SO_TICH_LUY = so_tich_luy; SO_AN = so_an;
    W1 = (float *)malloc(sizeof(float) * NNUE_DAC_TRUNG * so_tich_luy);
    B1 = (float *)malloc(sizeof(float) * so_tich_luy);
    W2 = (float *)malloc(sizeof(float) * (so_tich_luy + 1) * so_an);
    B2 = (float *)malloc(sizeof(float) * so_an);
    W3 = (float *)malloc(sizeof(float) * so_an);
    ACC = (float *)malloc(sizeof(float) * so_tich_luy);
    H2 = (float *)malloc(sizeof(float) * so_an);
    if (!W1 || !B1 || !W2 || !B2 || !W3 || !ACC || !H2) return 0;
    for (int i = 0; i < NNUE_DAC_TRUNG * so_tich_luy; i++) W1[i] = w1[i];
    for (int i = 0; i < so_tich_luy; i++) B1[i] = b1[i];
    for (int i = 0; i < (so_tich_luy + 1) * so_an; i++) W2[i] = w2[i];
    for (int i = 0; i < so_an; i++) B2[i] = b2[i];
    for (int i = 0; i < so_an; i++) W3[i] = w3[i];
    B3 = b3;
    return 1;
}

static float nnue_tho(const char *b, int trang);

static inline float kep01(float x) { return x < 0.0f ? 0.0f : (x > 1.0f ? 1.0f : x); }

/* Tinh tich luy tu dau (quet ca ban co) */
static void acc_tu_dau(const char *b, float *acc) {
    const int n = SO_TICH_LUY;
    for (int i = 0; i < n; i++) acc[i] = B1[i];
    for (int sq = 0; sq < 90; sq++) {
        char p = b[sq];
        if (p == '.') continue;
        int k = chi_so_nnue(p);
        if (k < 0) continue;
        const float *cot = W1 + (size_t)(k * 90 + sq) * n;
        for (int i = 0; i < n; i++) acc[i] += cot[i];
    }
}

/* Cap nhat TANG DAN: quan di tu `from` sang `to`, co the an quan `q_an`.
   Chi tru mot cot va cong mot (hoac hai) cot, thay vi cong lai ca 32 cot.
   Day la diem manh cot loi cua kien truc NNUE. */
static void acc_cap_nhat(const float *cha, float *con, char q_di,
                         int from, int to, char q_an) {
    const int n = SO_TICH_LUY;
    int k = chi_so_nnue(q_di);
    const float *bo = W1 + (size_t)(k * 90 + from) * n;
    const float *them = W1 + (size_t)(k * 90 + to) * n;
    if (q_an != '.') {
        int ka = chi_so_nnue(q_an);
        const float *bo2 = W1 + (size_t)(ka * 90 + to) * n;
        for (int i = 0; i < n; i++) con[i] = cha[i] - bo[i] + them[i] - bo2[i];
    } else {
        for (int i = 0; i < n; i++) con[i] = cha[i] - bo[i] + them[i];
    }
}

/* Tra ve xac suat thang cua Trang (0..1) theo mang, dung tich luy cho san. */
static float nnue_tu_acc(const float *acc, int trang) {
    const int n = SO_TICH_LUY, m = SO_AN;
    for (int j = 0; j < m; j++) H2[j] = B2[j];
    for (int i = 0; i < n; i++) {
        float a = kep01(acc[i]);
        if (a == 0.0f) continue;
        const float *hang = W2 + (size_t)i * m;
        for (int j = 0; j < m; j++) H2[j] += a * hang[j];
    }
    if (trang) {                       /* bit "ben di" la dac trung cuoi cung */
        const float *hang = W2 + (size_t)n * m;
        for (int j = 0; j < m; j++) H2[j] += hang[j];
    }
    float out = B3;
    for (int j = 0; j < m; j++) out += kep01(H2[j]) * W3[j];
    return 1.0f / (1.0f + expf(-out));
}

/* Quy doi diem tho -> thang 0..1000, giong engine/scoring.py */
#define MATERIAL_SCALE 1600.0
#define TEMPO 5.0

static int quy_doi(double tho, int trang) {
    double v = tanh(tho / MATERIAL_SCALE) * (500.0 - TEMPO);
    double d = 500.0 + v + (trang ? TEMPO : -TEMPO);
    long r = lround(d);
    if (r < 1) r = 1;
    if (r > 999) r = 999;
    return (int)r;
}

/* Danh gia TRON: (1-w) * thu cong + w * mang + lech, tat ca trong mot lan goi. */
static double trong_so_theo_pha(const char *b, double mac_dinh);

static int danh_gia_voi_acc(const char *b, int trang, const float *acc,
                            double trong_so_mang, double lech) {
    trong_so_mang = trong_so_theo_pha(b, trong_so_mang);
    int a = quy_doi((double)qs_danh_gia_tho(b), trang);
    double bnn = (double)nnue_tu_acc(acc, trang) * 1000.0;
    if (bnn < 1.0) bnn = 1.0;
    if (bnn > 999.0) bnn = 999.0;
    double d = (1.0 - trong_so_mang) * a + trong_so_mang * bnn + lech;
    long r = lround(d);
    if (r < 1) r = 1;
    if (r > 999) r = 999;
    return (int)r;
}

/* Trong so mang theo GIAI DOAN.
 *
 * Do tren 1.175 the co: ti le chon dung nuoc tot nhat cua Pikafish dat dinh o
 * trong so KHAC NHAU tuy giai doan, va nguoc chieu nhau:
 *     khai cuoc  w=0,8 -> 26,6%   (w=0,4 chi 23,4%)
 *     trung cuoc w=0,8 -> 24,3%   (w=0,4 chi 22,4%)
 *     tan cuoc   w=0,2 -> 29,1%   (w=0,4 chi 27,7%)
 * Tan cuoc it quan, dem vat chat va vi tri la tin hieu ro rang, con mang thay
 * it mau tuong tu hon nen nhieu.
 *
 * NHUNG DAU THAT LAI THUA: 40 van depth 6 cho 33,8%, tuc Elo -117 (khoang tin
 * cay -251…-11, KHONG chua 0). Trong so co dinh 0,4 manh hon han.
 * Day la lan thu ba mot chi so gian tiep danh lua: "ti le chon dung nuoc di"
 * cung khong bao dam luc co, chi co dau doi khang moi noi that.
 * Giu code lai de khong ai thu lai, nhung MAC DINH TAT.
 */
static int KEO_DAI_CHIEU = 1;      /* keo dai mot tang khi nuoc di gay chieu */

void qs_dat_keo_dai(int bat) { KEO_DAI_CHIEU = bat; }

static int DUNG_THEO_PHA = 0;
static double W_KHAI = 0.8, W_TRUNG = 0.8, W_TAN = 0.2;

void qs_dat_theo_pha(int bat, double w_khai, double w_trung, double w_tan) {
    DUNG_THEO_PHA = bat;
    W_KHAI = w_khai; W_TRUNG = w_trung; W_TAN = w_tan;
}

static int dem_quan(const char *b) {
    int n = 0;
    for (int sq = 0; sq < 90; sq++) if (b[sq] != '.') n++;
    return n;
}

static double trong_so_theo_pha(const char *b, double mac_dinh) {
    if (!DUNG_THEO_PHA) return mac_dinh;
    int n = dem_quan(b);
    if (n >= 28) return W_KHAI;
    if (n >= 16) return W_TRUNG;
    return W_TAN;
}

int qs_danh_gia_tron(const char *b, int trang, double trong_so_mang, double lech) {
    trong_so_mang = trong_so_theo_pha(b, trong_so_mang);
    int a = quy_doi((double)qs_danh_gia_tho(b), trang);
    double bnn = (double)nnue_tho(b, trang) * 1000.0;
    if (bnn < 1.0) bnn = 1.0;
    if (bnn > 999.0) bnn = 999.0;
    double d = (1.0 - trong_so_mang) * a + trong_so_mang * bnn + lech;
    long r = lround(d);
    if (r < 1) r = 1;
    if (r > 999) r = 999;
    return (int)r;
}

/* Chi mang, dung de doi chieu voi ban NumPy */
static float nnue_tho(const char *b, int trang) {
    acc_tu_dau(b, ACC);
    return nnue_tu_acc(ACC, trang);
}

int qs_nnue_danh_gia(const char *b, int trang) {
    double v = (double)nnue_tho(b, trang) * 1000.0;
    long r = lround(v);
    if (r < 1) r = 1;
    if (r > 999) r = 999;
    return (int)r;
}

/* ==========================================================================
 * Vong lap tim kiem trong C.
 *
 * Sau khi da chuyen sinh nuoc di, danh gia va bam sang C, thu con lai bang
 * Python la CHINH VONG LAP: moi nut phai sorted() voi ham khoa Python, tra
 * dict bang chuyen vi, cap phat tuple. Nhan voi hang tram nghin nut thi day
 * tro thanh phan ton nhat.
 *
 * Cai lai day du: alpha-beta, quiescence, bang chuyen vi Zobrist, sap xep
 * MVV-LVA, killer moves, history heuristic, null-move pruning, late move
 * reduction, iterative deepening - dung nhu ban Python da kiem chung.
 * ========================================================================== */

#define DIEM_MIN 0
#define DIEM_MAX 1000
#define BIEN_CHIEU_HET 50
#define QUIESCENCE_TOI_DA 4
#define PLY_TOI_DA 64
#define TT_BIT 20
#define TT_SO (1 << TT_BIT)

typedef struct {
    unsigned long long khoa;
    int diem;
    short do_sau;
    unsigned char co;        /* 0 dung, 1 can duoi, 2 can tren */
    int nuoc;
} TTMuc;

#define ACC_PLY_MAX 160
static float *ACC_STACK = 0;      /* [ply][SO_TICH_LUY] */

static TTMuc *TT = 0;
static int KILLER[PLY_TOI_DA][2];
static int *HISTORY = 0;         /* [o_di * 90 + o_den] */
static double TRONG_SO_MANG = 0.4, LECH_HIEU_CHINH = 0.0;
static long long SO_NUT = 0;

static const short GIA_TRI_AN[7] = {900, 400, 200, 200, 0, 450, 100};

void qs_tim_kiem_khoi_tao(double trong_so, double lech) {
    if (!TT) TT = (TTMuc *)calloc(TT_SO, sizeof(TTMuc));
    free(ACC_STACK);
    ACC_STACK = (float *)malloc(sizeof(float) * ACC_PLY_MAX * SO_TICH_LUY);
    if (!HISTORY) HISTORY = (int *)calloc(90 * 90, sizeof(int));
    TRONG_SO_MANG = trong_so;
    LECH_HIEU_CHINH = lech;
}

static void xoa_heuristic(void) {
    for (int i = 0; i < PLY_TOI_DA; i++) KILLER[i][0] = KILLER[i][1] = -1;
    if (HISTORY) for (int i = 0; i < 90 * 90; i++) HISTORY[i] = 0;
}

static inline int diem_cuoi(int trang, int ply) {
    int phat = ply > 1 ? ply - 1 : 0;
    return trang ? (DIEM_MIN + phat) : (DIEM_MAX - phat);
}

static inline void di_chuyen(char *b, int mv) {
    int from = (mv >> 8) & 127, to = mv & 127;
    b[to] = b[from];
    b[from] = '.';
}

/* Diem sap xep: cang NHO cang thu truoc (giong ban Python) */
static int khoa_sap_xep(const char *b, int mv, int mv_tt, int ply) {
    if (mv == mv_tt) return -1000000000;
    int to = mv & 127, from = (mv >> 8) & 127;
    char nan_nhan = b[to];
    if (nan_nhan != '.') {
        char kn = la_trang(nan_nhan) ? nan_nhan : (char)(nan_nhan - 32);
        char kt = la_trang(b[from]) ? b[from] : (char)(b[from] - 32);
        int in = chi_so_quan(kn), it = chi_so_quan(kt);
        return -(GIA_TRI_AN[in] * 10 - GIA_TRI_AN[it]);
    }
    if (ply < PLY_TOI_DA) {
        if (mv == KILLER[ply][0]) return -500;
        if (mv == KILLER[ply][1]) return -499;
    }
    return -HISTORY[from * 90 + to] / 1000;
}

/* Chon nuoc theo NHU CAU thay vi sap xep het.
 *
 * Alpha-beta thuong cat sau 1-3 nuoc dau, nen sap xep ca ~40 nuoc la lam thua
 * phan lon cong viec. Nay chi tinh khoa mot lan, roi moi vong lay ra nuoc tot
 * nhat con lai (doi cho voi vi tri hien tai). Neu cat som thi cac nuoc con lai
 * khong ton mot phep so sanh nao.
 */
static void tinh_khoa(const char *b, const int *mv, int n, int mv_tt, int ply,
                      int *khoa) {
    for (int i = 0; i < n; i++) khoa[i] = khoa_sap_xep(b, mv[i], mv_tt, ply);
}

/* Chon nuoc tot nhat con lai va dua len vi tri i, GIU NGUYEN thu tu tuong doi
   cua nhung nuoc con lai.
   Ban dau viet kieu hoan doi cho nhanh, nhung no xao tron thu tu cua cac nuoc
   co diem BANG NHAU - ma nuoc thuong thi diem bang nhau rat nhieu. Ket qua la
   thu tu thu nuoc kem di va so nut TANG len (depth 11: 4,1 trieu -> 5,1 trieu).
   Nay dich ca doan mot buoc thay vi hoan doi, giu dung thu tu nhu sap xep on
   dinh truoc day. */
static inline void chon_tot_nhat(int *mv, int *khoa, int n, int i) {
    int tot = i;
    for (int j = i + 1; j < n; j++) if (khoa[j] < khoa[tot]) tot = j;
    if (tot != i) {
        int m = mv[tot], k = khoa[tot];
        for (int j = tot; j > i; j--) { mv[j] = mv[j - 1]; khoa[j] = khoa[j - 1]; }
        mv[i] = m; khoa[i] = k;
    }
}

static inline float *acc_o(int ply) {
    return ACC_STACK + (size_t)ply * SO_TICH_LUY;
}

/* Danh gia tai nut: dung tich luy da tinh san cho ply nay.
   Neu vuot ngan xep (quiescence rat sau khi bi chieu lien tuc) thi tinh lai
   tu dau - dung nhung cham, va truong hop do rat hiem. */
static int danh_gia(const char *b, int trang, int ply) {
    if (ply < ACC_PLY_MAX)
        return danh_gia_voi_acc(b, trang, acc_o(ply), TRONG_SO_MANG, LECH_HIEU_CHINH);
    return qs_danh_gia_tron(b, trang, TRONG_SO_MANG, LECH_HIEU_CHINH);
}

/* Chuan bi tich luy cho nut con truoc khi di xuong */
static inline void acc_xuong(int ply, char q_di, int from, int to, char q_an) {
    if (ply + 1 < ACC_PLY_MAX)
        acc_cap_nhat(acc_o(ply), acc_o(ply + 1), q_di, from, to, q_an);
}

static int quiescence(char *b, int trang, int alpha, int beta,
                      int ply, int ply_goc) {
    SO_NUT++;
    int bi_chieu = qs_bi_chieu(b, trang);
    int dung_yen = danh_gia(b, trang, ply_goc + ply);
    if (ply >= QUIESCENCE_TOI_DA && !bi_chieu) return dung_yen;

    int mv[256];
    int n = gen_legal_tai_cho(b, trang, mv);
    if (n == 0) return diem_cuoi(trang, ply_goc + ply);

    if (!bi_chieu) {                       /* the co yen: chi xet nuoc an quan */
        int m = 0;
        for (int i = 0; i < n; i++) if (b[mv[i] & 127] != '.') mv[m++] = mv[i];
        n = m;
        if (n == 0) return dung_yen;
    }
    int khoa[256];
    tinh_khoa(b, mv, n, -1, ply_goc + ply, khoa);

    if (trang) {
        int tot = bi_chieu ? -1000000 : dung_yen;
        if (!bi_chieu) {
            if (dung_yen >= beta) return dung_yen;
            if (dung_yen > alpha) alpha = dung_yen;
        }
        for (int i = 0; i < n; i++) {
            chon_tot_nhat(mv, khoa, n, i);
            int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
            char q_di = b[from], q_an = b[to];
            acc_xuong(ply_goc + ply, q_di, from, to, q_an);
            b[to] = q_di; b[from] = '.';
            int sc = quiescence(b, 0, alpha, beta, ply + 1, ply_goc);
            b[from] = q_di; b[to] = q_an;
            if (sc > tot) tot = sc;
            if (tot > alpha) alpha = tot;
            if (alpha >= beta) break;
        }
        return tot;
    } else {
        int tot = bi_chieu ? 1000000 : dung_yen;
        if (!bi_chieu) {
            if (dung_yen <= alpha) return dung_yen;
            if (dung_yen < beta) beta = dung_yen;
        }
        for (int i = 0; i < n; i++) {
            chon_tot_nhat(mv, khoa, n, i);
            int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
            char q_di = b[from], q_an = b[to];
            acc_xuong(ply_goc + ply, q_di, from, to, q_an);
            b[to] = q_di; b[from] = '.';
            int sc = quiescence(b, 1, alpha, beta, ply + 1, ply_goc);
            b[from] = q_di; b[to] = q_an;
            if (sc < tot) tot = sc;
            if (tot < beta) beta = tot;
            if (alpha >= beta) break;
        }
        return tot;
    }
}

#define NULL_R 2
#define NULL_MIN_DEPTH 3
#define LMR_MIN_DEPTH 3
#define LMR_SAU_NUOC 3

static int co_quan_manh(const char *b, int trang) {
    const char *m = trang ? "RHC" : "rhc";
    for (int sq = 0; sq < 90; sq++) {
        char p = b[sq];
        if (p == m[0] || p == m[1] || p == m[2]) return 1;
    }
    return 0;
}

static void ghi_cat_tia(const char *b, int mv, int ply, int do_sau) {
    if (b[mv & 127] != '.') return;          /* nuoc an quan da co MVV-LVA lo */
    if (ply < PLY_TOI_DA && KILLER[ply][0] != mv) {
        KILLER[ply][1] = KILLER[ply][0];
        KILLER[ply][0] = mv;
    }
    HISTORY[((mv >> 8) & 127) * 90 + (mv & 127)] += do_sau * do_sau;
}

static int tim(char *b, int trang, int do_sau, int alpha, int beta,
               int ply, int cho_bo_luot, int *nuoc_ra) {
    SO_NUT++;
    int alpha_goc = alpha, beta_goc = beta;
    unsigned long long khoa = qs_bam(b, trang);
    TTMuc *muc = &TT[khoa & (TT_SO - 1)];
    int mv_tt = -1;
    if (muc->khoa == khoa) {
        mv_tt = muc->nuoc;
        if (muc->do_sau >= do_sau) {
            if (muc->co == 0) { if (nuoc_ra) *nuoc_ra = muc->nuoc; return muc->diem; }
            if (muc->co == 1) { if (muc->diem > alpha) alpha = muc->diem; }
            else              { if (muc->diem < beta)  beta  = muc->diem; }
            if (alpha >= beta) { if (nuoc_ra) *nuoc_ra = muc->nuoc; return muc->diem; }
        }
    }
    if (nuoc_ra) *nuoc_ra = -1;
    if (do_sau == 0) return quiescence(b, trang, alpha, beta, 0, ply);

    int mv[256];
    int n = gen_legal_tai_cho(b, trang, mv);
    if (n == 0) return diem_cuoi(trang, ply);

    int bi_chieu = qs_bi_chieu(b, trang);

    /* --- Null-move pruning --- */
    if (cho_bo_luot && ply > 0 && do_sau >= NULL_MIN_DEPTH && !bi_chieu
            && co_quan_manh(b, trang)) {
        int d = do_sau - 1 - NULL_R;
        if (d > 0 && ply + 1 < ACC_PLY_MAX) {
            /* Bo luot khong doi ban co -> tich luy giu nguyen */
            memcpy(acc_o(ply + 1), acc_o(ply), sizeof(float) * SO_TICH_LUY);
            if (trang) {
                int sc = tim(b, 0, d, beta - 1, beta, ply + 1, 0, 0);
                if (sc >= beta) return beta;
            } else {
                int sc = tim(b, 1, d, alpha, alpha + 1, ply + 1, 0, 0);
                if (sc <= alpha) return alpha;
            }
        }
    }

    int khoa_mv[256];
    tinh_khoa(b, mv, n, mv_tt, ply, khoa_mv);
    int tot_nuoc = -1, tot_diem;

    if (trang) {
        tot_diem = -1000000;
        for (int i = 0; i < n; i++) {
            chon_tot_nhat(mv, khoa_mv, n, i);
            int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
            int la_an_quan = (b[to] != '.');
            char q_di = b[from], q_an = b[to];
            int giam = 0;
            if (i >= LMR_SAU_NUOC && do_sau >= LMR_MIN_DEPTH && !bi_chieu
                    && !la_an_quan) {
                giam = (i < 7) ? 1 : 2;
                if (giam >= do_sau) giam = do_sau - 1;
            }
            acc_xuong(ply, q_di, from, to, q_an);
            b[to] = q_di; b[from] = '.';
            /* Keo dai khi chieu: neu nuoc nay chieu doi phuong thi tim them
               mot tang. Cac chuoi chieu thuong dan toi bat quan hoac chieu het,
               cat chung o do sau co dinh la de bo sot. */
            int them = (KEO_DAI_CHIEU && qs_bi_chieu(b, 0)) ? 1 : 0;
            int bo_qua = 0;
            if (giam) {
                int sc = tim(b, 0, do_sau - 1 - giam, alpha, alpha + 1,
                             ply + 1, 1, 0);
                if (sc <= alpha) bo_qua = 1;
            }
            int sc = 0;
            if (!bo_qua) sc = tim(b, 0, do_sau - 1 + them, alpha, beta, ply + 1, 1, 0);
            b[from] = q_di; b[to] = q_an;
            if (bo_qua) continue;
            if (sc > tot_diem) { tot_diem = sc; tot_nuoc = mv[i]; }
            if (tot_diem > alpha) alpha = tot_diem;
            if (alpha >= beta) { ghi_cat_tia(b, mv[i], ply, do_sau); break; }
        }
    } else {
        tot_diem = 1000000;
        for (int i = 0; i < n; i++) {
            chon_tot_nhat(mv, khoa_mv, n, i);
            int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
            int la_an_quan = (b[to] != '.');
            char q_di = b[from], q_an = b[to];
            int giam = 0;
            if (i >= LMR_SAU_NUOC && do_sau >= LMR_MIN_DEPTH && !bi_chieu
                    && !la_an_quan) {
                giam = (i < 7) ? 1 : 2;
                if (giam >= do_sau) giam = do_sau - 1;
            }
            acc_xuong(ply, q_di, from, to, q_an);
            b[to] = q_di; b[from] = '.';
            int them = (KEO_DAI_CHIEU && qs_bi_chieu(b, 1)) ? 1 : 0;
            int bo_qua = 0;
            if (giam) {
                int sc = tim(b, 1, do_sau - 1 - giam, beta - 1, beta,
                             ply + 1, 1, 0);
                if (sc >= beta) bo_qua = 1;
            }
            int sc = 0;
            if (!bo_qua) sc = tim(b, 1, do_sau - 1 + them, alpha, beta, ply + 1, 1, 0);
            b[from] = q_di; b[to] = q_an;
            if (bo_qua) continue;
            if (sc < tot_diem) { tot_diem = sc; tot_nuoc = mv[i]; }
            if (tot_diem < beta) beta = tot_diem;
            if (alpha >= beta) { ghi_cat_tia(b, mv[i], ply, do_sau); break; }
        }
    }

    if (tot_nuoc < 0) {          /* moi nuoc bi LMR cat -> tim lai day du */
        tot_diem = trang ? -1000000 : 1000000;
        for (int i = 0; i < n; i++) {
            int from = (mv[i] >> 8) & 127, to = mv[i] & 127;
            char q_di = b[from], q_an = b[to];
            acc_xuong(ply, q_di, from, to, q_an);
            b[to] = q_di; b[from] = '.';
            int sc = tim(b, !trang, do_sau - 1, alpha_goc, beta_goc,
                         ply + 1, 1, 0);
            b[from] = q_di; b[to] = q_an;
            if (trang ? (sc > tot_diem) : (sc < tot_diem)) {
                tot_diem = sc; tot_nuoc = mv[i];
            }
        }
    }

    /* Diem chieu het phu thuoc do sau tuong doi -> khong luu vao bang */
    if (tot_diem > DIEM_MIN + BIEN_CHIEU_HET && tot_diem < DIEM_MAX - BIEN_CHIEU_HET) {
        muc->khoa = khoa; muc->diem = tot_diem; muc->do_sau = (short)do_sau;
        muc->nuoc = tot_nuoc;
        muc->co = (tot_diem <= alpha_goc) ? 2 : ((tot_diem >= beta_goc) ? 1 : 0);
    }
    if (nuoc_ra) *nuoc_ra = tot_nuoc;
    return tot_diem;
}

/* Diem tra ve qua *diem, nuoc di la gia tri tra ve. -1 neu khong co nuoc nao. */
int qs_tim_kiem(const char *b_in, int trang, int do_sau, int *diem, long long *so_nut) {
    char b[90];
    memcpy(b, b_in, 90);
    if (!TT) qs_tim_kiem_khoi_tao(TRONG_SO_MANG, LECH_HIEU_CHINH);
    for (int i = 0; i < TT_SO; i++) TT[i].khoa = 0;
    xoa_heuristic();
    if (ACC_STACK) acc_tu_dau(b, acc_o(0));
    SO_NUT = 0;
    int nuoc = -1, d_cuoi = 500;
    /* --- Iterative deepening kem ASPIRATION WINDOW ---
     * Diem cua vong sau thuong rat gan diem vong truoc. Nen thay vi tim voi
     * cua so day du [0, 1000], ta tim voi cua so hep quanh diem cu. Cua so hep
     * lam alpha-beta cat som hon nhieu. Neu diem that roi ra ngoai cua so
     * (fail high/low) thi noi rong ra tim lai - it khi xay ra nen van loi.
     */
    for (int d = 1; d <= do_sau; d++) {
        int n_tmp = -1;
        if (d <= 3) {
            d_cuoi = tim(b, trang, d, DIEM_MIN, DIEM_MAX, 0, 1, &n_tmp);
        } else {
            int rong = 12;
            while (1) {
                int a = d_cuoi - rong, be = d_cuoi + rong;
                if (a < DIEM_MIN) a = DIEM_MIN;
                if (be > DIEM_MAX) be = DIEM_MAX;
                int sc = tim(b, trang, d, a, be, 0, 1, &n_tmp);
                if ((sc > a && sc < be) || (a == DIEM_MIN && be == DIEM_MAX)) {
                    d_cuoi = sc;
                    break;
                }
                rong *= 4;               /* ra ngoai cua so -> noi rong tim lai */
                if (rong > 1000) { a = DIEM_MIN; be = DIEM_MAX; }
            }
        }
        if (n_tmp >= 0) nuoc = n_tmp;
    }
    if (diem) *diem = d_cuoi;
    if (so_nut) *so_nut = SO_NUT;
    return nuoc;
}
