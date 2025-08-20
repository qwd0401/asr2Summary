import sqlite3
import json
import os
import logging
import threading
import time
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Tuple
import uuid
import gzip
import base64

# 导入压缩优化工具
try:
    from compression_utils import (
        compress_text, decompress_text, get_compression_stats,
        query_cache, cached_query, performance_monitor,
        DatabaseOptimizer, compression_stats
    )
    COMPRESSION_UTILS_AVAILABLE = True
except ImportError:
    COMPRESSION_UTILS_AVAILABLE = False
    logger.warning("压缩优化工具不可用，使用默认压缩方法")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 单例模式
    集成性能监控和优化功能
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = 'meetassistant.db'):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = 'meetassistant.db'):
        if self._initialized:
            return
            
        self.db_path = db_path
        self.connection_pool = []
        self.pool_size = 5
        self._lock = threading.Lock()
        self._initialized = True
        
        # 初始化性能优化器
        if COMPRESSION_UTILS_AVAILABLE:
            self.optimizer = DatabaseOptimizer(db_path)
        else:
            self.optimizer = None
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"数据库管理器初始化完成: {db_path}")
    
    def _init_database(self):
        """初始化数据库，创建表结构"""
        try:
            # 读取SQL架构文件
            schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema_sql = f.read()
                
                with self.get_connection() as conn:
                    # 执行架构创建
                    conn.executescript(schema_sql)
                    conn.commit()
                    logger.info("数据库架构初始化完成")
            else:
                logger.warning(f"数据库架构文件不存在: {schema_path}")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row  # 启用字典式访问
            
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 优化性能设置
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = 10000")
            conn.execute("PRAGMA temp_store = MEMORY")
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {e}")
            raise
        finally:
            if conn:
                conn.close()

