@echo off
REM ============================================================
REM SVN Hook 一键部署脚本 (批处理版本)
REM 用于为 VisualSVN Server 的所有仓库自动部署 post-commit hook
REM ============================================================

setlocal enabledelayedexpansion

REM 配置参数（可根据实际情况修改）
set REPOSITORIES_PATH=D:\Repositories
set HOOK_SCRIPTS_PATH=%~dp0

REM 颜色输出（如果支持）
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "CYAN=[96m"
set "RESET=[0m"

echo.
echo ========================================
echo SVN Hook 一键部署脚本
echo ========================================
echo.

REM 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [警告] 建议以管理员权限运行此脚本
    echo.
)

REM 验证仓库目录
if not exist "%REPOSITORIES_PATH%" (
    echo [错误] 仓库目录不存在: %REPOSITORIES_PATH%
    echo 请检查 VisualSVN Server 的仓库路径，或修改脚本中的 REPOSITORIES_PATH 变量
    pause
    exit /b 1
)

echo [信息] 仓库目录: %REPOSITORIES_PATH%
echo [信息] Hook脚本目录: %HOOK_SCRIPTS_PATH%
echo.

REM 验证Hook脚本文件
set POST_COMMIT_BAT=%HOOK_SCRIPTS_PATH%post-commit.bat
set SVN_HOOK_PY=%HOOK_SCRIPTS_PATH%svn_post_commit_hook.py

if not exist "%POST_COMMIT_BAT%" (
    echo [错误] 找不到 post-commit.bat 文件: %POST_COMMIT_BAT%
    pause
    exit /b 1
)

if not exist "%SVN_HOOK_PY%" (
    echo [错误] 找不到 svn_post_commit_hook.py 文件: %SVN_HOOK_PY%
    pause
    exit /b 1
)

echo [成功] Hook脚本文件验证通过
echo.

REM 统计信息
set TOTAL=0
set SUCCESS=0
set SKIPPED=0
set FAILED=0

REM 检查指定路径本身是否是仓库（包含conf目录）
if exist "%REPOSITORIES_PATH%\conf" (
    REM 路径本身是仓库，直接处理
    for %%P in ("%REPOSITORIES_PATH%") do set REPO_NAME=%%~nxP
    set REPO_PATH=%REPOSITORIES_PATH%
    set HOOKS_DIR=!REPO_PATH!\hooks
    set TARGET_BAT=!HOOKS_DIR!\post-commit.bat
    set TARGET_PY=!HOOKS_DIR!\svn_post_commit_hook.py
    set IS_VALID_REPO=1
    set PROCESS_SINGLE_REPO=1
) else (
    REM 路径包含多个仓库，遍历子目录
    set PROCESS_SINGLE_REPO=0
)

REM 处理单个仓库或遍历多个仓库
if !PROCESS_SINGLE_REPO! equ 1 (
    REM 处理单个仓库
    call :process_repo
) else (
    REM 遍历所有仓库
    for /d %%R in ("%REPOSITORIES_PATH%\*") do (
        set REPO_NAME=%%~nxR
        set REPO_PATH=%%R
        set HOOKS_DIR=!REPO_PATH!\hooks
        set TARGET_BAT=!HOOKS_DIR!\post-commit.bat
        set TARGET_PY=!HOOKS_DIR!\svn_post_commit_hook.py
        
        REM 检查是否是有效的SVN仓库（包含conf或hooks目录）
        if exist "!REPO_PATH!\conf" (
            set IS_VALID_REPO=1
        ) else if exist "!HOOKS_DIR!" (
            set IS_VALID_REPO=1
        ) else (
            set IS_VALID_REPO=0
        )
        
        REM 处理仓库
        call :process_repo
    )
)

goto :end_processing

:process_repo
REM 处理单个仓库的子程序
if !IS_VALID_REPO! equ 1 (
    set /a TOTAL+=1
    
    echo ----------------------------------------
    echo [信息] 处理仓库: !REPO_NAME!
    
    REM 创建hooks目录（如果不存在）
    if not exist "!HOOKS_DIR!" (
        echo [信息]   创建hooks目录...
        mkdir "!HOOKS_DIR!" >nul 2>&1
        if errorlevel 1 (
            echo [错误]   无法创建hooks目录
            set /a FAILED+=1
            exit /b
        )
        echo [成功]   hooks目录已创建
    )
    
    REM 检查文件是否已存在
    set BAT_EXISTS=0
    set PY_EXISTS=0
    if exist "!TARGET_BAT!" set BAT_EXISTS=1
    if exist "!TARGET_PY!" set PY_EXISTS=1
    
    REM 如果文件都已存在，跳过整个仓库
    if !BAT_EXISTS! equ 1 if !PY_EXISTS! equ 1 (
        echo [警告]   Hook文件已存在，跳过此仓库
        set /a SKIPPED+=1
        exit /b
    )
    
    REM 如果只有一个文件存在，也跳过（保持一致性）
    if !BAT_EXISTS! equ 1 (
        echo [警告]   post-commit.bat 已存在，跳过此仓库
        set /a SKIPPED+=1
        exit /b
    )
    
    if !PY_EXISTS! equ 1 (
        echo [警告]   svn_post_commit_hook.py 已存在，跳过此仓库
        set /a SKIPPED+=1
        exit /b
    )
    
    REM 部署文件
    REM 复制 post-commit.bat
    echo [信息]   部署 post-commit.bat...
    copy /Y "%POST_COMMIT_BAT%" "!TARGET_BAT!" >nul 2>&1
    if errorlevel 1 (
        echo [错误]   复制 post-commit.bat 失败
        set /a FAILED+=1
    ) else (
        echo [成功]   post-commit.bat 部署成功
        
        REM 复制 svn_post_commit_hook.py
        echo [信息]   部署 svn_post_commit_hook.py...
        copy /Y "%SVN_HOOK_PY%" "!TARGET_PY!" >nul 2>&1
        if errorlevel 1 (
            echo [错误]   复制 svn_post_commit_hook.py 失败
            set /a FAILED+=1
        ) else (
            echo [成功]   svn_post_commit_hook.py 部署成功
            
            REM 验证文件
            if exist "!TARGET_BAT!" if exist "!TARGET_PY!" (
                echo [成功]   仓库 !REPO_NAME! 的Hook部署完成
                set /a SUCCESS+=1
            ) else (
                echo [错误]   文件部署后验证失败
                set /a FAILED+=1
            )
        )
    )
)
exit /b

:end_processing
REM 输出统计信息
echo.
echo ========================================
echo 部署完成统计
echo ========================================
echo [信息] 总仓库数: %TOTAL%
echo [成功] 成功: %SUCCESS%
echo [警告] 跳过: %SKIPPED%
if %FAILED% gtr 0 (
    echo [错误] 失败: %FAILED%
)
echo.

REM 提示后续操作
if %SUCCESS% gtr 0 (
    echo ========================================
    echo 后续操作提示
    echo ========================================
    echo [信息] 1. 检查每个仓库的 svn_post_commit_hook.py 配置：
    echo [信息]    - REVIEW_API_URL: AI代码审查系统API地址
    echo [信息]    - REPO_URL: SVN仓库URL（需要根据实际仓库修改）
    echo.
    echo [信息] 2. 可以通过环境变量配置（推荐）：
    echo [信息]    - SVN_REVIEW_API_URL: 审查系统API地址
    echo [信息]    - SVN_REPO_URL: 仓库URL（或让脚本自动生成）
    echo.
    echo [信息] 3. 测试Hook是否正常工作：
    echo [信息]    在任意仓库中提交代码，检查审查系统是否收到webhook
    echo.
)

pause

