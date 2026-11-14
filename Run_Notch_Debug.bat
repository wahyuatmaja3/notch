@echo off
:: Launches Notch Dynamic Island with a visible console to show logs and errors
title Notch Dynamic Island (Debug)
cd /d "%~dp0notch_py"
"C:\Users\operator\AppData\Local\Programs\Python\Python311\python.exe" main.py
pause
