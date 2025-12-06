#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVN Post-Commit Hook Script
用于将SVN提交事件发送到AI代码审查系统

使用方法：
1. 将此文件复制到SVN仓库的hooks目录：/path/to/svn/repo/hooks/post-commit
2. 修改下方的配置参数
3. 添加执行权限：chmod +x /path/to/svn/repo/hooks/post-commit
4. 测试：手动执行脚本或提交代码测试

配置说明：
- REVIEW_API_URL: AI代码审查系统的API地址
- REPO_URL: SVN仓库的URL地址
- SVN_USERNAME: SVN认证用户名（如果需要）
- SVN_PASSWORD: SVN认证密码（如果需要）
- MAX_RETRIES: 失败重试次数
- RETRY_DELAY: 重试延迟（秒）
"""

import sys
import os
import subprocess
import json
import urllib.request
import urllib.error
import time
import logging
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, Union

# ==================== 配置区域 ====================
# AI代码审查系统API地址（必填）
# 优先从环境变量读取，如果没有则使用默认值（需要修改）
REVIEW_API_URL = os.getenv('SVN_REVIEW_API_URL', "http://10.10.9.12:5001/review/webhook")

# SVN仓库URL（必填，可以从环境变量或配置文件中读取）
# 优先从环境变量读取，如果没有则使用默认值（需要修改）
REPO_URL = os.getenv('SVN_REPO_URL', "https://10.10.9.12/svn/TestSVN/")

# SVN认证信息（可选，如果仓库需要认证）
# 优先从环境变量读取
SVN_USERNAME = os.getenv('SVN_USERNAME')  # 例如: "username"
SVN_PASSWORD = os.getenv('SVN_PASSWORD')  # 例如: "password"

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 5  # 秒

# 日志配置（可选，用于调试）
LOG_FILE = None  # 例如: "/var/log/svn/post-commit.log"

# 其他配置常量
WEBHOOK_TIMEOUT = 30  # 秒
SVNLOOK_COMMAND = 'svnlook'
# ==================== 配置区域结束 ====================


def setup_logging() -> None:
    """配置日志系统"""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    handlers = []
    if LOG_FILE:
        handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))
    handlers.append(logging.StreamHandler(sys.stderr))
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
        force=True  # 强制重新配置，避免重复配置问题
    )


def decode_output(output_bytes: Union[bytes, str]) -> str:
    """
    解码subprocess输出，优先使用UTF-8编码
    在Windows系统上，subprocess默认使用系统编码（GBK），但SVN输出可能是UTF-8
    
    :param output_bytes: subprocess返回的字节数据（如果是字符串则直接返回）
    :return: 解码后的字符串（确保是有效的Unicode字符串）
    """
    if isinstance(output_bytes, str):
        # 如果已经是字符串，尝试修复可能的编码错误
        try:
            # 尝试将字符串编码为latin-1再解码为UTF-8（修复错误的编码）
            return output_bytes.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return output_bytes
    
    # 按优先级尝试不同的编码方式
    encodings = ['utf-8', 'gbk']
    
    # 添加系统默认编码（如果不在已尝试列表中）
    default_encoding = sys.getdefaultencoding()
    if default_encoding and default_encoding.lower() not in encodings:
        encodings.append(default_encoding)
    
    # 尝试解码
    for encoding in encodings:
        try:
            return output_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # 最后使用UTF-8，用replace处理错误字符（避免完全失败）
    return output_bytes.decode('utf-8', errors='replace')


def run_svnlook_command(command: str, repos: str, rev: str) -> Optional[str]:
    """
    执行svnlook命令并返回解码后的输出
    
    :param command: svnlook子命令（如 'author', 'log', 'date', 'diff'）
    :param repos: SVN仓库路径
    :param rev: 提交版本号
    :return: 命令输出字符串，失败返回None
    """
    try:
        cmd = [SVNLOOK_COMMAND, command, '-r', rev, repos]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return decode_output(output).strip()
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to run svnlook {command}: {e}")
        return None
    except FileNotFoundError:
        logging.error(f"{SVNLOOK_COMMAND} command not found. Please ensure SVN is installed.")
        return None
    except Exception as e:
        logging.warning(f"Error running svnlook {command}: {e}")
        return None


def parse_timestamp(timestamp_str: str) -> str:
    """
    解析SVN时间戳并转换为ISO格式
    
    svnlook date 返回格式通常是：2025-12-06 17:49:25 +0800 (周六, 06 12月 2025)
    
    :param timestamp_str: SVN返回的时间戳字符串
    :return: ISO格式的时间戳字符串
    """
    # 提取括号前的部分（包含时区信息）
    timestamp_part = timestamp_str.split('(')[0].strip()
    
    if not timestamp_part:
        logging.warning(f"Could not extract timestamp from: {timestamp_str}")
        return datetime.now().isoformat()
    
    # 尝试解析带时区的格式：%Y-%m-%d %H:%M:%S %z
    try:
        dt = datetime.strptime(timestamp_part, '%Y-%m-%d %H:%M:%S %z')
        return dt.isoformat()
    except ValueError:
        pass
    
    # 尝试不带时区的格式：%Y-%m-%d %H:%M:%S
    try:
        dt = datetime.strptime(timestamp_part, '%Y-%m-%d %H:%M:%S')
        return dt.isoformat()
    except ValueError:
        pass
    
    # 如果都失败，使用当前时间
    logging.warning(f"Could not parse timestamp format: {timestamp_str}, using current time")
    return datetime.now().isoformat()


def get_svn_diff(repos: str, rev: str) -> str:
    """
    获取SVN提交的diff信息
    
    :param repos: SVN仓库路径
    :param rev: 提交版本号
    :return: diff文本字符串
    """
    try:
        prev_rev = int(rev) - 1
        if prev_rev < 1:
            logging.info(f"Revision {rev} is the first revision, no previous version to compare")
            return ""
    except ValueError:
        logging.warning(f"Invalid revision number: {rev}")
        return ""
    
    diff_text = run_svnlook_command('diff', repos, rev)
    return diff_text if diff_text else ""


def get_svn_info(repos: str, rev: str) -> Tuple[str, str, str]:
    """
    获取SVN提交信息
    
    :param repos: SVN仓库路径
    :param rev: 提交版本号
    :return: (author, message, timestamp) 元组
    """
    default_timestamp = datetime.now().isoformat()
    
    # 获取提交者
    author = run_svnlook_command('author', repos, rev) or "unknown"
    
    # 获取提交消息
    message = run_svnlook_command('log', repos, rev) or ""
    
    # 获取提交时间
    timestamp_str = run_svnlook_command('date', repos, rev)
    if timestamp_str:
        timestamp = parse_timestamp(timestamp_str)
    else:
        timestamp = default_timestamp
    
    return author, message, timestamp


def send_webhook(
    api_url: str,
    data: Dict[str, Any],
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY
) -> bool:
    """
    发送webhook请求，支持重试
    
    :param api_url: API地址
    :param data: 要发送的数据字典
    :param max_retries: 最大重试次数
    :param retry_delay: 重试延迟（秒）
    :return: 是否成功
    """
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    headers = {
        'Content-Type': 'application/json',
        'X-SVN-Event': 'commit'
    }
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(api_url, data=json_data, headers=headers)
            response = urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT)
            status_code = response.getcode()
            
            if status_code == 200:
                logging.info(f"Webhook sent successfully (attempt {attempt + 1}/{max_retries})")
                return True
            
            logging.warning(f"Webhook returned status code {status_code} (attempt {attempt + 1}/{max_retries})")
                
        except urllib.error.HTTPError as e:
            logging.error(f"HTTP error {e.code}: {e.reason} (attempt {attempt + 1}/{max_retries})")
            # 4xx错误不重试（客户端错误）
            if 400 <= e.code < 500:
                return False
        except urllib.error.URLError as e:
            logging.error(f"URL error: {e.reason} (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logging.error(f"Unexpected error: {e} (attempt {attempt + 1}/{max_retries})")
        
        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    
    logging.error(f"Failed to send webhook after {max_retries} attempts")
    return False


def validate_config() -> None:
    """验证配置参数"""
    default_api_url = "http://your-review-server:5001/review/webhook"
    default_repo_url = "svn://your-svn-server.com/repo"
    
    if not REVIEW_API_URL or REVIEW_API_URL == default_api_url:
        error_msg = "Please configure REVIEW_API_URL in the script or set SVN_REVIEW_API_URL environment variable"
        logging.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    
    if not REPO_URL or REPO_URL == default_repo_url:
        error_msg = "Please configure REPO_URL in the script or set SVN_REPO_URL environment variable"
        logging.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)


def build_webhook_data(repos: str, rev: str, author: str, message: str, 
                      timestamp: str, diff_text: str) -> Dict[str, Any]:
    """
    构建webhook数据
    
    :param repos: SVN仓库路径
    :param rev: 提交版本号
    :param author: 提交者
    :param message: 提交消息
    :param timestamp: 提交时间戳
    :param diff_text: diff文本
    :return: webhook数据字典
    """
    webhook_data = {
        "repository_url": REPO_URL,
        "revision": rev,
        "author": author,
        "message": message,
        "timestamp": timestamp
    }
    
    if diff_text:
        webhook_data["diff"] = diff_text
        logging.info(f"Got diff for revision {rev}, size: {len(diff_text)} characters")
    else:
        logging.warning(f"No diff found for revision {rev}")
    
    # 添加SVN认证信息（如果配置了）
    if SVN_USERNAME:
        webhook_data["svn_username"] = SVN_USERNAME
    if SVN_PASSWORD:
        webhook_data["svn_password"] = SVN_PASSWORD
    
    return webhook_data


def validate_message_encoding(message: str) -> None:
    """验证消息编码（调试用）"""
    if message:
        try:
            message.encode('utf-8')
        except UnicodeEncodeError:
            logging.warning("Message encoding issue detected, may contain invalid characters")


def main() -> None:
    """主函数"""
    setup_logging()
    
    # 检查参数
    if len(sys.argv) < 3:
        error_msg = f"Usage: post-commit REPOS REV. Got {len(sys.argv)-1} arguments: {sys.argv[1:]}"
        logging.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    
    repos = sys.argv[1]
    rev = sys.argv[2]
    
    # 验证配置
    validate_config()
    
    try:
        logging.info(f"Processing commit revision {rev} for repository {repos}")
        
        # 获取提交信息
        author, message, timestamp = get_svn_info(repos, rev)
        validate_message_encoding(message)
        
        # 获取diff信息
        diff_text = get_svn_diff(repos, rev)
        
        # 构建webhook数据
        webhook_data = build_webhook_data(repos, rev, author, message, timestamp, diff_text)
        
        # 发送webhook请求
        success = send_webhook(REVIEW_API_URL, webhook_data)
        
        if success:
            logging.info(f"Successfully sent webhook for revision {rev}")
        else:
            logging.error(f"Failed to send webhook for revision {rev}")
        
        # 即使失败也返回0，避免阻塞SVN提交
        # 如果需要严格模式，可以改为 sys.exit(1)
        sys.exit(0)
            
    except Exception as e:
        error_msg = f"Unexpected error in post-commit hook: {e}"
        logging.error(error_msg, exc_info=True)
        print(error_msg, file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # 即使出错也返回0，避免阻塞SVN提交
        sys.exit(0)


if __name__ == '__main__':
    main()

