import sqlite3
from pathlib import Path
import os

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity


def get_project_root():
    """获取项目根目录的绝对路径"""
    # 优先使用环境变量（由 ui.py 设置）
    if 'PROJECT_ROOT' in os.environ:
        return Path(os.environ['PROJECT_ROOT'])
    # 否则从当前文件位置计算（从 biz/service/review_service.py 向上两级到项目根目录）
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent


class ReviewService:
    # 使用绝对路径
    DB_FILE = str(get_project_root() / "data" / "data.db")
    DB_TIMEOUT = 30.0  # 数据库连接超时时间（秒）

    @staticmethod
    def get_db_connection():
        """获取数据库连接，配置超时和WAL模式"""
        conn = sqlite3.connect(ReviewService.DB_FILE, timeout=ReviewService.DB_TIMEOUT)
        # 启用WAL模式以改善并发性能（如果失败也不影响，继续使用默认模式）
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
        except sqlite3.DatabaseError:
            # WAL模式启用失败，使用默认模式继续
            pass
        return conn

    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        import time
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                conn = ReviewService.get_db_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                            CREATE TABLE IF NOT EXISTS mr_review_log (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                project_name TEXT,
                                author TEXT,
                                source_branch TEXT,
                                target_branch TEXT,
                                updated_at INTEGER,
                                commit_messages TEXT,
                                score INTEGER,
                                url TEXT,
                                review_result TEXT,
                                additions INTEGER DEFAULT 0,
                                deletions INTEGER DEFAULT 0,
                                last_commit_id TEXT DEFAULT ''
                            )
                        ''')
                    cursor.execute('''
                            CREATE TABLE IF NOT EXISTS push_review_log (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                project_name TEXT,
                                author TEXT,
                                branch TEXT,
                                updated_at INTEGER,
                                commit_messages TEXT,
                                score INTEGER,
                                review_result TEXT,
                                additions INTEGER DEFAULT 0,
                                deletions INTEGER DEFAULT 0
                            )
                        ''')
                    # 确保旧版本的mr_review_log、push_review_log表添加additions、deletions列
                    tables = ["mr_review_log", "push_review_log"]
                    columns = ["additions", "deletions"]
                    for table in tables:
                        try:
                            cursor.execute(f"PRAGMA table_info({table})")
                            current_columns = [col[1] for col in cursor.fetchall()]
                            for column in columns:
                                if column not in current_columns:
                                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT 0")
                        except sqlite3.DatabaseError:
                            # 如果表不存在，跳过
                            pass

                    # 为旧版本的mr_review_log表添加last_commit_id字段
                    try:
                        mr_columns = [
                            {
                                "name": "last_commit_id",
                                "type": "TEXT",
                                "default": "''"
                            }
                        ]
                        cursor.execute(f"PRAGMA table_info('mr_review_log')")
                        current_columns = [col[1] for col in cursor.fetchall()]
                        for column in mr_columns:
                            if column.get("name") not in current_columns:
                                cursor.execute(f"ALTER TABLE mr_review_log ADD COLUMN {column.get('name')} {column.get('type')} "
                                               f"DEFAULT {column.get('default')}")
                    except sqlite3.DatabaseError:
                        # 如果表不存在，跳过
                        pass

                    conn.commit()
                    # 添加时间字段索引（默认查询就需要时间范围）
                    try:
                        conn.execute('CREATE INDEX IF NOT EXISTS idx_push_review_log_updated_at ON '
                                     'push_review_log (updated_at);')
                        conn.execute('CREATE INDEX IF NOT EXISTS idx_mr_review_log_updated_at ON mr_review_log (updated_at);')
                        conn.commit()
                    except sqlite3.DatabaseError:
                        # 索引创建失败不影响，继续
                        pass
                finally:
                    conn.close()
                # 成功则退出重试循环
                return
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if 'locked' in error_msg or 'database is locked' in error_msg:
                    if attempt < max_retries - 1:
                        print(f"Database is locked, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        print(f"Database initialization failed after {max_retries} attempts: {e}")
                        return
                else:
                    print(f"Database initialization failed: {e}")
                    return
            except sqlite3.DatabaseError as e:
                print(f"Database initialization failed: {e}")
                return
            except Exception as e:
                print(f"Unexpected error during database initialization: {e}")
                return

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO mr_review_log (project_name,author, source_branch, target_branch, 
                                updated_at, commit_messages, score, url,review_result, additions, deletions, 
                                last_commit_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.source_branch,
                                entity.target_branch, entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions,
                                entity.last_commit_id))
                conn.commit()
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                query = """
                            SELECT id, project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE 1=1
                            """
                params = []

                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)
                query += " ORDER BY updated_at DESC"
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def check_mr_last_commit_id_exists(project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM mr_review_log 
                    WHERE project_name = ? AND source_branch = ? AND target_branch = ? AND last_commit_id = ?
                ''', (project_name, source_branch, target_branch, last_commit_id))
                count = cursor.fetchone()[0]
                return count > 0
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error checking last_commit_id: {e}")
            return False

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions))
                conn.commit()
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                # 基础查询
                query = """
                    SELECT id, project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                # 动态添加 authors 条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                # 动态添加 updated_at_gte 条件
                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                # 动态添加 updated_at_lte 条件
                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)

                # 按 updated_at 降序排序
                query += " ORDER BY updated_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_mr_review_log_by_id(record_id: int) -> pd.DataFrame:
        """根据ID获取单条合并请求审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                query = """
                            SELECT id, project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE id = ?
                            """
                df = pd.read_sql_query(sql=query, con=conn, params=[record_id])
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review log by id: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_push_review_log_by_id(record_id: int) -> pd.DataFrame:
        """根据ID获取单条推送审核日志"""
        try:
            conn = ReviewService.get_db_connection()
            try:
                query = """
                            SELECT id, project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                            FROM push_review_log
                            WHERE id = ?
                            """
                df = pd.read_sql_query(sql=query, con=conn, params=[record_id])
                return df
            finally:
                conn.close()
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review log by id: {e}")
            return pd.DataFrame()


# Initialize database
ReviewService.init_db()
