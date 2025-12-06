# SVN Post-Commit Hook 脚本使用说明

## 文件说明

- `svn_post_commit_hook.py` - Python版本的post-commit hook脚本（推荐，跨平台）
- `svn_post_commit_hook.bat` - Windows版本的包装脚本（用于调用Python脚本）

## 快速开始

### Linux/Unix 系统

1. **复制脚本到SVN仓库的hooks目录**
   ```bash
   cp svn_post_commit_hook.py /path/to/svn/repo/hooks/post-commit
   ```

2. **修改配置**
   编辑脚本，修改以下配置项：
   ```python
   REVIEW_API_URL = "http://your-review-server:5001/review/webhook"
   REPO_URL = "svn://your-svn-server.com/repo"
   ```

3. **添加执行权限**
   ```bash
   chmod +x /path/to/svn/repo/hooks/post-commit
   ```

4. **测试脚本**
   ```bash
   /path/to/svn/repo/hooks/post-commit /path/to/svn/repo 123
   ```

### Windows 系统

1. **复制脚本到SVN仓库的hooks目录**
   ```batch
   copy svn_post_commit_hook.py C:\path\to\svn\repo\hooks\
   copy svn_post_commit_hook.bat C:\path\to\svn\repo\hooks\post-commit.bat
   ```

2. **修改配置**
   编辑 `svn_post_commit_hook.py`，修改配置项（同上）

3. **修改批处理脚本（如果需要）**
   如果Python不在系统PATH中，编辑 `post-commit.bat`：
   ```batch
   set PYTHON_PATH=C:\Python39\python.exe
   set SCRIPT_PATH=C:\path\to\svn\repo\hooks\svn_post_commit_hook.py
   ```

## 配置说明

### 必需配置

- **REVIEW_API_URL**: AI代码审查系统的API地址
  ```python
  REVIEW_API_URL = "http://192.168.1.100:5001/review/webhook"
  ```

- **REPO_URL**: SVN仓库的URL地址
  ```python
  REPO_URL = "svn://svn.example.com/repo"
  # 或使用http/https
  REPO_URL = "http://svn.example.com/svn/repo"
  ```

### 可选配置

- **SVN_USERNAME**: SVN认证用户名（如果仓库需要认证）
  ```python
  SVN_USERNAME = "username"
  ```

- **SVN_PASSWORD**: SVN认证密码（如果仓库需要认证）
  ```python
  SVN_PASSWORD = "password"
  ```

- **MAX_RETRIES**: 失败重试次数（默认3次）
  ```python
  MAX_RETRIES = 5
  ```

- **RETRY_DELAY**: 重试延迟秒数（默认5秒）
  ```python
  RETRY_DELAY = 10
  ```

- **LOG_FILE**: 日志文件路径（可选，用于调试）
  ```python
  LOG_FILE = "/var/log/svn/post-commit.log"
  # Windows示例
  LOG_FILE = "C:\\logs\\svn\\post-commit.log"
  ```

## 从环境变量读取配置

脚本支持从环境变量读取配置，修改脚本中的配置部分：

```python
import os

# 从环境变量读取配置
REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', 'http://your-review-server:5001/review/webhook')
REPO_URL = os.getenv('SVN_REPO_URL', 'svn://your-svn-server.com/repo')
SVN_USERNAME = os.getenv('SVN_USERNAME')
SVN_PASSWORD = os.getenv('SVN_PASSWORD')
```

然后在系统环境变量或SVN服务器的启动脚本中设置：
```bash
export SVN_REVIEW_API_URL="http://your-review-server:5001/review/webhook"
export SVN_REPO_URL="svn://your-svn-server.com/repo"
export SVN_USERNAME="username"
export SVN_PASSWORD="password"
```

## 功能特性

1. **自动重试机制**：网络失败时自动重试，最多重试3次（可配置）
2. **错误处理**：完善的错误处理，不会阻塞SVN提交
3. **日志记录**：支持日志记录，便于调试和问题排查
4. **时间格式转换**：自动转换SVN时间格式为ISO格式
5. **UTF-8支持**：正确处理中文等非ASCII字符

## 测试

### 手动测试

```bash
# Linux/Unix
/path/to/svn/repo/hooks/post-commit /path/to/svn/repo 123

# Windows
C:\path\to\svn\repo\hooks\post-commit.bat C:\path\to\svn\repo 123
```

### 提交测试

1. 在SVN仓库中创建一个测试文件
2. 提交代码：
   ```bash
   svn commit -m "test commit for webhook" test.py
   ```
3. 检查AI代码审查系统是否收到webhook请求
4. 查看日志（如果配置了LOG_FILE）

## 故障排查

### 1. 脚本没有执行

**检查项：**
- 文件权限是否正确（Linux/Unix需要执行权限）
- 文件路径是否正确
- 脚本第一行shebang是否正确：`#!/usr/bin/env python3`

**解决方法：**
```bash
chmod +x /path/to/svn/repo/hooks/post-commit
```

### 2. Python未找到

**错误信息：**
```
/usr/bin/env: python3: No such file or directory
```

**解决方法：**
- 确保系统已安装Python 3
- 检查Python路径：`which python3`
- 修改脚本第一行：`#!/usr/bin/python3`（使用绝对路径）

### 3. svnlook命令未找到

**错误信息：**
```
svnlook command not found
```

**解决方法：**
- 确保SVN服务器已安装svnlook工具
- 使用绝对路径：`/usr/bin/svnlook`
- 检查PATH环境变量

### 4. Webhook请求失败

**检查项：**
- 网络连接是否正常
- API地址是否正确
- 防火墙是否阻止
- 审查系统是否正常运行

**测试网络连接：**
```bash
curl http://your-review-server:5001/review/webhook
```

### 5. 查看日志

如果配置了LOG_FILE，查看日志文件：
```bash
tail -f /var/log/svn/post-commit.log
```

如果没有配置LOG_FILE，查看系统日志或SVN服务器日志。

## 安全建议

1. **保护密码**：不要将密码硬编码在脚本中，使用环境变量或配置文件
2. **文件权限**：确保脚本文件权限设置正确，避免其他用户读取密码
3. **HTTPS**：如果可能，使用HTTPS协议连接审查系统
4. **防火墙**：限制审查系统的访问，只允许SVN服务器访问

## 示例配置

### 示例1：基本配置

```python
REVIEW_API_URL = "http://192.168.1.100:5001/review/webhook"
REPO_URL = "svn://svn.example.com/repo"
SVN_USERNAME = None
SVN_PASSWORD = None
```

### 示例2：带认证的配置

```python
REVIEW_API_URL = "http://192.168.1.100:5001/review/webhook"
REPO_URL = "svn://svn.example.com/repo"
SVN_USERNAME = "svnuser"
SVN_PASSWORD = "svnpass"
LOG_FILE = "/var/log/svn/post-commit.log"
```

### 示例3：使用环境变量

```python
import os

REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', 'http://localhost:5001/review/webhook')
REPO_URL = os.getenv('SVN_REPO_URL', 'svn://localhost/repo')
SVN_USERNAME = os.getenv('SVN_USERNAME')
SVN_PASSWORD = os.getenv('SVN_PASSWORD')
LOG_FILE = os.getenv('SVN_LOG_FILE')
```

## 支持

如有问题，请查看：
- [SVN Webhook 接入说明](svn_webhook_setup.md)
- [常见问题](faq.md)
- 项目GitHub Issues

