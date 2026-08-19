@echo off
cd /d "%~dp0"
python -m msfs_resume
if errorlevel 1 pause
