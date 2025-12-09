@echo off
REM ============================================================
REM SVN Hook Deployment Script (Batch Version)
REM Auto-deploy post-commit hooks to all VisualSVN Server repositories
REM ============================================================

setlocal enabledelayedexpansion

REM Hook scripts directory
set HOOK_SCRIPTS_PATH=%~dp0

REM Load configuration file
set CONFIG_FILE=%HOOK_SCRIPTS_PATH%deploy_config.bat
if exist "%CONFIG_FILE%" (
    call "%CONFIG_FILE%"
    echo [INFO] Loaded config from deploy_config.bat
) else (
    echo [WARNING] Config file not found, using defaults
    REM Default configuration
    set REPOSITORIES_PATH=D:\Repositories
    set REVIEW_API_URL=http://10.10.9.12:5001/review/webhook
    set SVN_SERVER_URL=http://10.10.9.12/svn
    set SKIP_EXISTING=1
)

REM Color codes removed for compatibility

echo.
echo ========================================
echo SVN Hook Deployment Script
echo ========================================
echo.

REM Check administrator privileges
net session >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Recommend running as administrator
    echo.
)

REM Validate repository directory
if not exist "%REPOSITORIES_PATH%" (
    echo [ERROR] Repository directory not found: %REPOSITORIES_PATH%
    echo Please check VisualSVN Server repository path or modify REPOSITORIES_PATH
    pause
    exit /b 1
)

echo [INFO] Repository Path: %REPOSITORIES_PATH%
echo [INFO] Hook Scripts Path: %HOOK_SCRIPTS_PATH%
echo [INFO] Review API URL: %REVIEW_API_URL%
echo [INFO] SVN Server URL: %SVN_SERVER_URL%
echo.

REM Validate hook script files
set POST_COMMIT_BAT=%HOOK_SCRIPTS_PATH%post-commit.bat
set SVN_HOOK_PY=%HOOK_SCRIPTS_PATH%svn_post_commit_hook.py

if not exist "%POST_COMMIT_BAT%" (
    echo [ERROR] post-commit.bat not found: %POST_COMMIT_BAT%
    pause
    exit /b 1
)

if not exist "%SVN_HOOK_PY%" (
    echo [ERROR] svn_post_commit_hook.py not found: %SVN_HOOK_PY%
    pause
    exit /b 1
)

echo [SUCCESS] Hook script files validated
echo.

REM Statistics
set TOTAL=0
set SUCCESS=0
set SKIPPED=0
set FAILED=0

REM Check if path itself is a repository (contains conf directory)
if exist "%REPOSITORIES_PATH%\conf" (
    REM Path is a repository, process directly
    for %%P in ("%REPOSITORIES_PATH%") do set REPO_NAME=%%~nxP
    set REPO_PATH=%REPOSITORIES_PATH%
    set HOOKS_DIR=!REPO_PATH!\hooks
    set TARGET_BAT=!HOOKS_DIR!\post-commit.bat
    set TARGET_PY=!HOOKS_DIR!\svn_post_commit_hook.py
    set IS_VALID_REPO=1
    set PROCESS_SINGLE_REPO=1
) else (
    REM Path contains multiple repositories, traverse subdirectories
    set PROCESS_SINGLE_REPO=0
)

REM Process single repository or traverse multiple repositories
if !PROCESS_SINGLE_REPO! equ 1 (
    REM Process single repository
    call :process_repo
) else (
    REM Traverse all repositories
    for /d %%R in ("%REPOSITORIES_PATH%\*") do (
        set REPO_NAME=%%~nxR
        set REPO_PATH=%%R
        set HOOKS_DIR=!REPO_PATH!\hooks
        set TARGET_BAT=!HOOKS_DIR!\post-commit.bat
        set TARGET_PY=!HOOKS_DIR!\svn_post_commit_hook.py
        
        REM Check if valid SVN repository (contains conf or hooks directory)
        if exist "!REPO_PATH!\conf" (
            set IS_VALID_REPO=1
        ) else if exist "!HOOKS_DIR!" (
            set IS_VALID_REPO=1
        ) else (
            set IS_VALID_REPO=0
        )
        
        REM Process repository
        call :process_repo
    )
)

goto :end_processing

