# SVN Webhook 接入说明

本文档说明如何配置SVN的post-commit hook，将SVN提交事件发送到AI代码审查系统。

## 快速开始

1. **配置环境变量**：在`conf/.env`中设置`PUSH_REVIEW_ENABLED=1`
2. **创建hook脚本**：在SVN仓库的`hooks`目录下创建`post-commit`脚本
3. **测试提交**：提交代码验证webhook是否正常工作

详细步骤请参考下方各章节。

## 目录

- [前置要求](#前置要求)
- [环境变量配置](#环境变量配置)
- [SVN Post-Commit Hook 配置](#svn-post-commit-hook-配置)
- [Webhook 数据格式](#webhook-数据格式)
- [验证配置](#验证配置)
- [常见问题](#常见问题)

## 前置要求

1. **SVN服务器访问权限**：需要能够修改SVN仓库的hooks目录
2. **Python环境**：SVN服务器需要安装Python（用于执行hook脚本）
3. **网络访问**：SVN服务器需要能够访问AI代码审查系统的API地址
4. **SVN客户端**：确保系统PATH中包含`svn`命令

## 配置方式选择

根据你的需求，可以选择以下配置方式：

- **单仓库配置**：为每个仓库单独配置hook（适合不同仓库需要不同配置的场景）
- **服务器级别配置**：使用统一脚本监听所有仓库（推荐，集中管理）

**如果需要在SVN服务器级别配置webhook监听所有仓库，请参考：**
👉 [SVN服务器级别Webhook配置说明](svn_server_webhook_config.md)

## 环境变量配置

在AI代码审查系统的配置文件中（`conf/.env`），添加以下SVN相关配置：

```bash
# SVN仓库URL（可选，如果webhook中已包含则不需要）
SVN_REPO_URL=svn://your-svn-server.com/repo

# SVN认证信息（如果仓库需要认证）
SVN_USERNAME=your_username
SVN_PASSWORD=your_password

# 启用Push审查（SVN提交审查使用此配置）
PUSH_REVIEW_ENABLED=1
```

**注意**：
- `SVN_REPO_URL`：如果webhook数据中已包含`repository_url`字段，可以不配置此项
- `SVN_USERNAME`和`SVN_PASSWORD`：仅在SVN仓库需要认证时配置
- `PUSH_REVIEW_ENABLED`：必须设置为`1`才能启用SVN提交审查

## SVN Post-Commit Hook 配置

### 1. 找到SVN仓库的hooks目录

SVN仓库的hooks目录通常位于：
```
/path/to/svn/repo/hooks/
```

### 2. 创建post-commit hook脚本

在hooks目录下创建或编辑`post-commit`文件（Linux/Unix）或`post-commit.bat`（Windows）：

#### Linux/Unix 版本

创建文件：`/path/to/svn/repo/hooks/post-commit`

```bash
#!/bin/bash

# SVN仓库路径
REPOS="$1"
REV="$2"

# AI代码审查系统API地址
REVIEW_API_URL="http://your-review-server:5001/review/webhook"

# 获取提交信息
AUTHOR=$(svnlook author -r "$REV" "$REPOS")
MESSAGE=$(svnlook log -r "$REV" "$REPOS")
TIMESTAMP=$(svnlook date -r "$REV" "$REPOS")

# 获取仓库URL（如果配置了SVN_REPO_URL，可以使用该值）
# 否则需要从REPOS路径或配置中获取
REPO_URL="svn://your-svn-server.com/repo"

# 构建JSON数据
JSON_DATA=$(cat <<EOF
{
  "repository_url": "$REPO_URL",
  "revision": "$REV",
  "author": "$AUTHOR",
  "message": "$MESSAGE",
  "timestamp": "$TIMESTAMP"
}
EOF
)

# 发送webhook请求
curl -X POST "$REVIEW_API_URL" \
  -H "Content-Type: application/json" \
  -H "X-SVN-Event: commit" \
  -d "$JSON_DATA"

exit 0
```

#### Windows 版本

创建文件：`C:\path\to\svn\repo\hooks\post-commit.bat`

```batch
@echo off
setlocal

set REPOS=%1
set REV=%2

set REVIEW_API_URL=http://your-review-server:5001/review/webhook

REM 获取提交信息（需要安装svnlook工具）
for /f "tokens=*" %%a in ('svnlook author -r %REV% %REPOS%') do set AUTHOR=%%a
for /f "tokens=*" %%a in ('svnlook log -r %REV% %REPOS%') do set MESSAGE=%%a
for /f "tokens=*" %%a in ('svnlook date -r %REV% %REPOS%') do set TIMESTAMP=%%a

set REPO_URL=svn://your-svn-server.com/repo

REM 构建JSON数据（使用PowerShell发送请求）
powershell -Command "$body = @{repository_url='%REPO_URL%'; revision='%REV%'; author='%AUTHOR%'; message='%MESSAGE%'; timestamp='%TIMESTAMP%'} | ConvertTo-Json; Invoke-RestMethod -Uri '%REVIEW_API_URL%' -Method Post -Body $body -ContentType 'application/json' -Headers @{'X-SVN-Event'='commit'}"

exit 0
```

#### Python 版本（推荐，跨平台）

创建文件：`/path/to/svn/repo/hooks/post-commit`（Linux）或`post-commit.bat`（Windows）

**Linux版本：**
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import json
import urllib.request
import urllib.parse
from datetime import datetime

# SVN仓库路径和版本号
REPOS = sys.argv[1]
REV = sys.argv[2]

# AI代码审查系统API地址
REVIEW_API_URL = "http://your-review-server:5001/review/webhook"

# 获取提交信息
def get_svn_info(repos, rev):
    """获取SVN提交信息"""
    author = subprocess.check_output(
        ['svnlook', 'author', '-r', rev, repos],
        universal_newlines=True
    ).strip()
    
    message = subprocess.check_output(
        ['svnlook', 'log', '-r', rev, repos],
        universal_newlines=True
    ).strip()
    
    timestamp = subprocess.check_output(
        ['svnlook', 'date', '-r', rev, repos],
        universal_newlines=True
    ).strip()
    
    return author, message, timestamp

# 获取仓库URL（可以从配置文件或环境变量读取）
REPO_URL = "svn://your-svn-server.com/repo"

try:
    # 获取提交信息
    author, message, timestamp = get_svn_info(REPOS, REV)
    
    # 构建webhook数据
    webhook_data = {
        "repository_url": REPO_URL,
        "revision": REV,
        "author": author,
        "message": message,
        "timestamp": timestamp
    }
    
    # 发送webhook请求
    data = json.dumps(webhook_data).encode('utf-8')
    req = urllib.request.Request(
        REVIEW_API_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'X-SVN-Event': 'commit'
        }
    )
    
    response = urllib.request.urlopen(req)
    print(f"Webhook sent successfully: {response.status}")
    
except Exception as e:
    print(f"Error sending webhook: {e}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
```

**Windows版本（post-commit.bat）：**
```batch
@echo off
python C:\path\to\svn\repo\hooks\post-commit.py %1 %2
```

### 3. 设置执行权限（Linux/Unix）

```bash
chmod +x /path/to/svn/repo/hooks/post-commit
```

### 4. 配置说明

- **REVIEW_API_URL**：替换为你的AI代码审查系统的实际API地址
- **REPO_URL**：替换为你的SVN仓库的实际URL
- 确保SVN服务器可以访问AI代码审查系统的API地址
- 如果SVN服务器需要认证，可以在webhook数据中添加`svn_username`和`svn_password`字段

## Webhook 数据格式

SVN post-commit hook需要发送以下格式的JSON数据：

```json
{
  "repository_url": "svn://your-svn-server.com/repo",
  "revision": "123",
  "author": "username",
  "message": "commit message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repository_url` | string | 是 | SVN仓库的URL地址 |
| `revision` | string | 是 | 提交的版本号 |
| `author` | string | 否 | 提交者用户名（建议填写） |
| `message` | string | 否 | 提交消息（建议填写） |
| `timestamp` | string | 否 | 提交时间戳（建议填写） |
| `svn_username` | string | 否 | SVN认证用户名（如果需要） |
| `svn_password` | string | 否 | SVN认证密码（如果需要） |

### HTTP Headers

建议在请求头中添加：
- `Content-Type: application/json`
- `X-SVN-Event: commit`（可选，用于标识SVN事件）

## 验证配置

### 1. 测试hook脚本

手动执行hook脚本测试：

```bash
# Linux/Unix
/path/to/svn/repo/hooks/post-commit /path/to/svn/repo 123

# Windows
C:\path\to\svn\repo\hooks\post-commit.bat C:\path\to\svn\repo 123
```

### 2. 提交测试代码

在SVN仓库中提交一个测试文件：

```bash
svn commit -m "test commit for webhook" test.py
```

### 3. 检查日志

查看AI代码审查系统的日志，确认收到webhook请求：

```bash
# 查看应用日志
tail -f log/app.log
```

应该能看到类似以下日志：
```
INFO: Received SVN webhook event
INFO: SVN Commit event received
```

### 4. 检查审查结果

- 如果配置了IM通知（钉钉/企业微信/飞书），应该能收到审查结果通知
- 访问Dashboard（http://your-server:5002）查看审查记录

## 常见问题

### 1. Hook脚本没有执行

**可能原因**：
- Hook脚本没有执行权限（Linux/Unix）
- Hook脚本路径错误
- Hook脚本语法错误

**解决方案**：
- 检查文件权限：`ls -l /path/to/svn/repo/hooks/post-commit`
- 添加执行权限：`chmod +x /path/to/svn/repo/hooks/post-commit`
- 检查脚本语法，确保第一行是`#!/bin/bash`或`#!/usr/bin/env python3`

### 2. Webhook请求失败

**可能原因**：
- 网络连接问题
- API地址错误
- 防火墙阻止

**解决方案**：
- 测试网络连接：`curl http://your-review-server:5001`
- 检查API地址是否正确
- 检查防火墙规则，确保SVN服务器可以访问审查系统

### 3. 无法获取SVN提交信息

**可能原因**：
- `svnlook`命令不可用
- 权限不足

**解决方案**：
- 确保SVN服务器安装了`svnlook`工具
- 检查执行hook的用户是否有权限访问SVN仓库
- 使用绝对路径调用`svnlook`：`/usr/bin/svnlook`

### 4. 代码审查没有触发

**可能原因**：
- `PUSH_REVIEW_ENABLED`未设置为`1`
- 提交的文件不在`SUPPORTED_EXTENSIONS`列表中
- Webhook数据格式不正确

**解决方案**：
- 检查`conf/.env`中的`PUSH_REVIEW_ENABLED=1`
- 检查`SUPPORTED_EXTENSIONS`配置，确保包含需要审查的文件类型
- 检查webhook数据格式，确保包含`revision`字段

### 5. SVN认证失败

**可能原因**：
- 用户名或密码错误
- SVN仓库需要认证但未配置

**解决方案**：
- 在webhook数据中添加`svn_username`和`svn_password`字段
- 或在环境变量中配置`SVN_USERNAME`和`SVN_PASSWORD`
- 确保认证信息正确

## 高级配置

### 使用配置文件

可以将配置信息存储在单独的配置文件中，避免硬编码：

```python
# config.json
{
  "review_api_url": "http://your-review-server:5001/review/webhook",
  "repo_url": "svn://your-svn-server.com/repo",
  "svn_username": "username",
  "svn_password": "password"
}
```

### 错误处理和重试

可以在hook脚本中添加错误处理和重试机制：

```python
import time

max_retries = 3
retry_delay = 5

for attempt in range(max_retries):
    try:
        # 发送webhook请求
        response = urllib.request.urlopen(req)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
        else:
            # 记录错误或发送告警
            print(f"Failed after {max_retries} attempts: {e}")
```

## 参考资源

- [SVN Hook脚本文档](https://svnbook.red-bean.com/en/1.7/svn.ref.reposhooks.post-commit.html)
- [SVN Look命令文档](https://svnbook.red-bean.com/en/1.7/svn.ref.svnlook.html)
- 项目GitHub地址：https://github.com/sunmh207/AI-Codereview-Gitlab

