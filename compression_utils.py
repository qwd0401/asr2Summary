from functools import wraps
import gzip
import hashlib
import json
import logging
import lzma
from threading import Lock
import time
from typing import Any, ClassVar, Dict, List, Optional, Tuple
import zlib

logger = logging.getLogger(__name__)


class TextCompressor:
    """
    文本压缩工具类
    支持多种压缩算法，自动选择最优压缩方案
    """

    # 压缩算法配置
    ALGORITHMS: ClassVar[dict] = {
        "zlib": {
            "compress": lambda data: zlib.compress(data.encode("utf-8"), level=6),
            "decompress": lambda data: zlib.decompress(data).decode("utf-8"),
            "min_size": 100,  # 最小压缩文本长度
        },
        "gzip": {
            "compress": lambda data: gzip.compress(data.encode("utf-8"), compresslevel=6),
            "decompress": lambda data: gzip.decompress(data).decode("utf-8"),
            "min_size": 200,
        },
        "lzma": {
            "compress": lambda data: lzma.compress(data.encode("utf-8"), preset=3),
            "decompress": lambda data: lzma.decompress(data).decode("utf-8"),
            "min_size": 500,  # LZMA适合较大文本
        },
    }

    @classmethod
    def compress_text(cls, text: str, algorithm: str = "auto") -> Tuple[bytes, str]:
        """
        压缩文本

        Args:
            text: 要压缩的文本
            algorithm: 压缩算法 ('auto', 'zlib', 'gzip', 'lzma')

        Returns:
            (compressed_data, used_algorithm)
        """
        if not text or len(text) < 50:
            # 短文本不压缩
            return text.encode("utf-8"), "none"

        if algorithm == "auto":
            algorithm = cls._select_best_algorithm(text)

        if algorithm == "none" or algorithm not in cls.ALGORITHMS:
            return text.encode("utf-8"), "none"

        try:
            compressed_data = cls.ALGORITHMS[algorithm]["compress"](text)

            # 检查压缩效果
            original_size = len(text.encode("utf-8"))
            compressed_size = len(compressed_data)

            if compressed_size >= original_size * 0.9:  # 压缩率不足10%
                logger.debug(f"压缩效果不佳，使用原文本: {compressed_size}/{original_size}")
                return text.encode("utf-8"), "none"

            logger.debug(f"文本压缩成功: {original_size} -> {compressed_size} ({algorithm})")
            return compressed_data, algorithm

        except Exception as e:
            logger.warning(f"文本压缩失败，使用原文本: {e}")
            return text.encode("utf-8"), "none"

    @classmethod
    def decompress_text(cls, compressed_data: bytes, algorithm: str) -> str:
        """
        解压缩文本

        Args:
            compressed_data: 压缩数据
            algorithm: 压缩算法

        Returns:
            解压缩后的文本
        """
        if algorithm == "none" or algorithm not in cls.ALGORITHMS:
            return compressed_data.decode("utf-8")

        try:
            return cls.ALGORITHMS[algorithm]["decompress"](compressed_data)
        except Exception as e:
            logger.error(f"文本解压缩失败: {e}")
            # 尝试作为未压缩文本处理
            try:
                return compressed_data.decode("utf-8")
            except Exception:
                return "[解压缩失败]"

    @classmethod
    def _select_best_algorithm(cls, text: str) -> str:
        """
        根据文本特征选择最佳压缩算法
        """
        text_length = len(text)

        # 根据文本长度选择算法
        if text_length < 100:
            return "none"
        elif text_length < 500:
            return "zlib"
        elif text_length < 2000:
            return "gzip"
        else:
            return "lzma"

    @classmethod
    def get_compression_stats(cls, original_text: str, compressed_data: bytes, algorithm: str) -> Dict[str, Any]:
        """
        获取压缩统计信息
        """
        original_size = len(original_text.encode("utf-8"))
        compressed_size = len(compressed_data)

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compressed_size / original_size if original_size > 0 else 1.0,
            "space_saved": original_size - compressed_size,
            "space_saved_percent": (1 - compressed_size / original_size) * 100 if original_size > 0 else 0,
            "algorithm": algorithm,
        }


