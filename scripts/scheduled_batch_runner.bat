@echo off
REM Scheduled batch runner helper for Windows Task Scheduler.
REM
REM Usage:
REM   scheduled_batch_runner.bat --run-once
REM   scheduled_batch_runner.bat --watch
REM   scheduled_batch_runner.bat --watch --interval 30
REM
REM Register with Task Scheduler (run on machine startup or on a schedule):
REM   schtasks /create /tn "UP Police Analyst Batch" /tr "F:\Hermes_Project\scripts\scheduled_batch_runner.bat --run-once" /sc daily /st 03:00 /f
setlocal ENABLEDELAYEDEXPANSION

cd /d F:\Hermes_Project

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv python.exe. Run `uv sync` first.
  exit /b 1
)

.venv\Scripts\python.exe scripts\scheduled_batch_runner.py %*
set EXIT_CODE=%ERRORLEVEL%

exit /b %EXIT_CODE%