:process_repo
REM Subroutine to process single repository
if !IS_VALID_REPO! equ 1 (
    set /a TOTAL+=1
    
    echo ----------------------------------------
    echo [INFO] Processing repository: !REPO_NAME!
    
    REM Create hooks directory if not exists
    if not exist "!HOOKS_DIR!" (
        echo [INFO]   Creating hooks directory...
        mkdir "!HOOKS_DIR!" >nul 2>&1
        if errorlevel 1 (
            echo [ERROR]   Failed to create hooks directory
            set /a FAILED+=1
            exit /b
        )
        echo [SUCCESS]   Hooks directory created
    )
    
    REM Check if files already exist
    set BAT_EXISTS=0
    set PY_EXISTS=0
    if exist "!TARGET_BAT!" set BAT_EXISTS=1
    if exist "!TARGET_PY!" set PY_EXISTS=1
    
    REM Decide whether to skip based on configuration
    if "%SKIP_EXISTING%"=="1" (
        REM Skip if both files exist
        if !BAT_EXISTS! equ 1 if !PY_EXISTS! equ 1 (
            echo [WARNING]   Hook files exist, skipping
            set /a SKIPPED+=1
            exit /b
        )
        
        REM Skip if only one file exists (for consistency)
        if !BAT_EXISTS! equ 1 (
            echo [WARNING]   post-commit.bat exists, skipping
            set /a SKIPPED+=1
            exit /b
        )
        
        if !PY_EXISTS! equ 1 (
            echo [WARNING]   svn_post_commit_hook.py exists, skipping
            set /a SKIPPED+=1
            exit /b
        )
    ) else (
        if !BAT_EXISTS! equ 1 if !PY_EXISTS! equ 1 (
            echo [INFO]   Hook files exist, will overwrite
        )
    )
    
    REM Deploy files
    REM Copy post-commit.bat (binary copy to preserve original)
    echo [INFO]   Deploying post-commit.bat...
    copy /B /Y "%POST_COMMIT_BAT%" "!TARGET_BAT!" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR]   Failed to copy post-commit.bat
        set /a FAILED+=1
    ) else (
        echo [SUCCESS]   post-commit.bat deployed
        
        REM Copy and configure svn_post_commit_hook.py
        echo [INFO]   Deploying and configuring svn_post_commit_hook.py...
        set REPO_FULL_URL=%SVN_SERVER_URL%/!REPO_NAME!/
        
        REM Use PowerShell to copy and modify config (preserve UTF-8 encoding)
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $content = [System.IO.File]::ReadAllText('%SVN_HOOK_PY%', [System.Text.UTF8Encoding]::new($false)); $content = $content -replace 'REVIEW_API_URL = os\.getenv\(''SVN_REVIEW_API_URL'', \".*?\"\)', 'REVIEW_API_URL = os.getenv(''SVN_REVIEW_API_URL'', \"!REVIEW_API_URL!\")'; $content = $content -replace 'REPO_URL = os\.getenv\(''SVN_REPO_URL'', \".*?\"\)', 'REPO_URL = os.getenv(''SVN_REPO_URL'', \"!REPO_FULL_URL!\")'; [System.IO.File]::WriteAllText('!TARGET_PY!', $content, [System.Text.UTF8Encoding]::new($false)); exit 0 } catch { Write-Error $_.Exception.Message; exit 1 }"
        
        if errorlevel 1 (
            echo [ERROR]   Failed to deploy svn_post_commit_hook.py
            set /a FAILED+=1
        ) else (
            echo [SUCCESS]   svn_post_commit_hook.py deployed and configured
            echo [INFO]   Config: !REPO_FULL_URL!
        )
            
            REM Verify files
            if exist "!TARGET_BAT!" if exist "!TARGET_PY!" (
                echo [SUCCESS]   Repository !REPO_NAME! hook deployment complete
                set /a SUCCESS+=1
            ) else (
                echo [ERROR]   File verification failed
                set /a FAILED+=1
            )
        )
    )
)
exit /b

:end_processing
REM Output statistics
echo.
echo ========================================
echo Deployment Statistics
echo ========================================
echo [INFO] Total repositories: %TOTAL%
echo [SUCCESS] Successful: %SUCCESS%
echo [WARNING] Skipped: %SKIPPED%
if %FAILED% gtr 0 (
    echo [ERROR] Failed: %FAILED%
)
echo.

REM Next steps
if %SUCCESS% gtr 0 (
    echo ========================================
    echo Next Steps
    echo ========================================
    echo [INFO] 1. Configuration has been auto-updated in each repository
    echo [INFO]    - REVIEW_API_URL: %REVIEW_API_URL%
    echo [INFO]    - REPO_URL: Auto-generated based on repository name
    echo.
    echo [INFO] 2. To modify configuration:
    echo [INFO]    - Edit deploy_config.bat and set SKIP_EXISTING=0
    echo [INFO]    - Or use environment variables SVN_REVIEW_API_URL and SVN_REPO_URL
    echo.
    echo [INFO] 3. Test the hook:
    echo [INFO]    Commit code to any repository and check if review system receives webhook
    echo.
)

pause

