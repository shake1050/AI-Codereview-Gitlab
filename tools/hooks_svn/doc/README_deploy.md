# SVN Hook 一键部署脚本使用说明

本目录包含用于为 VisualSVN Server 的所有仓库一键部署 post-commit hook 的自动化脚本。

## 文件说明

- `deploy_hooks_to_all_repos.bat` - 批处理版本（兼容性更好）
- `post-commit.bat` - Post-commit hook 批处理脚本
- `svn_post_commit_hook.py` - Post-commit hook Python 脚本

## 使用方法

### 方法一：使用 PowerShell 脚本（推荐）

1. **以管理员身份打开 PowerShell**

2. **运行部署脚本**：
   ```powershell
   cd G:\Projects_AI\AI-Codereview\tools\hooks_svn
   .\deploy_hooks_to_all_repos.ps1
   ```

3. **自定义参数**（可选）：
   ```powershell
   # 指定仓库路径
   .\deploy_hooks_to_all_repos.ps1 -RepositoriesPath "D:\SVN\Repositories"
   
   # 强制覆盖已存在的hook文件
   .\deploy_hooks_to_all_repos.ps1 -Force
   
   # 禁用备份功能
   .\deploy_hooks_to_all_repos.ps1 -BackupExisting:$false
   ```

### 方法二：使用批处理脚本

1. **以管理员身份打开命令提示符**

2. **运行部署脚本**：
   ```batch
   cd G:\Projects_AI\AI-Codereview\tools\hooks_svn
   deploy_hooks_to_all_repos.bat
   ```

3. **修改配置**（如需要）：
   编辑 `deploy_hooks_to_all_repos.bat`，修改以下变量：
   ```batch
   set REPOSITORIES_PATH=C:\Repositories
   set HOOK_SCRIPTS_PATH=%~dp0
   ```

## 脚本功能

### PowerShell 版本功能

- ✅ 自动扫描 VisualSVN Server 仓库目录
- ✅ 为每个仓库创建 hooks 目录（如果不存在）
- ✅ 自动部署 `post-commit.bat` 和 `svn_post_commit_hook.py`
- ✅ 备份现有文件（可选）
- ✅ 强制覆盖模式（可选）
- ✅ 详细的日志输出和统计信息
- ✅ 错误处理和验证

### 批处理版本功能

- ✅ 自动扫描 VisualSVN Server 仓库目录
- ✅ 为每个仓库创建 hooks 目录（如果不存在）
- ✅ 自动部署 `post-commit.bat` 和 `svn_post_commit_hook.py`
- ✅ 跳过已存在的文件（避免覆盖）
- ✅ 基本的错误处理

## 参数说明

### PowerShell 脚本参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-RepositoriesPath` | string | `C:\Repositories` | VisualSVN Server 仓库根目录 |
| `-HookScriptsPath` | string | 脚本所在目录 | Hook 脚本文件所在目录 |
| `-BackupExisting` | switch | `$true` | 是否备份已存在的文件 |
| `-Force` | switch | `$false` | 是否强制覆盖已存在的文件 |

## 工作流程

1. **验证环境**
   - 检查仓库目录是否存在
   - 验证 Hook 脚本文件是否存在

2. **扫描仓库**
   - 遍历仓库目录下的所有子目录
   - 识别有效的 SVN 仓库（包含 `conf` 或 `hooks` 目录）

3. **部署 Hook**
   - 为每个仓库创建 `hooks` 目录（如果不存在）
   - 备份现有文件（如果启用）
   - 复制 `post_commit.bat` → `hooks\post-commit.bat`
   - 复制 `svn_post_commit_hook.py` → `hooks\svn_post_commit_hook.py`

4. **验证和统计**
   - 验证文件是否成功部署
   - 输出部署统计信息

## 配置后续步骤

部署完成后，需要为每个仓库配置 `svn_post_commit_hook.py`：

### 方法一：手动配置（适合不同仓库需要不同配置）

