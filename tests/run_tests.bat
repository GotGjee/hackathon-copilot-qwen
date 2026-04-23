@echo off
echo ============================================
echo Hackathon Copilot - Test Suite
echo ============================================
echo.

REM Install test dependencies if not already installed
pip install pytest pytest-asyncio -q 2>nul

echo Running tests...
echo.

REM Run pytest with verbose output
cd /d "%~dp0.."
python -m pytest tests/ -v --tb=short --color=yes

echo.
echo ============================================
echo Test run complete
echo ============================================

REM Pause to see results
pause