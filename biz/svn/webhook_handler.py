import os
import re
import subprocess
from typing import List, Dict, Any
from urllib.parse import urlparse

from biz.utils.log import logger


def filter_changes(changes: list):
    """
    过滤数据，只保留支持的文件类型以及必要的字段信息
    专门处理SVN格式的变更
    """
    # 从环境变量中获取支持的文件扩展名
    supported_extensions = [
        ext.strip() for ext in os.getenv('SUPPORTED_EXTENSIONS', '.java,.py,.php').split(',')
        if ext.strip()
    ]

    filtered_changes = []
    for item in changes:
        # 跳过删除的文件
        status = (item.get('status') or '').lower()
        if status in ('removed', 'deleted'):
            continue

        new_path = item.get('new_path') or item.get('path') or ''
        if not new_path:
            continue

        # 检查文件扩展名
        if supported_extensions and not any(new_path.endswith(ext) for ext in supported_extensions):
            continue

        diff_text = item.get('diff') or ''
        additions = item.get('additions')
        deletions = item.get('deletions')

        # 如果没有提供additions/deletions，从diff中计算
        if additions is None:
            additions = len(re.findall(r'^\+(?!\+\+)', diff_text, re.MULTILINE))
        if deletions is None:
            deletions = len(re.findall(r'^-(?!--)', diff_text, re.MULTILINE))

        filtered_changes.append({
            'diff': diff_text,
            'new_path': new_path,
            'additions': additions,
            'deletions': deletions
        })

    return filtered_changes


def slugify_url(original_url: str) -> str:
    """
    将原始URL转换为适合作为文件名的字符串，其中非字母或数字的字符会被替换为下划线
    """
    # Remove URL scheme (http, https, svn, svn+ssh, etc.) if present
    original_url = re.sub(r'^[a-z+]+://', '', original_url)

    # Replace non-alphanumeric characters (except underscore) with underscores
    target = re.sub(r'[^a-zA-Z0-9]', '_', original_url)

    # Remove trailing underscore if present
    target = target.rstrip('_')

    return target


