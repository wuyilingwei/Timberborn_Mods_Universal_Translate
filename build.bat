@echo off
title TMT Builder
pip install -r requirements.txt
pyinstaller main.spec
echo all down, file in dist folder.
timeout /t 5 /nobreak
exit 