class QueryCache:
    """
    查询缓存管理器
    提供内存缓存和持久化缓存功能
    """

    def __init__(self, max_memory_size: int = 1000, cache_ttl: int = 3600):
        self.max_memory_size = max_memory_size
        self.cache_ttl = cache_ttl
        self.memory_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._lock = Lock()

    def get_cache_key(self, query: str, params: Optional[Dict] = None) -> str:
        """
        生成缓存键
        """
        cache_data = {"query": query, "params": params or {}}
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[Any]:
        """
        从缓存获取数据
        """
        with self._lock:
            if cache_key in self.memory_cache:
                cache_entry = self.memory_cache[cache_key]

                # 检查是否过期
                if time.time() - cache_entry["timestamp"] > self.cache_ttl:
                    del self.memory_cache[cache_key]
                    self.cache_stats["misses"] += 1
                    return None

                # 更新访问时间
                cache_entry["last_access"] = time.time()
                self.cache_stats["hits"] += 1
                return cache_entry["data"]

            self.cache_stats["misses"] += 1
            return None

    def set(self, cache_key: str, data: Any) -> None:
        """
        设置缓存数据
        """
        with self._lock:
            # 检查缓存大小限制
            if len(self.memory_cache) >= self.max_memory_size:
                self._evict_oldest()

            self.memory_cache[cache_key] = {"data": data, "timestamp": time.time(), "last_access": time.time()}

    def _evict_oldest(self) -> None:
        """
        淘汰最旧的缓存项
        """
        if not self.memory_cache:
            return

        # 找到最旧的缓存项
        oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k]["last_access"])

        del self.memory_cache[oldest_key]
        self.cache_stats["evictions"] += 1

    def clear(self) -> None:
        """
        清空缓存
        """
        with self._lock:
            self.memory_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        """
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "memory_cache_size": len(self.memory_cache),
            "max_memory_size": self.max_memory_size,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "evictions": self.cache_stats["evictions"],
            "hit_rate": hit_rate,
            "cache_ttl": self.cache_ttl,
        }


def cached_query(cache_instance: QueryCache, ttl: Optional[int] = None):
    """
    查询缓存装饰器
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_instance.get_cache_key(f"{func.__name__}", {"args": args, "kwargs": kwargs})

            # 尝试从缓存获取
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_result

            # 执行查询
            result = func(*args, **kwargs)

            # 存储到缓存
            cache_instance.set(cache_key, result)
            logger.debug(f"缓存存储: {func.__name__}")

            return result

        return wrapper

    return decorator


class DatabaseOptimizer:
    """
    数据库优化工具
    提供查询优化、索引建议、性能监控等功能
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.query_stats = {}
        self._lock = Lock()

    def analyze_query_performance(self, query: str, execution_time: float, result_count: int = 0) -> None:
        """
        分析查询性能
        """
        with self._lock:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = {
                    "query": query,
                    "executions": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "max_time": 0,
                    "min_time": float("inf"),
                    "total_results": 0,
                }

            stats = self.query_stats[query_hash]
            stats["executions"] += 1
            stats["total_time"] += execution_time
            stats["avg_time"] = stats["total_time"] / stats["executions"]
            stats["max_time"] = max(stats["max_time"], execution_time)
            stats["min_time"] = min(stats["min_time"], execution_time)
            stats["total_results"] += result_count

    def get_slow_queries(self, threshold: float = 0.1) -> List[Dict[str, Any]]:
        """
        获取慢查询列表
        """
        slow_queries = []

        for query_hash, stats in self.query_stats.items():
            if stats["avg_time"] > threshold:
                slow_queries.append(
                    {
                        "query_hash": query_hash,
                        "query": stats["query"][:100] + "..." if len(stats["query"]) > 100 else stats["query"],
                        "avg_time": stats["avg_time"],
                        "max_time": stats["max_time"],
                        "executions": stats["executions"],
                        "total_time": stats["total_time"],
                    }
                )

        return sorted(slow_queries, key=lambda x: x["avg_time"], reverse=True)

    def suggest_indexes(self) -> List[str]:
        """
        基于查询模式建议索引
        """
        suggestions = []

        # 分析查询模式
        for stats in self.query_stats.values():
            query = stats["query"].lower()

            # 检查WHERE子句
            if "where" in query and stats["executions"] > 10:
                # 简单的索引建议逻辑
                if "created_at" in query:
                    suggestions.append("CREATE INDEX IF NOT EXISTS idx_created_at ON table_name(created_at);")
                if "audio_file_id" in query:
                    suggestions.append("CREATE INDEX IF NOT EXISTS idx_audio_file_id ON transcriptions(audio_file_id);")
                if "transcription_id" in query:
                    suggestions.append(
                        "CREATE INDEX IF NOT EXISTS idx_transcription_id ON meeting_summaries(transcription_id);"
                    )

        return list(set(suggestions))  # 去重

    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        """
        if not self.query_stats:
            return {"message": "暂无查询统计数据"}

        total_queries = sum(stats["executions"] for stats in self.query_stats.values())
        total_time = sum(stats["total_time"] for stats in self.query_stats.values())
        avg_query_time = total_time / total_queries if total_queries > 0 else 0

        return {
            "total_queries": total_queries,
            "unique_queries": len(self.query_stats),
            "total_execution_time": total_time,
            "average_query_time": avg_query_time,
            "slow_queries": self.get_slow_queries(),
            "index_suggestions": self.suggest_indexes(),
        }


