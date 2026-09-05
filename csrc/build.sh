#!/bin/bash
# Bien dich phan loi C. Chay: bash csrc/build.sh
# Neu khong bien dich duoc, engine tu dong chay bang Python thuan.
cd "$(dirname "$0")/.."
cc -O3 -shared -fPIC -o engine/libqisheng.so csrc/qisheng.c && \
    echo "Da bien dich engine/libqisheng.so" || \
    echo "Khong bien dich duoc - engine se chay bang Python thuan"
