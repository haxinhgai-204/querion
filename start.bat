@echo off
REM ============================================================
REM  Querion - Start All Services (double-click to run)
REM ============================================================

powershell -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