def performance_monitor(optimizer: DatabaseOptimizer):
    """
    性能监控装饰器
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 尝试获取查询信息
                query = None
                result_count = 0

                if hasattr(func, "__name__") and "query" in func.__name__.lower():
                    # 如果是查询函数，尝试获取查询语句
                    if args and isinstance(args[0], str):
                        query = args[0]
                    elif "query" in kwargs:
                        query = kwargs["query"]

                if isinstance(result, (list, tuple)):
                    result_count = len(result)
                elif isinstance(result, dict) and "count" in result:
                    result_count = result["count"]

                if query:
                    optimizer.analyze_query_performance(query, execution_time, result_count)

                # 记录慢查询
                if execution_time > 0.5:  # 超过500ms的查询
                    logger.warning(f"慢查询检测: {func.__name__} 耗时 {execution_time:.3f}s")

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"查询异常: {func.__name__} 耗时 {execution_time:.3f}s, 错误: {e}")
                raise

        return wrapper

    return decorator


class CompressionStats:
    """
    压缩统计管理器
    """

    def __init__(self):
        self.stats = {
            "total_compressed": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "compression_by_algorithm": {},
            "compression_by_type": {},
        }
        self._lock = Lock()

    def record_compression(
        self, original_size: int, compressed_size: int, algorithm: str, data_type: str = "text"
    ) -> None:
        """
        记录压缩统计
        """
        with self._lock:
            self.stats["total_compressed"] += 1
            self.stats["total_original_size"] += original_size
            self.stats["total_compressed_size"] += compressed_size

            # 按算法统计
            if algorithm not in self.stats["compression_by_algorithm"]:
                self.stats["compression_by_algorithm"][algorithm] = {
                    "count": 0,
                    "original_size": 0,
                    "compressed_size": 0,
                }

            alg_stats = self.stats["compression_by_algorithm"][algorithm]
            alg_stats["count"] += 1
            alg_stats["original_size"] += original_size
            alg_stats["compressed_size"] += compressed_size

            # 按数据类型统计
            if data_type not in self.stats["compression_by_type"]:
                self.stats["compression_by_type"][data_type] = {"count": 0, "original_size": 0, "compressed_size": 0}

            type_stats = self.stats["compression_by_type"][data_type]
            type_stats["count"] += 1
            type_stats["original_size"] += original_size
            type_stats["compressed_size"] += compressed_size

    def get_summary(self) -> Dict[str, Any]:
        """
        获取压缩统计摘要
        """
        if self.stats["total_compressed"] == 0:
            return {"message": "暂无压缩统计数据"}

        overall_ratio = (
            self.stats["total_compressed_size"] / self.stats["total_original_size"]
            if self.stats["total_original_size"] > 0
            else 1.0
        )

        space_saved = self.stats["total_original_size"] - self.stats["total_compressed_size"]
        space_saved_percent = (1 - overall_ratio) * 100

        return {
            "total_items_compressed": self.stats["total_compressed"],
            "total_original_size_mb": self.stats["total_original_size"] / (1024 * 1024),
            "total_compressed_size_mb": self.stats["total_compressed_size"] / (1024 * 1024),
            "overall_compression_ratio": overall_ratio,
            "space_saved_mb": space_saved / (1024 * 1024),
            "space_saved_percent": space_saved_percent,
            "compression_by_algorithm": self.stats["compression_by_algorithm"],
            "compression_by_type": self.stats["compression_by_type"],
        }


# 全局实例
text_compressor = TextCompressor()
query_cache = QueryCache(max_memory_size=500, cache_ttl=1800)  # 30分钟TTL
compression_stats = CompressionStats()


# 导出的便捷函数
def compress_text(text: str, algorithm: str = "auto") -> Tuple[bytes, str]:
    """压缩文本的便捷函数"""
    return text_compressor.compress_text(text, algorithm)


def decompress_text(compressed_data: bytes, algorithm: str) -> str:
    """解压缩文本的便捷函数"""
    return text_compressor.decompress_text(compressed_data, algorithm)


def get_compression_stats(original_text: str, compressed_data: bytes, algorithm: str) -> Dict[str, Any]:
    """获取压缩统计的便捷函数"""
    return text_compressor.get_compression_stats(original_text, compressed_data, algorithm)


if __name__ == "__main__":
    # 测试压缩功能
    test_text = "这是一个测试文本，用于验证压缩功能的效果。" * 50

    print(f"原始文本长度: {len(test_text)}")

    for algorithm in ["zlib", "gzip", "lzma"]:
        compressed_data, used_algorithm = compress_text(test_text, algorithm)
        decompressed_text = decompress_text(compressed_data, used_algorithm)

        stats = get_compression_stats(test_text, compressed_data, used_algorithm)

        print(f"\n算法: {algorithm} (实际使用: {used_algorithm})")
        print(f"压缩后长度: {len(compressed_data)}")
        print(f"压缩率: {stats['compression_ratio']:.3f}")
        print(f"节省空间: {stats['space_saved_percent']:.1f}%")
        print(f"解压缩正确: {decompressed_text == test_text}")
