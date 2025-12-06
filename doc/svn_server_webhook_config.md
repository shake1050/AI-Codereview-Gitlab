# SVN服务器级别Webhook配置说明

本文档说明如何在SVN服务器级别配置webhook，实现对所有仓库提交的统一监听。

## 当前功能匹配情况

✅ **当前功能已完全支持SVN服务器级别的webhook监听**

当前实现通过以下方式支持：
1. **API自动识别SVN webhook**：通过header (`X-SVN-Event`) 或请求体中的 `revision` 字段自动识别
2. **支持多仓库**：每个仓库的post-commit hook都会发送webhook到同一个API端点
3. **统一处理**：所有SVN提交都会通过 `/review/webhook` 端点统一处理

## 配置方案

### 方案一：为每个仓库单独配置（推荐，灵活）

**适用场景**：不同仓库需要不同的配置（如不同的认证信息）

**配置步骤**：

1. **为每个仓库创建post-commit hook**
   ```bash
   # 仓库1
   cp doc/svn_post_commit_hook.py /path/to/svn/repo1/hooks/post-commit
   chmod +x /path/to/svn/repo1/hooks/post-commit
   
   # 仓库2
   cp doc/svn_post_commit_hook.py /path/to/svn/repo2/hooks/post-commit
   chmod +x /path/to/svn/repo2/hooks/post-commit
   ```

2. **修改每个仓库的hook配置**
   编辑每个仓库的hook脚本，设置对应的 `REPO_URL`：
   ```python
   # 仓库1的配置
   REPO_URL = "svn://svn-server.com/repo1"
   
   # 仓库2的配置
   REPO_URL = "svn://svn-server.com/repo2"
   ```

**优点**：
- 每个仓库可以独立配置
- 支持不同的认证信息
- 配置灵活

**缺点**：
- 需要为每个仓库单独配置
- 维护成本较高

### 方案二：统一脚本 + 符号链接（推荐，集中管理）

**适用场景**：所有仓库使用相同的配置

**配置步骤**：

1. **创建统一的hook脚本**
   ```bash
   # 创建统一的hooks目录
   mkdir -p /opt/svn/hooks
   
   # 复制脚本到统一位置
   cp doc/svn_post_commit_hook.py /opt/svn/hooks/post-commit-unified.py
   chmod +x /opt/svn/hooks/post-commit-unified.py
   ```

2. **配置统一脚本**
   编辑 `/opt/svn/hooks/post-commit-unified.py`，使用环境变量或从参数动态获取仓库URL：
   ```python
   import os
   import sys
   
   # 从环境变量或配置文件中读取
   REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', 'http://your-review-server:5001/review/webhook')
   
   # 从SVN仓库路径动态生成URL
   REPOS = sys.argv[1]
   # 假设仓库路径为 /var/svn/repos/repo1，URL为 svn://server/repo1
   repo_name = os.path.basename(REPOS)
   REPO_URL = f"svn://your-svn-server.com/{repo_name}"
   ```

3. **为每个仓库创建符号链接**
   ```bash
   # 为仓库1创建符号链接
   ln -s /opt/svn/hooks/post-commit-unified.py /path/to/svn/repo1/hooks/post-commit
   
   # 为仓库2创建符号链接
   ln -s /opt/svn/hooks/post-commit-unified.py /path/to/svn/repo2/hooks/post-commit
   
   # 批量创建（如果所有仓库在同一目录下）
   for repo in /var/svn/repos/*; do
       if [ -d "$repo" ]; then
           ln -sf /opt/svn/hooks/post-commit-unified.py "$repo/hooks/post-commit"
       fi
   done
   ```

**优点**：
- 集中管理，只需维护一个脚本
- 配置更新方便
- 减少重复代码

**缺点**：
- 所有仓库使用相同配置
- 需要确保仓库URL生成逻辑正确

### 方案三：使用配置文件（最灵活）

**适用场景**：需要集中管理但支持不同配置

**配置步骤**：

