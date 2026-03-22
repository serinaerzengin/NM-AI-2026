@echo off
REM Create a Windows Task Scheduler task to run auto_round.py every 2 hours 54 minutes (174 min)
REM Run this script once as Administrator to set up the schedule.

set PYTHON_PATH=C:\Python314\python.exe
set SCRIPT_PATH=C:\Users\light\Documents\ntnu\NM-AI-2026\task2-AstarIsland\auto_round.py
set WORK_DIR=C:\Users\light\Documents\ntnu\NM-AI-2026\task2-AstarIsland

schtasks /create /tn "AstarIsland_AutoRound" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc minute /mo 174 /f /rl HIGHEST

echo.
echo Task "AstarIsland_AutoRound" created. Runs every 174 minutes (2h54m).
echo.
echo To check:   schtasks /query /tn "AstarIsland_AutoRound"
echo To delete:   schtasks /delete /tn "AstarIsland_AutoRound" /f
echo To run now:  schtasks /run /tn "AstarIsland_AutoRound"
pause
