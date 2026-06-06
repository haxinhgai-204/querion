@echo off
REM ============================================================
REM  Querion - Stop All Services (double-click to run)
REM ============================================================

powershell -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
pause