1. **创建统一的hook脚本（支持配置文件）**
   
   创建 `/opt/svn/hooks/post-commit-unified.py`：
   ```python
   #!/usr/bin/env python3
   # -*- coding: utf-8 -*-
   
   import sys
   import os
   import json
   import subprocess
   import urllib.request
   import logging
   from datetime import datetime
   
   # 配置文件路径
   CONFIG_FILE = '/opt/svn/hooks/repo_config.json'
   
   # 默认配置
   DEFAULT_CONFIG = {
       'review_api_url': 'http://your-review-server:5001/review/webhook',
       'repos': {}
   }
   
   def load_config():
       """加载配置文件"""
       if os.path.exists(CONFIG_FILE):
           with open(CONFIG_FILE, 'r') as f:
               return json.load(f)
       return DEFAULT_CONFIG
   
   def get_repo_config(repos_path, config):
       """获取仓库配置"""
       repo_name = os.path.basename(repos_path)
       
       # 优先使用配置文件中的配置
       if repo_name in config.get('repos', {}):
           repo_config = config['repos'][repo_name]
           return {
               'repo_url': repo_config.get('url', f'svn://server/{repo_name}'),
               'username': repo_config.get('username'),
               'password': repo_config.get('password')
           }
       
       # 使用默认配置
       return {
           'repo_url': f'svn://server/{repo_name}',
           'username': None,
           'password': None
       }
   
   # ... (其余代码与标准脚本相同，但使用动态配置)
   ```

2. **创建配置文件**
   
   创建 `/opt/svn/hooks/repo_config.json`：
   ```json
   {
     "review_api_url": "http://your-review-server:5001/review/webhook",
     "repos": {
       "repo1": {
         "url": "svn://svn-server.com/repo1",
         "username": "user1",
         "password": "pass1"
       },
       "repo2": {
         "url": "svn://svn-server.com/repo2",
         "username": "user2",
         "password": "pass2"
       },
       "*": {
         "url": "svn://svn-server.com/{repo_name}",
         "username": null,
         "password": null
       }
     }
   }
   ```

3. **为每个仓库创建符号链接**
   ```bash
   ln -s /opt/svn/hooks/post-commit-unified.py /path/to/svn/repo1/hooks/post-commit
   ln -s /opt/svn/hooks/post-commit-unified.py /path/to/svn/repo2/hooks/post-commit
   ```

**优点**：
- 集中管理
- 支持不同仓库的不同配置
- 配置更新无需修改代码

**缺点**：
- 需要维护配置文件
- 脚本逻辑稍复杂

## 自动化配置脚本

创建一个自动化配置脚本，为新仓库自动配置hook：

### 创建配置脚本

创建 `/opt/svn/hooks/setup_hook.sh`：

```bash
#!/bin/bash
# SVN Hook自动配置脚本

HOOK_SCRIPT="/opt/svn/hooks/post-commit-unified.py"
SVN_REPOS_BASE="/var/svn/repos"

# 检查hook脚本是否存在
if [ ! -f "$HOOK_SCRIPT" ]; then
    echo "Error: Hook script not found at $HOOK_SCRIPT"
    exit 1
fi

# 为所有仓库配置hook
for repo in "$SVN_REPOS_BASE"/*; do
    if [ -d "$repo" ] && [ -d "$repo/hooks" ]; then
        repo_name=$(basename "$repo")
        hook_path="$repo/hooks/post-commit"
        
        # 如果hook不存在或不是符号链接，创建它
        if [ ! -e "$hook_path" ]; then
            ln -s "$HOOK_SCRIPT" "$hook_path"
            echo "Created hook for repository: $repo_name"
        elif [ ! -L "$hook_path" ]; then
            echo "Warning: $hook_path exists but is not a symlink. Skipping $repo_name"
        else
            echo "Hook already exists for repository: $repo_name"
        fi
    fi
    done

echo "Hook setup completed!"
```

### 使用配置脚本

```bash
# 添加执行权限
chmod +x /opt/svn/hooks/setup_hook.sh

# 运行配置脚本
/opt/svn/hooks/setup_hook.sh

# 或者添加到cron，定期检查新仓库
# 0 2 * * * /opt/svn/hooks/setup_hook.sh
```

## 验证配置

### 1. 检查hook是否配置

