"""审查规则管理服务"""
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional
import os

import pandas as pd
import yaml

from biz.entity.rule_entity import RuleEntity, RuleHistoryEntity
from biz.utils.log import logger


def get_project_root():
    """获取项目根目录的绝对路径"""
    if 'PROJECT_ROOT' in os.environ:
        return Path(os.environ['PROJECT_ROOT'])
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


class RuleService:
    """审查规则管理服务"""
    
    DB_FILE = str(get_project_root() / "data" / "data.db")
    DB_TIMEOUT = 30.0
    YAML_CONFIG_PATH = str(get_project_root() / "conf" / "prompt_templates.yml")
    
    @staticmethod
    def get_db_connection():
        """获取数据库连接，配置超时和WAL模式"""
        conn = sqlite3.connect(RuleService.DB_FILE, timeout=RuleService.DB_TIMEOUT)
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
        except sqlite3.DatabaseError:
            pass
        return conn

    
    @staticmethod
    def import_from_yaml(rule_key: str, imported_by: str = "system") -> bool:
        """
        从YAML文件导入规则到数据库
        
        Args:
            rule_key: 规则键名，如 'code_review_prompt'
            imported_by: 导入人，默认为 'system'
            
        Returns:
            bool: 导入成功返回True，失败返回False
        """
        try:
            # 读取YAML文件
            with open(RuleService.YAML_CONFIG_PATH, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
            
            if rule_key not in yaml_data:
                logger.warn(f"规则 {rule_key} 在YAML文件中不存在")
                return False
            
            rule_data = yaml_data[rule_key]
            system_prompt = rule_data.get('system_prompt', '')
            user_prompt = rule_data.get('user_prompt', '')
            
            if not system_prompt or not user_prompt:
                logger.warn(f"规则 {rule_key} 的prompt内容不完整")
                return False
            
            # 插入到数据库
            conn = RuleService.get_db_connection()
            try:
                cursor = conn.cursor()
                current_time = int(time.time())
                
                # 检查规则是否已存在
                cursor.execute('SELECT id FROM review_rules WHERE rule_key = ?', (rule_key,))
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"规则 {rule_key} 已存在，跳过导入")
                    return True
                
                # 插入规则
                cursor.execute('''
                    INSERT INTO review_rules (rule_key, system_prompt, user_prompt, description, 
                                             is_active, created_at, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (rule_key, system_prompt, user_prompt, f"从YAML导入的{rule_key}规则", 
                      1, current_time, current_time, imported_by))
                
                rule_id = cursor.lastrowid
                
                # 创建初始化历史记录
                cursor.execute('''
                    INSERT INTO review_rules_history (rule_id, rule_key, system_prompt_old, 
                                                     system_prompt_new, user_prompt_old, user_prompt_new,
                                                     change_type, changed_at, changed_by, change_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (rule_id, rule_key, None, system_prompt, None, user_prompt,
                      'create', current_time, imported_by, '从YAML文件初始化导入'))
                
                conn.commit()
                logger.info(f"成功从YAML导入规则: {rule_key}")
                return True
                
            finally:
                conn.close()
                
        except FileNotFoundError:
            logger.error(f"YAML配置文件不存在: {RuleService.YAML_CONFIG_PATH}")
            return False
        except yaml.YAMLError as e:
            logger.error(f"YAML文件解析失败: {e}")
            return False
        except sqlite3.DatabaseError as e:
            logger.error(f"数据库操作失败: {e}")
            return False
        except Exception as e:
            logger.error(f"导入规则失败: {e}")
            return False

    
    @staticmethod
    def get_rule(rule_key: str, style: str = "professional") -> Dict[str, Any]:
        """
        获取指定规则配置
        优先从数据库读取，失败则从YAML读取并自动导入
        
        Args:
            rule_key: 规则键名
            style: 审查风格（用于日志，实际渲染在调用方完成）
            
        Returns:
            Dict: 包含 system_prompt, user_prompt 等字段的字典
        """
        # 尝试从数据库加载
        try:
            conn = RuleService.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, rule_key, system_prompt, user_prompt, description, 
                           is_active, created_at, updated_at, updated_by
                    FROM review_rules
                    WHERE rule_key = ? AND is_active = 1
                ''', (rule_key,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'rule_key': row[1],
                        'system_prompt': row[2],
                        'user_prompt': row[3],
                        'description': row[4],
                        'is_active': row[5],
                        'created_at': row[6],
                        'updated_at': row[7],
                        'updated_by': row[8]
                    }
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            logger.warn(f"数据库查询失败，尝试从YAML加载: {e}")
        
        # 数据库中没有，尝试从YAML导入
        logger.info(f"数据库中未找到规则 {rule_key}，尝试从YAML导入")
        if RuleService.import_from_yaml(rule_key):
            # 导入成功，再次从数据库读取
            try:
                conn = RuleService.get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, rule_key, system_prompt, user_prompt, description, 
                               is_active, created_at, updated_at, updated_by
                        FROM review_rules
                        WHERE rule_key = ? AND is_active = 1
                    ''', (rule_key,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'rule_key': row[1],
                            'system_prompt': row[2],
                            'user_prompt': row[3],
                            'description': row[4],
                            'is_active': row[5],
                            'created_at': row[6],
                            'updated_at': row[7],
                            'updated_by': row[8]
                        }
                finally:
                    conn.close()
            except sqlite3.DatabaseError as e:
                logger.error(f"导入后数据库查询失败: {e}")
        
        # 最后尝试直接从YAML读取（降级方案）
        logger.warn(f"从YAML文件直接读取规则（降级模式）: {rule_key}")
        try:
            with open(RuleService.YAML_CONFIG_PATH, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)
            
            if rule_key in yaml_data:
                rule_data = yaml_data[rule_key]
                return {
                    'id': None,
                    'rule_key': rule_key,
                    'system_prompt': rule_data.get('system_prompt', ''),
                    'user_prompt': rule_data.get('user_prompt', ''),
                    'description': f"从YAML降级加载的{rule_key}规则",
                    'is_active': True,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                    'updated_by': 'yaml_fallback'
                }
        except Exception as e:
            logger.error(f"从YAML读取失败: {e}")
        
        # 所有方法都失败，抛出异常
        error_msg = f"无法加载规则 {rule_key}，数据库和YAML文件均不可用"
        logger.error(error_msg)
        raise Exception(error_msg)

    
    @staticmethod
    def update_rule(rule_key: str, system_prompt: str, user_prompt: str, 
                   updated_by: str, change_reason: Optional[str] = None) -> bool:
        """
        更新规则并记录历史
        
        Args:
            rule_key: 规则键名
            system_prompt: 新的系统提示词
            user_prompt: 新的用户提示词
            updated_by: 修改人
            change_reason: 修改原因（可选）
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            conn = RuleService.get_db_connection()
            try:
                cursor = conn.cursor()
                
                # 获取当前规则
                cursor.execute('''
                    SELECT id, system_prompt, user_prompt
                    FROM review_rules
                    WHERE rule_key = ?
                ''', (rule_key,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warn(f"规则 {rule_key} 不存在")
                    return False
                
                rule_id, old_system_prompt, old_user_prompt = row
                current_time = int(time.time())
                
                # 开始事务
                cursor.execute('BEGIN TRANSACTION')
                
                try:
                    # 更新规则
                    cursor.execute('''
                        UPDATE review_rules
                        SET system_prompt = ?, user_prompt = ?, updated_at = ?, updated_by = ?
                        WHERE rule_key = ?
                    ''', (system_prompt, user_prompt, current_time, updated_by, rule_key))
                    
                    # 创建历史记录
                    cursor.execute('''
                        INSERT INTO review_rules_history (rule_id, rule_key, system_prompt_old, 
                                                         system_prompt_new, user_prompt_old, user_prompt_new,
                                                         change_type, changed_at, changed_by, change_reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (rule_id, rule_key, old_system_prompt, system_prompt, 
                          old_user_prompt, user_prompt, 'update', current_time, 
                          updated_by, change_reason))
                    
                    # 提交事务
                    conn.commit()
                    logger.info(f"成功更新规则: {rule_key} by {updated_by}")
                    return True
                    
                except Exception as e:
                    # 回滚事务
                    conn.rollback()
                    logger.error(f"更新规则失败，已回滚: {e}")
                    return False
                    
            finally:
                conn.close()
                
        except sqlite3.DatabaseError as e:
            logger.error(f"数据库操作失败: {e}")
            return False
        except Exception as e:
            logger.error(f"更新规则失败: {e}")
            return False

    
    @staticmethod
    def get_rule_history(rule_key: str, limit: int = 50) -> pd.DataFrame:
        """
        获取规则修改历史
        
        Args:
            rule_key: 规则键名
            limit: 返回记录数量限制
            
        Returns:
            pd.DataFrame: 历史记录DataFrame
        """
        try:
            conn = RuleService.get_db_connection()
            try:
                query = """
                    SELECT id, rule_id, rule_key, system_prompt_old, system_prompt_new,
                           user_prompt_old, user_prompt_new, change_type, changed_at, 
                           changed_by, change_reason
                    FROM review_rules_history
                    WHERE rule_key = ?
                    ORDER BY changed_at DESC
                    LIMIT ?
                """
                df = pd.read_sql_query(sql=query, con=conn, params=[rule_key, limit])
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            logger.error(f"查询历史记录失败: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def get_all_rules() -> pd.DataFrame:
        """
        获取所有规则列表
        
        Returns:
            pd.DataFrame: 规则列表DataFrame
        """
        try:
            conn = RuleService.get_db_connection()
            try:
                query = """
                    SELECT id, rule_key, description, is_active, created_at, updated_at, updated_by
                    FROM review_rules
                    ORDER BY rule_key
                """
                df = pd.read_sql_query(sql=query, con=conn)
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            logger.error(f"查询规则列表失败: {e}")
            return pd.DataFrame()



# 系统启动时自动初始化规则
def init_rules():
    """
    系统启动时自动初始化规则
    检查数据库中是否存在规则，如果不存在则从YAML导入
    """
    try:
        conn = RuleService.get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM review_rules')
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("数据库中无规则配置，开始从YAML导入...")
                # 导入默认规则
                RuleService.import_from_yaml('code_review_prompt', 'system')
                logger.info("规则导入完成")
            else:
                logger.info(f"数据库中已存在 {count} 条规则配置")
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"规则初始化失败: {e}")


# 在模块加载时自动初始化
init_rules()