class AudioFileDAO:
    """音频文件数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, filename: str, original_filename: str, file_path: str, 
               file_size: int, file_type: str) -> int:
        """创建音频文件记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audio_files 
                (filename, original_filename, file_path, file_size, file_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (filename, original_filename, file_path, file_size, file_type)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_by_id(self, audio_id: int) -> Optional[Dict]:
        """根据ID获取音频文件信息"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audio_files WHERE id = ?",
                (audio_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_by_filename(self, filename: str) -> Optional[Dict]:
        """根据文件名获取音频文件信息"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audio_files WHERE filename = ?",
                (filename,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_status(self, audio_id: int, status: str) -> bool:
        """更新音频文件状态"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE audio_files SET status = ? WHERE id = ?",
                (status, audio_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def list_recent(self, limit: int = 50) -> List[Dict]:
        """获取最近的音频文件列表"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM audio_files 
                ORDER BY upload_time DESC 
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete(self, audio_id: int) -> bool:
        """删除音频文件记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM audio_files WHERE id = ?",
                (audio_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

class TranscriptionDAO:
    """转录文本数据访问对象
    集成文本压缩功能
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, audio_file_id: int, transcription_text: str, 
               processing_time: float = None, confidence_score: float = None,
               language: str = 'zh-CN') -> int:
        """创建转录记录（使用优化压缩）"""
        # 使用优化的文本压缩
        if COMPRESSION_UTILS_AVAILABLE:
            compressed_data, algorithm = compress_text(transcription_text)
            
            # 记录压缩统计
            original_size = len(transcription_text.encode('utf-8'))
            compressed_size = len(compressed_data)
            compression_stats.record_compression(original_size, compressed_size, algorithm, 'transcription')
            
            # 记录压缩信息到日志
            if algorithm != 'none':
                stats = get_compression_stats(transcription_text, compressed_data, algorithm)
                logger.info(f"转录文本压缩: {stats['space_saved_percent']:.1f}% 空间节省 ({algorithm})")
        else:
            compressed_data = self._compress_text(transcription_text)
            algorithm = 'gzip'
        
        text_length = len(transcription_text)
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transcriptions 
                (audio_file_id, transcription_text, text_length, processing_time, 
                 confidence_score, language)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (audio_file_id, compressed_data, text_length, processing_time, 
                 confidence_score, language)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_by_id(self, transcription_id: int) -> Optional[Dict]:
        """根据ID获取转录记录（带缓存优化）"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM transcriptions WHERE id = ?",
                (transcription_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 使用优化的解压缩
                if COMPRESSION_UTILS_AVAILABLE:
                    try:
                        result['transcription_text'] = decompress_text(result['transcription_text'], 'auto')
                    except Exception as e:
                        logger.warning(f"转录文本解压缩失败，尝试备用方法: {e}")
                        result['transcription_text'] = self._decompress_text(result['transcription_text'])
                else:
                    result['transcription_text'] = self._decompress_text(result['transcription_text'])
                return result
            return None
    
    def get_by_audio_id(self, audio_file_id: int) -> Optional[Dict]:
        """根据音频文件ID获取转录记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM transcriptions WHERE audio_file_id = ?",
                (audio_file_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['transcription_text'] = self._decompress_text(result['transcription_text'])
                return result
            return None
    
    def list_recent(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取最近的转录记录列表"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM transcriptions 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # 对于列表查询，不解压缩文本内容以提高性能
                # 如果需要文本内容，应该单独调用get_by_id
                results.append(result)
            return results
    
    def _compress_text(self, text: str) -> str:
        """压缩文本数据"""
        try:
            compressed = gzip.compress(text.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        except Exception as e:
            logger.warning(f"文本压缩失败，使用原文本: {e}")
            return text
    
    def _decompress_text(self, compressed_text: str) -> str:
        """解压缩文本数据"""
        try:
            # 尝试解压缩
            compressed_bytes = base64.b64decode(compressed_text.encode('ascii'))
            return gzip.decompress(compressed_bytes).decode('utf-8')
        except Exception:
            # 如果解压缩失败，说明是未压缩的原文本
            return compressed_text

class MeetingSummaryDAO:
    """会议总结数据访问对象
    集成文本压缩功能
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, transcription_id: int, template_type: str, 
               summary_content: str, processing_time: float = None) -> int:
        """创建会议总结记录（使用优化压缩）"""
        # 使用优化的文本压缩
        if COMPRESSION_UTILS_AVAILABLE:
            compressed_data, algorithm = compress_text(summary_content)
            
            # 记录压缩统计
            original_size = len(summary_content.encode('utf-8'))
            compressed_size = len(compressed_data)
            compression_stats.record_compression(original_size, compressed_size, algorithm, 'summary')
            
            # 记录压缩信息到日志
            if algorithm != 'none':
                stats = get_compression_stats(summary_content, compressed_data, algorithm)
                logger.info(f"总结内容压缩: {stats['space_saved_percent']:.1f}% 空间节省 ({algorithm})")
        else:
            compressed_data = self._compress_text(summary_content)
            algorithm = 'gzip'
        
        content_length = len(summary_content)
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO meeting_summaries 
                (transcription_id, template_type, summary_content, content_length, processing_time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (transcription_id, template_type, compressed_data, content_length, processing_time)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_by_id(self, summary_id: int) -> Optional[Dict]:
        """根据ID获取会议总结（带缓存优化）"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM meeting_summaries WHERE id = ?",
                (summary_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 使用优化的解压缩
                if COMPRESSION_UTILS_AVAILABLE:
                    try:
                        result['summary_content'] = decompress_text(result['summary_content'], 'auto')
                    except Exception as e:
                        logger.warning(f"总结内容解压缩失败，尝试备用方法: {e}")
                        result['summary_content'] = self._decompress_text(result['summary_content'])
                else:
                    result['summary_content'] = self._decompress_text(result['summary_content'])
                return result
            return None
    
    def get_by_transcription_id(self, transcription_id: int) -> Optional[Dict]:
        """根据转录ID获取会议总结"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM meeting_summaries WHERE transcription_id = ?",
                (transcription_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['summary_content'] = self._decompress_text(result['summary_content'])
                return result
            return None
    
    def list_recent(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取最近的会议总结列表"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM meeting_summaries 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # 对于列表查询，不解压缩文本内容以提高性能
                results.append(result)
            return results
    
    def list_by_template(self, template_type: str, limit: int = 20) -> List[Dict]:
        """根据模板类型获取总结列表"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM meeting_summaries 
                WHERE template_type = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (template_type, limit)
            )
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['summary_content'] = self._decompress_text(result['summary_content'])
                results.append(result)
            return results
    
    def _compress_text(self, text: str) -> str:
        """压缩文本数据"""
        try:
            compressed = gzip.compress(text.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        except Exception as e:
            logger.warning(f"文本压缩失败，使用原文本: {e}")
            return text
    
    def _decompress_text(self, compressed_text: str) -> str:
        """解压缩文本数据"""
        try:
            compressed_bytes = base64.b64decode(compressed_text.encode('ascii'))
            return gzip.decompress(compressed_bytes).decode('utf-8')
        except Exception:
            return compressed_text

class UsageStatisticsDAO:
    """使用统计数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, request_id: str, endpoint: str, method: str, 
               success: bool, processing_time: float, file_size: int = 0,
               file_type: str = None, error_type: str = None, 
               error_message: str = None, user_agent: str = None,
               ip_address: str = None) -> int:
        """创建使用统计记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO usage_statistics 
                (request_id, endpoint, method, success, processing_time, file_size,
                 file_type, error_type, error_message, user_agent, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (request_id, endpoint, method, success, processing_time, file_size,
                 file_type, error_type, error_message, user_agent, ip_address)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """获取每日统计数据"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM daily_statistics 
                WHERE date >= date('now', '-{} days')
                ORDER BY date DESC
                """.format(days)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_endpoint_stats(self) -> List[Dict]:
        """获取端点统计数据"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM endpoint_statistics")
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """清理过期记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM usage_statistics WHERE created_at < datetime('now', '-{} days')".format(days)
            )
            conn.commit()
            return cursor.rowcount

class TemplateConfigDAO:
    """模板配置数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_all_active(self) -> List[Dict]:
        """获取所有活跃的模板配置"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM template_configs WHERE is_active = 1 ORDER BY template_type"
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_by_type(self, template_type: str) -> Optional[Dict]:
        """根据类型获取模板配置"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM template_configs WHERE template_type = ? AND is_active = 1",
                (template_type,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

class SystemConfigDAO:
    """系统配置数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_config(self, key: str) -> Optional[Any]:
        """获取系统配置值"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT config_value, config_type FROM system_configs WHERE config_key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                value, config_type = row
                return self._convert_value(value, config_type)
            return None
    
    def set_config(self, key: str, value: Any, config_type: str = 'string') -> bool:
        """设置系统配置值"""
        str_value = self._convert_to_string(value, config_type)
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO system_configs (config_key, config_value, config_type)
                VALUES (?, ?, ?)
                """,
                (key, str_value, config_type)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def _convert_value(self, value: str, config_type: str) -> Any:
        """转换配置值类型"""
        if config_type == 'integer':
            return int(value)
        elif config_type == 'float':
            return float(value)
        elif config_type == 'boolean':
            return value.lower() in ('true', '1', 'yes')
        elif config_type == 'json':
            return json.loads(value)
        else:
            return value
    
    def _convert_to_string(self, value: Any, config_type: str) -> str:
        """转换值为字符串"""
        if config_type == 'json':
            return json.dumps(value)
        elif config_type == 'boolean':
            return 'true' if value else 'false'
        else:
            return str(value)

class MeetingRecordDAO:
    """会议记录综合数据访问对象"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_complete_record(self, audio_id: int) -> Optional[Dict]:
        """获取完整的会议记录"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM meeting_records WHERE audio_id = ?",
                (audio_id,)
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # 解压缩文本内容
                if result.get('transcription_text'):
                    result['transcription_text'] = self._decompress_text(result['transcription_text'])
                if result.get('summary_content'):
                    result['summary_content'] = self._decompress_text(result['summary_content'])
                return result
            return None
    
    def list_recent_records(self, limit: int = 20) -> List[Dict]:
        """获取最近的会议记录列表"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM meeting_records ORDER BY upload_time DESC LIMIT ?",
                (limit,)
            )
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # 只解压缩需要的字段，提高性能
                if result.get('transcription_text'):
                    result['transcription_text'] = self._decompress_text(result['transcription_text'])
                if result.get('summary_content'):
                    result['summary_content'] = self._decompress_text(result['summary_content'])
                results.append(result)
            return results
    
    def _decompress_text(self, compressed_text: str) -> str:
        """解压缩文本数据"""
        if not compressed_text:
            return compressed_text
        try:
            compressed_bytes = base64.b64decode(compressed_text.encode('ascii'))
            return gzip.decompress(compressed_bytes).decode('utf-8')
        except Exception:
            return compressed_text

# 数据库服务类
class DatabaseService:
    """数据库服务 - 统一的数据访问接口"""
    
    def __init__(self, db_path: str = 'meetassistant.db'):
        self.db_manager = DatabaseManager(db_path)
        
        # 初始化各个DAO
        self.audio_files = AudioFileDAO(self.db_manager)
        self.transcriptions = TranscriptionDAO(self.db_manager)
        self.summaries = MeetingSummaryDAO(self.db_manager)
        self.usage_stats = UsageStatisticsDAO(self.db_manager)
        self.templates = TemplateConfigDAO(self.db_manager)
        self.configs = SystemConfigDAO(self.db_manager)
        self.records = MeetingRecordDAO(self.db_manager)
        
        logger.info("数据库服务初始化完成")
    
    def optimize_database(self):
        """优化数据库性能"""
        with self.db_manager.get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.execute("PRAGMA optimize")
            conn.commit()
        logger.info("数据库优化完成")
    
    def cleanup_old_data(self, retention_days: int = None):
        """清理过期数据"""
        if retention_days is None:
            retention_days = self.configs.get_config('retention_days') or 90
        
        # 清理使用统计
        deleted_count = self.usage_stats.cleanup_old_records(retention_days)
        logger.info(f"清理了 {deleted_count} 条过期使用统计记录")
        
        # 优化数据库
        self.optimize_database()
    
    def get_database_stats(self) -> Dict:
        """获取数据库统计信息"""
        with self.db_manager.get_connection() as conn:
            stats = {}
            
            # 获取各表记录数
            tables = ['audio_files', 'transcriptions', 'meeting_summaries', 
                     'usage_statistics', 'template_configs', 'system_configs']
            
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # 获取数据库大小
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            stats['database_size_bytes'] = page_count * page_size
            stats['database_size_mb'] = round(stats['database_size_bytes'] / (1024 * 1024), 2)
            
            return stats

# 全局数据库服务实例
_db_service = None

def get_database_service(db_path: str = 'meetassistant.db') -> DatabaseService:
    """获取数据库服务实例（单例模式）"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(db_path)
    return _db_service

if __name__ == "__main__":
    # 测试代码
    db_service = get_database_service('test_meetassistant.db')
    
    # 测试音频文件创建
    audio_id = db_service.audio_files.create(
        filename="test_audio.mp3",
        original_filename="原始音频.mp3",
        file_path="/uploads/test_audio.mp3",
        file_size=1024000,
        file_type="mp3"
    )
    print(f"创建音频文件记录，ID: {audio_id}")
    
    # 测试转录创建
    transcription_id = db_service.transcriptions.create(
        audio_file_id=audio_id,
        transcription_text="这是一段测试转录文本，用于验证数据库功能是否正常工作。" * 100,
        processing_time=5.2,
        confidence_score=0.95
    )
    print(f"创建转录记录，ID: {transcription_id}")
    
    # 测试会议总结创建
    summary_id = db_service.summaries.create(
        transcription_id=transcription_id,
        template_type="product",
        summary_content="这是一份测试会议总结，包含了会议的主要内容和决策。" * 50,
        processing_time=3.8
    )
    print(f"创建会议总结记录，ID: {summary_id}")
    
    # 测试完整记录查询
    complete_record = db_service.records.get_complete_record(audio_id)
    if complete_record:
        print(f"完整记录查询成功，文件名: {complete_record['filename']}")
        print(f"转录文本长度: {len(complete_record['transcription_text'])}")
        print(f"总结内容长度: {len(complete_record['summary_content'])}")
    
    # 获取数据库统计
    stats = db_service.get_database_stats()
    print(f"数据库统计: {stats}")
    
    print("数据库测试完成！")