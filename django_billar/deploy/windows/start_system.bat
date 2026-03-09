@echo off
cd /d %~dp0\..\..
if not exist venv\Scripts\python.exe (
  echo Ambiente virtual nao encontrado.
  pause
  exit /b 1
)
venv\Scripts\python.exe deploy\windows\launcher.py
