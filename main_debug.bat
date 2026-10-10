@echo off
python "%~dp0main.py" --debug %*
if errorlevel 1 pause
