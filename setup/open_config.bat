@echo off
echo Opening BuildBot configuration file...
cd /d "D:\ai module\New-task1-AI devops\buildbot"

if exist ".env" (
    notepad .env
) else (
    echo .env file not found! Creating from template...
    copy .env.example .env
    notepad .env
)
