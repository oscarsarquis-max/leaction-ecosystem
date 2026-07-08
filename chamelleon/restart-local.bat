@echo off
cd /d "%~dp0"
echo.
echo Reiniciando Chamelleon...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart-local.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao reiniciar. Veja as mensagens acima.
  pause
  exit /b 1
)
echo.
pause
