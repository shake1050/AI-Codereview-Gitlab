# VisualSVN Server Hook 配置说明

本文档说明如何在 VisualSVN Server 上配置 post-commit hook，实现代码审查功能。

## VisualSVN Server Hook 位置

VisualSVN Server 的 hook 脚本位于：
```
C:\Repositories\<RepositoryName>\hooks\post-commit.bat
```

每个仓库都有独立的 hooks 目录。

## 快速配置步骤

### 1. 准备文件

将以下文件复制到 VisualSVN Server 的 hooks 目录：

```batch
REM 假设仓库名为 TestSVN
copy svn_post_commit_hook.py C:\Repositories\TestSVN\hooks\
copy svn_post_commit_hook.bat C:\Repositories\TestSVN\hooks\post-commit.bat
```

### 2. 配置 Python 脚本

编辑 `svn_post_commit_hook.py`，修改以下配置：

```python
# AI代码审查系统API地址
REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', "http://10.10.9.12:5001/review/webhook")

# SVN仓库URL（从VisualSVN Server获取）
REPO_URL = os.getenv('SVN_REPO_URL', "https://10.10.9.12/svn/TestSVN/")
```

### 3. 配置批处理脚本（可选）

如果 Python 不在系统 PATH 中，编辑 `post-commit.bat`：

```batch
REM 修改Python路径
set PYTHON_PATH=C:\Python39\python.exe
```

### 4. 验证配置

#### 方法1：通过 VisualSVN Server Manager

1. 打开 VisualSVN Server Manager
2. 右键点击仓库 → Properties → Hooks
3. 查看 post-commit hook 是否已配置

#### 方法2：手动测试

```batch
REM 使用实际的仓库路径和版本号测试
C:\Repositories\TestSVN\hooks\post-commit.bat "C:\Repositories\TestSVN" 123
```

## 配置多个仓库

### 方法1：逐个配置（推荐，灵活）

为每个仓库单独配置，可以设置不同的仓库URL。

### 方法2：使用统一脚本（集中管理）

1. **创建统一脚本目录**
   ```batch
   mkdir C:\SVN_Hooks
   copy svn_post_commit_hook.py C:\SVN_Hooks\
   ```

2. **修改统一脚本支持多仓库**
   编辑 `svn_post_commit_hook.py`，添加自动检测仓库URL的逻辑：
   ```python
   import os
   
   # 从仓库路径自动生成URL
   REPOS = sys.argv[1]
   repo_name = os.path.basename(REPOS)
   REPO_URL = f"https://10.10.9.12/svn/{repo_name}/"
   ```

3. **为每个仓库创建批处理脚本**
   在每个仓库的 hooks 目录创建 `post-commit.bat`：
   ```batch
   @echo off
   C:\Python39\python.exe C:\SVN_Hooks\svn_post_commit_hook.py "%~1" "%~2"
   exit /b 0
   ```

## 环境变量配置

### 系统级环境变量

在 Windows 系统环境变量中设置：

1. 打开"系统属性" → "高级" → "环境变量"
2. 添加以下变量：
   ```
   SVN_REVIEW_API_URL=http://10.10.9.12:5001/review/webhook
   SVN_REPO_URL=https://10.10.9.12/svn/TestSVN/
   SVN_USERNAME=svn_user
   SVN_PASSWORD=svn_pass
   ```

### VisualSVN Server 服务环境变量

VisualSVN Server 作为 Windows 服务运行，需要为服务设置环境变量：

1. 打开"服务"管理器（services.msc）
2. 找到 "VisualSVN Server" 服务
3. 右键 → 属性 → 登录
4. 在"环境变量"中添加上述变量

或者使用 PowerShell：

```powershell
# 为VisualSVN Server服务设置环境变量
$service = Get-WmiObject Win32_Service -Filter "Name='VisualSVN Server'"
$service.EnvironmentVariables += "SVN_REVIEW_API_URL=http://10.10.9.12:5001/review/webhook"
$service.Change($null, $null, $null, $null, $null, $null, $null, $null, $null, $null, $null)
```

## 常见问题

### Q1: Python 未找到

**错误信息**：
```
Error: Python not found. Please install Python 3.6+ or set PYTHON_PATH correctly.
```

**解决方案**：
1. 安装 Python 3.6 或更高版本
2. 将 Python 添加到系统 PATH
3. 或在 `post-commit.bat` 中设置完整路径：
   ```batch
   set PYTHON_PATH=C:\Python39\python.exe
   ```

### Q2: 脚本文件未找到

**错误信息**：
```
Error: Python script not found at: C:\Repositories\TestSVN\hooks\svn_post_commit_hook.py
```

**解决方案**：
确保 `svn_post_commit_hook.py` 文件在 hooks 目录中。

### Q3: Hook 未执行

**可能原因**：
1. 文件权限问题
2. VisualSVN Server 服务账户没有执行权限
3. Hook 脚本有错误

**解决方案**：
1. 检查文件权限，确保 VisualSVN Server 服务账户有读取和执行权限
2. 查看 VisualSVN Server 日志：`C:\ProgramData\VisualSVN Server\Log\`
3. 手动测试 hook 脚本

### Q4: 路径中包含空格

**解决方案**：
脚本已经使用引号包裹参数，可以正确处理包含空格的路径。

### Q5: 查看执行日志

**方法1：Python脚本日志**
如果配置了 `LOG_FILE`，查看日志文件。

**方法2：VisualSVN Server日志**
查看：`C:\ProgramData\VisualSVN Server\Log\vsvnserver.log`

**方法3：Windows事件查看器**
查看 Windows 事件查看器中的应用程序日志。

## 测试验证

### 1. 手动测试 Hook

```batch
REM 使用实际的仓库路径和版本号
C:\Repositories\TestSVN\hooks\post-commit.bat "C:\Repositories\TestSVN" 123
```

### 2. 提交测试

在仓库中提交测试代码：
```batch
svn commit -m "test webhook" test.py
```

### 3. 检查审查系统

查看 AI 代码审查系统是否收到 webhook 请求：
- 查看审查系统日志
- 检查 Dashboard
- 查看 IM 通知（如果配置了）

## 权限配置

确保 VisualSVN Server 服务账户有权限：
1. 读取和执行 hook 脚本
2. 读取 Python 脚本
3. 写入日志文件（如果配置了）
4. 访问网络（发送 webhook 请求）

## 最佳实践

1. **使用环境变量**：敏感信息（如密码）通过环境变量配置
2. **统一脚本**：多个仓库使用统一的脚本，便于维护
3. **日志记录**：启用日志记录，便于问题排查
4. **测试验证**：配置后务必测试验证
5. **定期检查**：定期检查 hook 是否正常工作

## 参考

- [SVN Post-Commit Hook 脚本使用说明](svn_post_commit_hook_README.md)
- [SVN Webhook 接入说明](svn_webhook_setup.md)
- [VisualSVN Server 官方文档](https://www.visualsvn.com/support/topic/00018/)

