@echo off
setlocal
if exist "%~dp0python.exe" (
  "%~dp0python.exe" -m rm_vsmlrt %*
) else (
  python -m rm_vsmlrt %*
)
set "exit_code=%ERRORLEVEL%"
endlocal & exit /b %exit_code%
