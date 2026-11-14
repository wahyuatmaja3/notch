@echo off
:: Launches Notch Dynamic Island quietly in the background (no console window)
cd /d "%~dp0notch_py"
start "" "C:\Users\operator\AppData\Local\Programs\Python\Python311\pythonw.exe" main.py
exit
