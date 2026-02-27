"""
数据库连接池管理

提供高效的数据库连接复用，提升性能
"""
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional

from exceptions import ConnectionError, DatabaseError

logger = logging.getLogger(__name__)


class ConnectionPool:
    """SQLite 连接池"""

    def __init__(
        self,
        db_path: str,
        max_connections: int = 5,
        timeout: float = 30.0
    ):
        """
        初始化连接池

        Args:
            db_path: 数据库路径
            max_connections: 最大连接数
            timeout: 获取连接的超时时间（秒）
        """
        self.db_path = Path(db_path).expanduser()
        self.max_connections = max_connections
        self.timeout = timeout

        self._pool = []
        self._in_use = 0
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

        logger.info(f"初始化连接池: {self.db_path}, 最大连接数: {max_connections}")

        # 初始化连接
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        try:
            for i in range(self.max_connections):
                conn = self._create_connection()
                self._pool.append(conn)
            logger.info(f"连接池初始化完成: {len(self._pool)} 个连接")
        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise ConnectionError(f"连接池初始化失败: {e}")

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=self.timeout
            )
            # 启用 WAL 模式，提升并发性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            return conn
        except sqlite3.Error as e:
            logger.error(f"创建数据库连接失败: {e}")
            raise ConnectionError(f"创建数据库连接失败: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """
        从连接池获取连接

        Returns:
            数据库连接

        Raises:
            ConnectionError: 获取连接超时
        """
        with self._cv:
            # 等待直到有可用连接
            if not self._pool and self._in_use >= self.max_connections:
                if not self._cv.wait(self.timeout):
                    raise ConnectionError("获取连接超时")

            # 尝试从池中获取连接
            if self._pool:
                conn = self._pool.pop()
                self._in_use += 1
                logger.debug(f"从连接池获取连接，当前使用: {self._in_use}/{self.max_connections}")
                return conn

            # 如果没有可用连接，创建新连接
            try:
                conn = self._create_connection()
                self._in_use += 1
                logger.debug(f"创建新连接，当前使用: {self._in_use}/{self.max_connections}")
                return conn
            except Exception as e:
                logger.error(f"创建新连接失败: {e}")
                raise ConnectionError(f"创建新连接失败: {e}")

    def return_connection(self, conn: sqlite3.Connection):
        """
        归还连接到连接池

        Args:
            conn: 要归还的连接
        """
        with self._cv:
            try:
                # 检查连接是否有效
                conn.execute("SELECT 1")
                self._pool.append(conn)
                self._in_use -= 1
                logger.debug(f"归还连接到连接池，当前使用: {self._in_use}/{self.max_connections}")
                self._cv.notify()
            except sqlite3.Error:
                # 连接已失效，关闭它
                try:
                    conn.close()
                except:
                    pass
                self._in_use -= 1
                logger.debug(f"关闭失效连接，当前使用: {self._in_use}/{self.max_connections}")
                self._cv.notify()

    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            # 关闭池中的连接
            for conn in self._pool:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"关闭连接失败: {e}")

            self._pool.clear()
            self._in_use = 0

            logger.info("所有连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_all()


class ConnectionContext:
    """连接上下文管理器"""

    def __init__(self, pool: ConnectionPool):
        """
        初始化连接上下文

        Args:
            pool: 连接池实例
        """
        self.pool = pool
        self.conn = None

    def __enter__(self) -> sqlite3.Connection:
        """获取连接"""
        self.conn = self.pool.get_connection()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """归还连接"""
        if self.conn:
            if exc_type is not None:
                # 发生异常，回滚
                try:
                    self.conn.rollback()
                except:
                    pass
            self.pool.return_connection(self.conn)
            self.conn = None

        # 不抑制异常
        return False