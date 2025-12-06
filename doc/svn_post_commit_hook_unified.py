#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVN Post-Commit Hook Script (Unified Version)
用于SVN服务器级别配置，监听所有仓库的提交

使用方法：
1. 将此文件复制到统一位置：/opt/svn/hooks/post-commit-unified.py
2. 修改下方的配置参数
3. 为每个仓库创建符号链接：
   ln -s /opt/svn/hooks/post-commit-unified.py /path/to/svn/repo/hooks/post-commit
4. 添加执行权限：chmod +x /opt/svn/hooks/post-commit-unified.py

配置说明：
- REVIEW_API_URL: AI代码审查系统的API地址
- SVN_SERVER_URL: SVN服务器的基础URL（用于生成仓库URL）
- SVN_USERNAME: SVN认证用户名（如果需要）
- SVN_PASSWORD: SVN认证密码（如果需要）
- CONFIG_FILE: 仓库配置文件路径（可选）
"""

import sys
import os
import subprocess
import json
import urllib.request
import urllib.error
import logging
from datetime import datetime

# ==================== 配置区域 ====================
# AI代码审查系统API地址（必填）
REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', "http://your-review-server:5001/review/webhook")

# SVN服务器基础URL（用于生成仓库URL）
# 例如：如果仓库路径为 /var/svn/repos/repo1，URL为 svn://server/repo1
SVN_SERVER_URL = os.getenv('SVN_SERVER_URL', "svn://your-svn-server.com")

# SVN认证信息（可选，如果仓库需要认证）
SVN_USERNAME = os.getenv('SVN_USERNAME')
SVN_PASSWORD = os.getenv('SVN_PASSWORD')

# 仓库配置文件路径（可选，用于不同仓库的不同配置）
CONFIG_FILE = os.getenv('SVN_REPO_CONFIG_FILE', '/opt/svn/hooks/repo_config.json')

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 日志配置（可选，用于调试）
LOG_FILE = os.getenv('SVN_HOOK_LOG_FILE', '/var/log/svn/post-commit.log')

# 仓库路径到URL的映射规则
# 如果仓库路径为 /var/svn/repos/repo1，URL生成方式：
# - 'basename': 使用 basename，结果为 svn://server/repo1
# - 'relative': 相对于某个基础路径，需要设置 REPOS_BASE_PATH
REPO_URL_MODE = 'basename'  # 'basename' 或 'relative'
REPOS_BASE_PATH = '/var/svn/repos'  # 当使用 'relative' 模式时使用
# ==================== 配置区域结束 ====================


def setup_logging():
    """配置日志"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    if LOG_FILE:
        # 确保日志目录存在
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                pass  # 如果无法创建目录，使用默认日志
        
        try:
            logging.basicConfig(
                filename=LOG_FILE,
                level=logging.INFO,
                format=log_format,
                filemode='a'  # 追加模式
            )
        except Exception:
            # 如果无法写入日志文件，使用默认日志
            logging.basicConfig(
                level=logging.WARNING,
                format=log_format
            )
    else:
        logging.basicConfig(
            level=logging.WARNING,  # 默认只记录警告和错误
            format=log_format
        )


def load_repo_config(repo_name):
    """
    从配置文件加载仓库配置
    
    :param repo_name: 仓库名称
    :return: 仓库配置字典，如果不存在则返回None
    """
    if not CONFIG_FILE or not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            repos_config = config.get('repos', {})
            
            # 优先查找精确匹配
            if repo_name in repos_config:
                return repos_config[repo_name]
            
            # 查找通配符配置
            if '*' in repos_config:
                return repos_config['*']
            
            return None
    except Exception as e:
        logging.warning(f"Failed to load repo config: {e}")
        return None


def get_repo_url(repos_path):
    """
    根据仓库路径生成仓库URL
    
    :param repos_path: SVN仓库路径
    :return: 仓库URL
    """
    repo_name = os.path.basename(repos_path.rstrip('/'))
    
    # 尝试从配置文件获取URL
    repo_config = load_repo_config(repo_name)
    if repo_config and repo_config.get('url'):
        url_template = repo_config['url']
        # 支持 {repo_name} 占位符
        return url_template.replace('{repo_name}', repo_name)
    
    # 根据模式生成URL
    if REPO_URL_MODE == 'relative' and REPOS_BASE_PATH:
        try:
            relative_path = os.path.relpath(repos_path, REPOS_BASE_PATH)
            # 将路径分隔符替换为URL分隔符
            repo_path_part = relative_path.replace(os.sep, '/')
            return f"{SVN_SERVER_URL}/{repo_path_part}"
        except ValueError:
            # 如果不在基础路径下，使用basename模式
            pass
    
    # 默认使用basename模式
    return f"{SVN_SERVER_URL}/{repo_name}"


