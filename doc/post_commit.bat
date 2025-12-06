@echo off
REM ============================================================
REM SVN Post-Commit Hook Script for VisualSVN Server
REM 用于将SVN提交事件发送到AI代码审查系统
REM 
REM 配置说明：
REM 1. 将此文件复制到VisualSVN Server的hooks目录：
REM    C:\Repositories\<RepositoryName>\hooks\post-commit.bat
REM 2. 将svn_post_commit_hook.py复制到同一目录
REM 3. 修改Python路径（如果需要）
REM 4. 配置在svn_post_commit_hook.py中完成
REM ============================================================

setlocal enabledelayedexpansion

REM 创建日志文件路径（用于调试和错误追踪）
set LOG_FILE=%~dp0post-commit.log

REM ==================== 配置区域 ====================
REM Python路径配置
REM 方法1：如果Python在系统PATH中，直接使用（默认）
REM 方法2：如果Python不在PATH中，取消下面一行的注释并修改为您的Python完整路径
REM 方法3：如果都不行，脚本会自动尝试常见路径

REM 优先使用配置的路径（如果设置了）
REM 取消下面的注释并修改为您的Python完整路径：
REM set PYTHON_PATH=C:\Python39\python.exe
REM 或者：
REM set PYTHON_PATH=C:\Program Files\Python39\python.exe
REM 或者：
REM set PYTHON_PATH=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\python.exe

REM 如果上面没有设置，则尝试使用PATH中的python命令
if not defined PYTHON_PATH (
    set PYTHON_PATH=python
)

REM 脚本路径（相对于当前bat文件所在目录）
REM VisualSVN Server会自动设置当前目录为hooks目录
set SCRIPT_PATH=%~dp0svn_post_commit_hook.py
REM ==================== 配置区域结束 ====================

REM 记录执行开始信息（用于调试）
echo [%date% %time%] Post-commit hook started >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Repository: %~1 >> "%LOG_FILE%" 2>&1
echo [%date% %time%] Revision: %~2 >> "%LOG_FILE%" 2>&1

REM 验证参数
if "%~1"=="" (
    echo Error: Missing repository path argument >&2
    exit /b 1
)

if "%~2"=="" (
    echo Error: Missing revision number argument >&2
    exit /b 1
)

REM 验证Python脚本是否存在
if not exist "%SCRIPT_PATH%" (
    echo Error: Python script not found at: %SCRIPT_PATH% >&2
    echo Please ensure svn_post_commit_hook.py is in the same directory as this batch file. >&2
    echo Current directory: %CD% >&2
    echo Batch file directory: %~dp0 >&2
    exit /b 1
)

REM 验证Python是否可用
%PYTHON_PATH% --version >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] Python not found with path: %PYTHON_PATH% >> "%LOG_FILE%" 2>&1
    echo Attempting to find Python in common locations... >> "%LOG_FILE%" 2>&1
    
    REM 尝试常见的Python安装路径
    set PYTHON_FOUND=0
    
    REM 尝试路径1: C:\Python3X\python.exe
    for /L %%i in (9,1,12) do (
        if !PYTHON_FOUND! equ 0 (
            if exist "C:\Python3%%i\python.exe" (
                set "PYTHON_PATH=C:\Python3%%i\python.exe"
                "!PYTHON_PATH!" --version >nul 2>&1
                if not errorlevel 1 (
                    set PYTHON_FOUND=1
                    echo [%date% %time%] Found Python at: !PYTHON_PATH! >> "%LOG_FILE%" 2>&1
                )
            )
        )
    )
    
    REM 尝试路径2: C:\Program Files\Python3X\python.exe
    if !PYTHON_FOUND! equ 0 (
        for /L %%i in (9,1,12) do (
            if !PYTHON_FOUND! equ 0 (
                if exist "C:\Program Files\Python3%%i\python.exe" (
                    set "PYTHON_PATH=C:\Program Files\Python3%%i\python.exe"
                    "!PYTHON_PATH!" --version >nul 2>&1
                    if not errorlevel 1 (
                        set PYTHON_FOUND=1
                        echo [%date% %time%] Found Python at: !PYTHON_PATH! >> "%LOG_FILE%" 2>&1
                    )
                )
            )
        )
    )
    
    REM 尝试路径3: 用户目录下的Python
    if !PYTHON_FOUND! equ 0 (
        for /L %%i in (9,1,12) do (
            if !PYTHON_FOUND! equ 0 (
                if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python3%%i\python.exe" (
                    set "PYTHON_PATH=%USERPROFILE%\AppData\Local\Programs\Python\Python3%%i\python.exe"
                    "!PYTHON_PATH!" --version >nul 2>&1
                    if not errorlevel 1 (
                        set PYTHON_FOUND=1
                        echo [%date% %time%] Found Python at: !PYTHON_PATH! >> "%LOG_FILE%" 2>&1
                    )
                )
            )
        )
    )
    
    REM 尝试路径4: py launcher (Python Launcher for Windows)
    if !PYTHON_FOUND! equ 0 (
        py --version >nul 2>&1
        if not errorlevel 1 (
            set PYTHON_PATH=py
            set PYTHON_FOUND=1
            echo [%date% %time%] Found Python via py launcher >> "%LOG_FILE%" 2>&1
        )
    )
    
    REM 如果仍然找不到Python
    if !PYTHON_FOUND! equ 0 (
        echo Error: Python not found. Please install Python 3.6+ or set PYTHON_PATH correctly. >&2
        echo. >&2
        echo Troubleshooting steps: >&2
        echo 1. Install Python 3.6 or later from https://www.python.org/downloads/ >&2
        echo 2. Or edit this batch file and set PYTHON_PATH to your Python executable path >&2
        echo 3. Common Python paths: >&2
        echo    - C:\Python39\python.exe >&2
        echo    - C:\Program Files\Python39\python.exe >&2
        echo    - %%USERPROFILE%%\AppData\Local\Programs\Python\Python39\python.exe >&2
        echo. >&2
        echo Check log file for details: %LOG_FILE% >&2
        echo [%date% %time%] Python detection failed. Searched common locations. >> "%LOG_FILE%" 2>&1
        exit /b 1
    )
)

REM 调用Python脚本
REM 使用引号包裹参数以处理路径中的空格
REM 注意：VisualSVN Server可能不会显示输出，所以错误信息也会写入日志文件
%PYTHON_PATH% "%SCRIPT_PATH%" "%~1" "%~2" >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

REM 如果Python脚本失败，记录详细信息
if %EXIT_CODE% neq 0 (
    echo [%date% %time%] Error: Hook script failed with exit code %EXIT_CODE% >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Repository: %~1 >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Revision: %~2 >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Python Path: %PYTHON_PATH% >> "%LOG_FILE%" 2>&1
    echo [%date% %time%] Script Path: %SCRIPT_PATH% >> "%LOG_FILE%" 2>&1
    echo Warning: Hook script returned error code %EXIT_CODE%, but continuing to avoid blocking commit. >&2
    echo Check log file for details: %LOG_FILE% >&2
)

REM 即使Python脚本失败，也返回0以避免阻塞SVN提交
REM 如果需要严格模式（失败时阻塞提交），可以改为：exit /b %EXIT_CODE%
exit /b 0