class CommitHandler:
    """
    处理SVN提交事件的Handler类
    """
    
    def __init__(self, webhook_data: dict, svn_repo_url: str = None, svn_username: str = None, svn_password: str = None):
        """
        初始化SVN Commit Handler
        
        :param webhook_data: webhook数据
        :param svn_repo_url: SVN仓库URL（如果webhook中没有提供）
        :param svn_username: SVN用户名（如果需要认证）
        :param svn_password: SVN密码（如果需要认证）
        """
        self.webhook_data = webhook_data
        self.svn_repo_url = svn_repo_url or os.getenv('SVN_REPO_URL')
        self.svn_username = svn_username or os.getenv('SVN_USERNAME')
        self.svn_password = svn_password or os.getenv('SVN_PASSWORD')
        
        # 从webhook数据中提取信息
        self.repository_url = webhook_data.get('repository_url') or self.svn_repo_url
        self.revision = webhook_data.get('revision')
        self.author = webhook_data.get('author')
        self.message = webhook_data.get('message') or webhook_data.get('commit_message', '')
        self.timestamp = webhook_data.get('timestamp')
        
        if not self.repository_url:
            raise ValueError("SVN repository URL is required")
        if not self.revision:
            raise ValueError("SVN revision number is required")

    def _run_svn_command(self, command: List[str], cwd: str = None) -> tuple[str, str, int]:
        """
        执行SVN命令
        
        :param command: SVN命令列表
        :param cwd: 工作目录
        :return: (stdout, stderr, return_code)
        """
        try:
            # 如果需要认证，添加用户名和密码参数
            if self.svn_username:
                command.extend(['--username', self.svn_username])
            if self.svn_password:
                command.extend(['--password', self.svn_password])
            
            # 添加非交互式标志
            command.extend(['--non-interactive'])
            
            # 处理SSL证书验证问题
            # 如果环境变量SVN_TRUST_SERVER_CERT设置为true，则信任服务器证书
            # 这对于自签名证书或证书主机名不匹配的情况很有用
            trust_cert = os.getenv('SVN_TRUST_SERVER_CERT', 'false').lower() in ('true', '1', 'yes')
            if trust_cert:
                command.extend(['--trust-server-cert'])
            
            logger.debug(f"Executing SVN command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warn(f"SVN command failed with return code {result.returncode}: {result.stderr}")
            
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"SVN command timed out: {' '.join(command)}")
            return "", "Command timed out", -1
        except Exception as e:
            logger.error(f"Error executing SVN command: {e}")
            return "", str(e), -1

    def get_commit_info(self) -> Dict[str, Any]:
        """
        获取提交信息
        
        :return: 包含提交信息的字典
        """
        commit_info = {
            'id': str(self.revision),
            'message': self.message,
            'author': self.author,
            'timestamp': self.timestamp,
            'revision': self.revision
        }
        
        # 如果没有从webhook获取完整信息，尝试通过SVN命令获取
        if not self.message or not self.author:
            try:
                # 使用svn log获取提交信息
                command = ['svn', 'log', '-r', str(self.revision), '--xml', self.repository_url]
                stdout, stderr, return_code = self._run_svn_command(command)
                
                if return_code == 0 and stdout:
                    # 解析XML格式的log输出
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(stdout)
                    logentry = root.find('logentry')
                    if logentry is not None:
                        if not commit_info['author']:
                            author_elem = logentry.find('author')
                            if author_elem is not None:
                                commit_info['author'] = author_elem.text
                        
                        if not commit_info['message']:
                            msg_elem = logentry.find('msg')
                            if msg_elem is not None:
                                commit_info['message'] = msg_elem.text or ''
                        
                        if not commit_info['timestamp']:
                            date_elem = logentry.find('date')
                            if date_elem is not None:
                                commit_info['timestamp'] = date_elem.text
            except Exception as e:
                logger.warn(f"Failed to get commit info from SVN: {e}")
        
        return commit_info

    def get_commit_changes(self) -> List[Dict[str, Any]]:
        """
        获取提交的代码变更
        
        优先使用webhook中传递的diff信息（如果hook在服务器端获取了diff）
        如果没有，则尝试通过svn diff命令获取
        
        :return: 变更列表，格式与GitLab/GitHub兼容
        """
        changes = []
        
        try:
            # 优先使用webhook中传递的diff信息（hook在服务器端获取，避免SSL证书问题）
            diff_text = self.webhook_data.get('diff')
            
            if diff_text:
                logger.info(f"Using diff from webhook data for revision {self.revision}")
                # 解析SVN diff格式
                changes = self._parse_svn_diff(diff_text)
                if changes:
                    return changes
                else:
                    logger.warn(f"Failed to parse diff from webhook, will try to get diff via svn command")
            
            # 如果没有从webhook获取到diff，尝试通过svn diff命令获取（备用方案）
            logger.info(f"Getting diff via svn command for revision {self.revision}")
            prev_revision = int(self.revision) - 1
            if prev_revision < 1:
                logger.info(f"Revision {self.revision} is the first revision, no previous version to compare")
                return []
            
            # 使用svn diff获取变更
            command = ['svn', 'diff', '-r', f'{prev_revision}:{self.revision}', self.repository_url]
            stdout, stderr, return_code = self._run_svn_command(command)
            
            if return_code != 0:
                logger.error(f"Failed to get SVN diff: {stderr}")
                return []
            
            if not stdout:
                logger.info(f"No changes found in revision {self.revision}")
                return []
            
            # 解析SVN diff格式
            changes = self._parse_svn_diff(stdout)
            
        except Exception as e:
            logger.error(f"Error getting commit changes: {e}")
            return []
        
        return changes

    def _parse_svn_diff(self, diff_text: str) -> List[Dict[str, Any]]:
        """
        解析SVN diff格式，转换为统一的changes格式
        
        支持两种SVN diff格式：
        1. svn diff格式:
           Index: path/to/file.py
           ===================================================================
           --- path/to/file.py	(revision 123)
           +++ path/to/file.py	(revision 124)
        
        2. svnlook diff格式:
           Modified: path/to/file.py
           ===================================================================
           --- path/to/file.py	2025-12-06 10:09:25 UTC (rev 14)
           +++ path/to/file.py	2025-12-06 10:11:59 UTC (rev 15)
        
        :param diff_text: SVN diff文本
        :return: changes列表
        """
        changes = []
        current_file = None
        current_diff_lines = []
        current_path = None
        status = None
        
        # 处理Windows换行符（\r\n）和Unix换行符（\n）
        lines = diff_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检测文件开始标记 - svn diff格式 (Index:)
            if line.startswith('Index: '):
                # 保存前一个文件
                if current_file is not None and current_path:
                    changes.append({
                        'diff': '\n'.join(current_diff_lines),
                        'new_path': current_path,
                        'old_path': current_path,
                        'status': status or 'modified',
                        'additions': len([l for l in current_diff_lines if l.startswith('+') and not l.startswith('+++')]),
                        'deletions': len([l for l in current_diff_lines if l.startswith('-') and not l.startswith('---')])
                    })
                
                # 开始新文件
                current_path = line[7:].strip()  # 移除 "Index: " 前缀
                current_diff_lines = [line]
                current_file = True
                status = None
                i += 1
                continue
            
            # 检测文件开始标记 - svnlook diff格式 (Modified:/Added:/Deleted:)
            if line.startswith('Modified: ') or line.startswith('Added: ') or line.startswith('Deleted: '):
                # 保存前一个文件
                if current_file is not None and current_path:
                    changes.append({
                        'diff': '\n'.join(current_diff_lines),
                        'new_path': current_path,
                        'old_path': current_path,
                        'status': status or 'modified',
                        'additions': len([l for l in current_diff_lines if l.startswith('+') and not l.startswith('+++')]),
                        'deletions': len([l for l in current_diff_lines if l.startswith('-') and not l.startswith('---')])
                    })
                
                # 开始新文件
                if line.startswith('Modified: '):
                    current_path = line[10:].strip()  # 移除 "Modified: " 前缀
                    status = 'modified'
                elif line.startswith('Added: '):
                    current_path = line[7:].strip()  # 移除 "Added: " 前缀
                    status = 'added'
                elif line.startswith('Deleted: '):
                    current_path = line[9:].strip()  # 移除 "Deleted: " 前缀
                    status = 'removed'
                
                current_diff_lines = [line]
                current_file = True
                i += 1
                continue
            
            # 检测文件状态（新增/删除/修改）
            if line.startswith('--- '):
                # 检查是否是删除的文件
                if '/dev/null' in line or '(revision 0)' in line:
                    status = 'added'
                elif current_file:
                    status = 'modified'
                current_diff_lines.append(line)
                i += 1
                continue
            
            if line.startswith('+++ '):
                # 检查是否是新增的文件
                if '/dev/null' in line:
                    status = 'removed'
                elif status != 'added':
                    status = 'modified'
                current_diff_lines.append(line)
                i += 1
                continue
            
            # 收集diff内容
            if current_file:
                current_diff_lines.append(line)
            
            i += 1
        
        # 保存最后一个文件
        if current_file is not None and current_path:
            changes.append({
                'diff': '\n'.join(current_diff_lines),
                'new_path': current_path,
                'old_path': current_path,
                'status': status or 'modified',
                'additions': len([l for l in current_diff_lines if l.startswith('+') and not l.startswith('+++')]),
                'deletions': len([l for l in current_diff_lines if l.startswith('-') and not l.startswith('---')])
            })
        
        return changes

    def add_commit_notes(self, message: str):
        """
        添加提交注释（SVN通常不支持在提交后添加注释，此方法保留接口兼容性）
        
        :param message: 注释内容
        """
        # SVN不像Git那样支持在提交后添加注释
        # 这里可以记录日志或通过其他方式通知（如IM通知）
        logger.info(f"SVN commit review result for revision {self.revision}: {message}")
        # 可以考虑通过其他渠道发送通知，比如IM消息