def get_repo_auth(repo_name):
    """
    获取仓库认证信息
    
    :param repo_name: 仓库名称
    :return: (username, password) 元组
    """
    # 尝试从配置文件获取
    repo_config = load_repo_config(repo_name)
    if repo_config:
        return repo_config.get('username'), repo_config.get('password')
    
    # 使用全局配置
    return SVN_USERNAME, SVN_PASSWORD


def get_svn_info(repos, rev):
    """
    获取SVN提交信息
    
    :param repos: SVN仓库路径
    :param rev: 提交版本号
    :return: (author, message, timestamp) 元组
    """
    try:
        # 获取提交者
        author = subprocess.check_output(
            ['svnlook', 'author', '-r', rev, repos],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        # 获取提交消息
        message = subprocess.check_output(
            ['svnlook', 'log', '-r', rev, repos],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        # 获取提交时间
        timestamp = subprocess.check_output(
            ['svnlook', 'date', '-r', rev, repos],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        # 转换时间格式为ISO格式
        try:
            # 尝试解析svnlook返回的时间格式
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S %z (%a, %d %b %Y)')
            timestamp = dt.isoformat()
        except ValueError:
            try:
                dt = datetime.strptime(timestamp.split('(')[0].strip(), '%Y-%m-%d %H:%M:%S')
                timestamp = dt.isoformat()
            except ValueError:
                timestamp = datetime.now().isoformat()
        
        return author, message, timestamp
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get SVN info: {e}")
        return "unknown", "", datetime.now().isoformat()
    except FileNotFoundError:
        logging.error("svnlook command not found. Please ensure SVN is installed.")
        return "unknown", "", datetime.now().isoformat()


def send_webhook(api_url, data, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """
    发送webhook请求，支持重试
    
    :param api_url: API地址
    :param data: 要发送的数据字典
    :param max_retries: 最大重试次数
    :param retry_delay: 重试延迟（秒）
    :return: 是否成功
    """
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                api_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'X-SVN-Event': 'commit'
                }
            )
            
            response = urllib.request.urlopen(req, timeout=30)
            status_code = response.getcode()
            
            if status_code == 200:
                logging.info(f"Webhook sent successfully (attempt {attempt + 1}/{max_retries})")
                return True
            else:
                logging.warning(f"Webhook returned status code {status_code} (attempt {attempt + 1}/{max_retries})")
                
        except urllib.error.HTTPError as e:
            logging.error(f"HTTP error {e.code}: {e.reason} (attempt {attempt + 1}/{max_retries})")
            if e.code < 500:  # 4xx错误不重试
                return False
        except urllib.error.URLError as e:
            logging.error(f"URL error: {e.reason} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logging.error(f"Unexpected error: {e} (attempt {attempt + 1}/{max_retries})")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries - 1:
            import time
            time.sleep(retry_delay)
    
    logging.error(f"Failed to send webhook after {max_retries} attempts")
    return False


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    
    # 检查参数
    if len(sys.argv) < 3:
        logging.error("Usage: post-commit REPOS REV")
        sys.exit(1)
    
    REPOS = sys.argv[1]
    REV = sys.argv[2]
    
    # 验证配置
    if not REVIEW_API_URL or REVIEW_API_URL == "http://your-review-server:5001/review/webhook":
        logging.error("Please configure REVIEW_API_URL in the script or environment variable SVN_REVIEW_API_URL")
        sys.exit(1)
    
    try:
        # 获取仓库名称和URL
        repo_name = os.path.basename(REPOS.rstrip('/'))
        repo_url = get_repo_url(REPOS)
        
        # 获取提交信息
        logging.info(f"Processing commit revision {REV} for repository {repo_name} ({repo_url})")
        author, message, timestamp = get_svn_info(REPOS, REV)
        
        # 获取认证信息
        username, password = get_repo_auth(repo_name)
        
        # 构建webhook数据
        webhook_data = {
            "repository_url": repo_url,
            "revision": REV,
            "author": author,
            "message": message,
            "timestamp": timestamp
        }
        
        # 如果配置了认证信息，添加到webhook数据中
        if username:
            webhook_data["svn_username"] = username
        if password:
            webhook_data["svn_password"] = password
        
        # 发送webhook请求
        success = send_webhook(REVIEW_API_URL, webhook_data)
        
        if success:
            logging.info(f"Successfully sent webhook for revision {REV} (repo: {repo_name})")
            sys.exit(0)
        else:
            logging.error(f"Failed to send webhook for revision {REV} (repo: {repo_name})")
            # 即使失败也返回0，避免阻塞SVN提交
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Unexpected error in post-commit hook: {e}", exc_info=True)
        # 即使出错也返回0，避免阻塞SVN提交
        sys.exit(0)


if __name__ == '__main__':
    main()

