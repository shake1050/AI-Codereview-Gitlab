@echo off
REM ============================================================
REM SVN Hook Deployment Configuration
REM Edit this file before running deploy_hooks_to_all_repos.bat
REM ============================================================

REM ==================== Required Configuration ====================

REM SVN Repository Root Path
set REPOSITORIES_PATH=D:\Repositories

REM AI Code Review System API URL
set REVIEW_API_URL=http://10.10.9.12:5001/review/webhook

REM SVN Server URL (without repository name)
set SVN_SERVER_URL=http://10.10.9.12/svn

REM ==================== Optional Configuration ====================

REM Skip existing hooks (1=skip, 0=overwrite for updates)
set SKIP_EXISTING=0
