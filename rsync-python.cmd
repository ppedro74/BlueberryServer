@echo off

set SRC_DIR=/c/dev/BlueberryServer/Blueberry.Server.Python
set DST_SERVER1=rpi-buster-4g.local
set DST_SERVER2=rpi-mate-xenial1.local
set DST_USER=ptp
set DST_DIR=~/dev
set DST_PORT=22
set KEY_FILE=C:\Users\ptp\Dropbox\Keys\nuci7-priv.ppk


rem rsync -ruzv -batch %SRC_DIR% %DST_USER%@%DST_SERVER1%:%DST_DIR%
rsync -ruzv -batch %SRC_DIR% %DST_USER%@%DST_SERVER2%:%DST_DIR%