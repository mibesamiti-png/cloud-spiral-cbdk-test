@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "BLENDER="
if not "%~1"=="" if exist "%~1" set "BLENDER=%~1"
if not defined BLENDER if exist "%ProgramFiles%\Blender Foundation\Blender 4.4\blender.exe" set "BLENDER=%ProgramFiles%\Blender Foundation\Blender 4.4\blender.exe"
if not defined BLENDER if exist "%ProgramFiles%\Blender Foundation\Blender 4.5\blender.exe" set "BLENDER=%ProgramFiles%\Blender Foundation\Blender 4.5\blender.exe"
if not defined BLENDER if exist "%ProgramFiles%\Blender Foundation\Blender 5.2\blender.exe" set "BLENDER=%ProgramFiles%\Blender Foundation\Blender 5.2\blender.exe"
if not defined BLENDER (
  echo [Cloud Spiral] Blender was not found automatically.
  echo Drag your blender.exe onto run_windows_review.bat to select it.
  echo This is a test scene; it does not overwrite your projects.
  pause
  exit /b 2
)
if not exist "%~dp0addon\cloud_spiral_lobe_builder_v04.py" (
  echo [Cloud Spiral] Missing addon\cloud_spiral_lobe_builder_v04.py
  pause
  exit /b 3
)
if not exist "%~dp0scripts\windows_review_session.py" (
  echo [Cloud Spiral] Missing scripts\windows_review_session.py
  pause
  exit /b 3
)
if not exist "%~dp0qa-output" mkdir "%~dp0qa-output"
echo [Cloud Spiral] Using Blender: "%BLENDER%"
echo [Cloud Spiral] Starting an isolated factory-startup review session...
echo [Cloud Spiral] Review results are saved in qa-output; no project is overwritten.
start "Cloud Spiral Windows Review" "%BLENDER%" --factory-startup --python "%~dp0scripts\windows_review_session.py" -- "%~dp0addon\cloud_spiral_lobe_builder_v04.py" "%~dp0qa-output"
if errorlevel 1 (
  echo [Cloud Spiral] Could not start Blender.
  pause
  exit /b 4
)
exit /b 0
