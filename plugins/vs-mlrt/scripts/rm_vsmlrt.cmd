@echo off
set RM_VSMLRT_DEFER_ENTRY_CLEANUP=1
if exist "%~dp0python.exe" goto local_python
python -m rm_vsmlrt %* & exit /b
:local_python
"%~dp0python.exe" -m rm_vsmlrt %* & exit /b
