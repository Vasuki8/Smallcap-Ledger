@echo off
setlocal
cd /d "%~dp0"
title Smallcap Ledger
where uv >nul 2>nul
if %errorlevel%==0 (
  uv run --frozen python -m tracker
  goto finish
)
if exist "%USERPROFILE%\.local\bin\uv.exe" (
  "%USERPROFILE%\.local\bin\uv.exe" run --frozen python -m tracker
  goto finish
)
echo uv is not installed or could not be found.
echo.
echo Open PowerShell and run this official installation command:
echo powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
echo.
echo Close and reopen this launcher after installing uv.
echo See START-HERE.md for full instructions.
:finish
echo.
echo The tracker window has stopped. Existing data is retained.
pause