```bash
# 检查所有仓库的hook
for repo in /var/svn/repos/*; do
    if [ -d "$repo/hooks" ]; then
        repo_name=$(basename "$repo")
        if [ -L "$repo/hooks/post-commit" ]; then
            echo "$repo_name: Hook configured (symlink)"
        elif [ -f "$repo/hooks/post-commit" ]; then
            echo "$repo_name: Hook configured (file)"
        else
            echo "$repo_name: Hook NOT configured"
        fi
    fi
done
```

### 2. 测试单个仓库

```bash
# 测试仓库1的hook
/path/to/svn/repo1/hooks/post-commit /path/to/svn/repo1 123
```

### 3. 提交测试

```bash
# 在任意仓库中提交测试代码
svn commit -m "test webhook" test.py
```

### 4. 检查审查系统日志

```bash
# 查看审查系统是否收到webhook
tail -f /path/to/review-system/log/app.log | grep SVN
```

## 环境变量配置

在SVN服务器上设置环境变量，供所有hook使用：

### Linux系统

编辑 `/etc/environment` 或创建 `/etc/profile.d/svn-hooks.sh`：

```bash
# SVN Webhook配置
export SVN_REVIEW_API_URL="http://your-review-server:5001/review/webhook"
export SVN_USERNAME="svn_user"
export SVN_PASSWORD="svn_pass"
```

### 在hook脚本中使用环境变量

修改hook脚本，优先使用环境变量：

```python
import os

# 从环境变量读取配置
REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', 'http://your-review-server:5001/review/webhook')
SVN_USERNAME = os.getenv('SVN_USERNAME')
SVN_PASSWORD = os.getenv('SVN_PASSWORD')

# 从仓库路径生成URL
REPOS = sys.argv[1]
repo_name = os.path.basename(REPOS)
REPO_URL = os.getenv('SVN_REPO_URL_PREFIX', 'svn://server') + '/' + repo_name
```

## 监控和维护

### 1. 监控hook执行

创建监控脚本 `/opt/svn/hooks/monitor_hooks.sh`：

```bash
#!/bin/bash
# 监控所有仓库的hook配置

LOG_FILE="/var/log/svn/hook_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Checking SVN hooks..." >> "$LOG_FILE"

for repo in /var/svn/repos/*; do
    if [ -d "$repo" ]; then
        repo_name=$(basename "$repo")
        hook_path="$repo/hooks/post-commit"
        
        if [ ! -e "$hook_path" ]; then
            echo "[$DATE] WARNING: $repo_name has no post-commit hook" >> "$LOG_FILE"
        elif [ ! -x "$hook_path" ]; then
            echo "[$DATE] WARNING: $repo_name hook is not executable" >> "$LOG_FILE"
        fi
    fi
done

echo "[$DATE] Hook check completed" >> "$LOG_FILE"
```

### 2. 日志轮转

配置logrotate，避免日志文件过大：

创建 `/etc/logrotate.d/svn-hooks`：

```
/var/log/svn/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 svn svn
}
```

## 常见问题

### Q1: 如何为新创建的仓库自动配置hook？

**A**: 使用方案二的自动化配置脚本，或创建SVN仓库时自动创建hook的脚本。

### Q2: 如何为特定仓库禁用webhook？

**A**: 
- 方案一：删除或重命名该仓库的hook文件
- 方案二/三：在配置文件中添加排除列表，或在hook脚本中添加判断逻辑

### Q3: 如何更新所有仓库的hook配置？

**A**: 
- 方案一：需要逐个更新
- 方案二/三：只需更新统一脚本或配置文件，所有仓库自动生效

### Q4: 如何查看哪些仓库已配置hook？

**A**: 使用验证配置部分的检查脚本。

## 最佳实践

1. **使用方案二（统一脚本+符号链接）**：适合大多数场景，维护成本低
2. **使用环境变量**：敏感信息（如密码）通过环境变量配置，不要硬编码
3. **定期检查**：使用监控脚本定期检查hook配置
4. **日志记录**：启用hook日志，便于问题排查
5. **测试验证**：新配置后务必测试验证

## 参考

- [SVN Webhook 接入说明](svn_webhook_setup.md)
- [SVN Post-Commit Hook 脚本](svn_post_commit_hook.py)
- [SVN Hook脚本使用说明](svn_post_commit_hook_README.md)

