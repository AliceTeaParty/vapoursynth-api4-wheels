@echo off
setlocal EnableExtensions EnableDelayedExpansion
if exist "%~dp0python.exe" ("%~dp0python.exe" -m rm_vsmlrt %* & exit /b !ERRORLEVEL!) else (python -m rm_vsmlrt %* & exit /b !ERRORLEVEL!)
