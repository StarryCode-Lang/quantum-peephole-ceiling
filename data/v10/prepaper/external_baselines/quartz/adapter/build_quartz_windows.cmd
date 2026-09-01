@echo off
setlocal
if "%~1"=="" (
  echo Usage: build_quartz_windows.cmd ^<python.exe^>
  exit /b 2
)
set "QUARTZ_PYTHON=%~1"
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
cmake -S "%~dp0..\repo" -B "%~dp0..\build-ninja" -G Ninja -DPython_EXECUTABLE="%QUARTZ_PYTHON%"
if errorlevel 1 exit /b %errorlevel%
cmake --build "%~dp0..\build-ninja" --target test_optimize -j 4
exit /b %errorlevel%
