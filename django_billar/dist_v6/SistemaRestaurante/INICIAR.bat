@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" SistemaRestaurante.exe
timeout /t 10 /nobreak
start http://localhost:8000