编辑每个仓库的 `hooks\svn_post_commit_hook.py`，修改：
```python
REVIEW_API_URL = "http://your-review-server:5001/review/webhook"
REPO_URL = "https://your-svn-server/svn/RepositoryName/"
```

### 方法二：使用环境变量（推荐，统一配置）

在系统环境变量或 VisualSVN Server 服务环境变量中设置：
```
SVN_REVIEW_API_URL=http://your-review-server:5001/review/webhook
SVN_REPO_URL_PREFIX=https://your-svn-server/svn
```

然后修改 `svn_post_commit_hook.py`，使其自动从仓库路径生成 URL：
```python
import os
import sys

REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', "http://your-review-server:5001/review/webhook")

# 从仓库路径自动生成URL
REPOS = sys.argv[1]
repo_name = os.path.basename(REPOS)
REPO_URL_PREFIX = os.getenv('SVN_REPO_URL_PREFIX', "https://your-svn-server/svn")
REPO_URL = f"{REPO_URL_PREFIX}/{repo_name}/"
```

## 验证部署

### 1. 检查文件是否部署

```powershell
# PowerShell
Get-ChildItem "C:\Repositories\*\hooks\post-commit.bat" -Recurse

# 批处理
dir /s /b C:\Repositories\*\hooks\post-commit.bat
```

### 2. 测试单个仓库的 Hook

```batch
C:\Repositories\RepositoryName\hooks\post-commit.bat "C:\Repositories\RepositoryName" 123
```

### 3. 提交测试代码

在任意仓库中提交代码，检查：
- AI 代码审查系统是否收到 webhook
- Hook 日志文件（`hooks\post-commit.log`）
- VisualSVN Server 日志

## 常见问题

### Q1: 脚本提示权限不足

**解决方案**：
- 以管理员身份运行脚本
- 检查 VisualSVN Server 服务账户是否有权限访问仓库目录

### Q2: 找不到仓库目录

**解决方案**：
- 确认 VisualSVN Server 的仓库路径
- 使用 `-RepositoriesPath` 参数指定正确的路径
- 检查路径是否正确（注意大小写）

### Q3: Hook 文件已存在，被跳过

**解决方案**：
- 使用 `-Force` 参数强制覆盖（PowerShell 版本）
- 或手动删除现有文件后重新运行脚本

### Q4: 如何为新创建的仓库自动部署 Hook？

**解决方案**：
- 定期运行部署脚本（可以添加到计划任务）
- 或创建仓库时手动运行脚本

## 最佳实践

1. **首次部署前备份**：虽然脚本支持备份，但建议先手动备份重要仓库的 hooks 目录

2. **使用环境变量**：通过环境变量配置 API 地址等，避免在每个仓库中重复配置

3. **测试验证**：部署后务必测试几个仓库的 Hook 是否正常工作

4. **定期检查**：定期运行脚本检查是否有新仓库需要部署 Hook

5. **日志监控**：关注 Hook 执行日志，及时发现问题

## 示例输出

```
========================================
SVN Hook 一键部署脚本
========================================

[信息] 仓库目录: C:\Repositories
[信息] Hook脚本目录: G:\Projects_AI\AI-Codereview\tools\hooks_svn

[成功] Hook脚本文件验证通过

[信息] 找到 5 个仓库

----------------------------------------
[信息] 处理仓库: ProjectA
[信息]   创建hooks目录...
[成功]   hooks目录已创建
[信息]   部署 post-commit.bat...
[成功]   post-commit.bat 部署成功
[信息]   部署 svn_post_commit_hook.py...
[成功]   svn_post_commit_hook.py 部署成功
[成功]   仓库 ProjectA 的Hook部署完成

...

========================================
部署完成统计
========================================
[信息] 总仓库数: 5
[成功] 成功: 5
[警告] 跳过: 0
[错误] 失败: 0
```

## 相关文档

- [VisualSVN Server Hook 配置说明](visualsvn_server_setup.md)
- [SVN服务器级别Webhook配置说明](svn_server_webhook_config.md)

