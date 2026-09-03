#!/bin/zsh
# QiSheng: tu dong dung moi job thu thap vao gio chi dinh (mac dinh 2100)
STOP_AT=${1:-2100}
while [ "$(date +%H%M)" -lt "$STOP_AT" ]; do sleep 15; done
pkill -f collect_positions.py
pkill -f collect_xiangqi_data.py
pkill -f "caffeinate -i -w"
echo "$(date '+%F %H:%M:%S') - QiSheng: da dung moi job thu thap" >> qisheng_shutdown.log
