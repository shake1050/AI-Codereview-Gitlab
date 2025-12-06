#!/bin/bash
# SVN Hook自动配置脚本
# 用于为所有SVN仓库自动配置post-commit hook

set -e

# 配置变量
HOOK_SCRIPT="${SVN_HOOK_SCRIPT:-/opt/svn/hooks/post-commit-unified.py}"
SVN_REPOS_BASE="${SVN_REPOS_BASE:-/var/svn/repos}"
BACKUP_DIR="${SVN_HOOK_BACKUP_DIR:-/opt/svn/hooks/backup}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查hook脚本是否存在
if [ ! -f "$HOOK_SCRIPT" ]; then
    log_error "Hook script not found at $HOOK_SCRIPT"
    log_info "Please copy svn_post_commit_hook_unified.py to $HOOK_SCRIPT"
    exit 1
fi

# 确保hook脚本有执行权限
chmod +x "$HOOK_SCRIPT"
log_info "Ensured hook script is executable"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 统计变量
total_repos=0
configured_repos=0
skipped_repos=0
error_repos=0

# 为所有仓库配置hook
log_info "Scanning repositories in $SVN_REPOS_BASE..."

for repo in "$SVN_REPOS_BASE"/*; do
    if [ ! -d "$repo" ]; then
        continue
    fi
    
    repo_name=$(basename "$repo")
    total_repos=$((total_repos + 1))
    
    # 检查是否是SVN仓库（检查是否有hooks目录）
    if [ ! -d "$repo/hooks" ]; then
        log_warn "Skipping $repo_name: not a valid SVN repository (no hooks directory)"
        skipped_repos=$((skipped_repos + 1))
        continue
    fi
    
    hook_path="$repo/hooks/post-commit"
    
    # 如果hook已存在
    if [ -e "$hook_path" ]; then
        # 如果是符号链接且指向我们的脚本，跳过
        if [ -L "$hook_path" ] && [ "$(readlink "$hook_path")" = "$HOOK_SCRIPT" ]; then
            log_info "Hook already configured for repository: $repo_name"
            configured_repos=$((configured_repos + 1))
            continue
        fi
        
        # 如果是文件，备份它
        if [ -f "$hook_path" ] && [ ! -L "$hook_path" ]; then
            backup_file="$BACKUP_DIR/${repo_name}_post-commit_$(date +%Y%m%d_%H%M%S)"
            cp "$hook_path" "$backup_file"
            log_warn "Backed up existing hook for $repo_name to $backup_file"
        fi
        
        # 删除现有hook
        rm -f "$hook_path"
    fi
    
    # 创建符号链接
    if ln -s "$HOOK_SCRIPT" "$hook_path"; then
        log_info "Created hook for repository: $repo_name"
        configured_repos=$((configured_repos + 1))
    else
        log_error "Failed to create hook for repository: $repo_name"
        error_repos=$((error_repos + 1))
    fi
done

# 输出统计信息
echo ""
log_info "Hook setup completed!"
echo "  Total repositories: $total_repos"
echo "  Configured: $configured_repos"
echo "  Skipped: $skipped_repos"
echo "  Errors: $error_repos"

# 如果有错误，返回非零退出码
if [ $error_repos -gt 0 ]; then
    exit 1
fi

exit 0

