#!/bin/bash
# Bien dich phan loi C. Chay: bash csrc/build.sh
# Neu khong bien dich duoc, engine tu dong chay bang Python thuan.
cd "$(dirname "$0")/.."
cc -O3 -shared -fPIC -o engine/libxuanwu.so csrc/xuanwu.c && \
    echo "Da bien dich engine/libxuanwu.so" || \
    echo "Khong bien dich duoc - engine se chay bang Python thuan"
