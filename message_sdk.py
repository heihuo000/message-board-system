#!/usr/bin/env python3
"""
Message Board SDK - AI CLI 通信工具包

独立版本，不依赖 src 模块
"""
import sqlite3
import uuid
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 导入异常定义
from exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    MessageNotFoundError,
    TimeoutError as MessageTimeoutError,
    ValidationError,
    ConfigurationError
)

# 导入连接池
from connection_pool import ConnectionPool, ConnectionContext

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path('~/.message_board/sdk.log').expanduser()),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MessageBoardClient:
    """留言簿客户端 - 为 AI CLI 提供通信接口"""
    
    def __init__(
        self,
        client_id: str,
        db_path: str = "~/.message_board/board.db",
        enable_logging: bool = True,
        enable_pool: bool = True,
        pool_size: int = 5
    ):
        """
        初始化客户端

        Args:
            client_id: 客户端唯一标识
            db_path: 数据库路径
            enable_logging: 是否启用日志
            enable_pool: 是否启用连接池
            pool_size: 连接池大小
        """
        self.client_id = client_id
        self.db_path = Path(db_path).expanduser()
        self.enable_logging = enable_logging
        self.enable_pool = enable_pool
        self.pool_size = pool_size

        logger.info(f"初始化客户端: {client_id}")

        # 初始化缓存
        self._cache = {}
        self._cache_max_size = 100
        self._cache_hits = 0
        self._cache_misses = 0

        # 初始化性能指标
        self._metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'total_response_time': 0,
            'start_time': time.time()
        }

        # 初始化连接池
        if self.enable_pool:
            try:
                self._pool = ConnectionPool(str(self.db_path), max_connections=pool_size)
                logger.info(f"连接池已启用，大小: {pool_size}")
            except Exception as e:
                logger.error(f"连接池初始化失败，降级为直连模式: {e}")
                self.enable_pool = False
        else:
            self._pool = None

        # 确保数据库存在
        if not self.db_path.exists():
            logger.info("数据库不存在，创建新数据库")
            try:
                self._init_db()
                logger.info("数据库创建成功")
            except Exception as e:
                logger.error(f"数据库创建失败: {e}")
                raise DatabaseError(f"数据库创建失败: {e}")
    
    def _init_db(self):
        """初始化数据库"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    read INTEGER DEFAULT 0,
                    reply_to TEXT,
                    priority TEXT DEFAULT 'normal',
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)")
            
            conn.commit()
            conn.close()
            
            logger.debug("数据库表和索引创建成功")
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            raise DatabaseError(f"数据库初始化失败: {e}")
    
    def send(
        self,
        content: str,
        priority: str = "normal",
        reply_to: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        发送消息

        Args:
            content: 消息内容
            priority: 优先级 (normal/high/urgent)
            reply_to: 回复的消息 ID
            metadata: 额外元数据

        Returns:
            消息 ID
        """
        if not content or not content.strip():
            error_msg = "消息内容不能为空"
            logger.error(error_msg)
            raise ValidationError(error_msg)

        valid_priorities = ['normal', 'high', 'urgent']
        if priority not in valid_priorities:
            error_msg = f"无效的优先级: {priority}，必须是 {valid_priorities} 之一"
            logger.error(error_msg)
            raise ValidationError(error_msg)

        try:
            start_time = time.time()

            if self.enable_logging:
                logger.info(f"发送消息: {content[:50]}{'...' if len(content) > 50 else ''}")

            message_id = str(uuid.uuid4())
            timestamp = int(time.time())
            metadata_json = json.dumps(metadata) if metadata else None

            if self.enable_pool:
                # 使用连接池
                with ConnectionContext(self._pool) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (message_id, self.client_id, content, timestamp, 0, reply_to, priority, metadata_json))
                    conn.commit()
            else:
                # 直连模式
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (message_id, self.client_id, content, timestamp, 0, reply_to, priority, metadata_json))
                conn.commit()
                conn.close()

            # 记录指标
            elapsed = time.time() - start_time
            self._metrics['messages_sent'] += 1
            self._metrics['total_response_time'] += elapsed

            if self.enable_logging:
                logger.info(f"消息发送成功: {message_id}，耗时: {elapsed:.3f}秒")

            return message_id

        except sqlite3.Error as e:
            error_msg = f"发送消息失败: {e}"
            logger.error(error_msg)
            self._metrics['errors'] += 1
            raise DatabaseError(error_msg)
    
    def read_unread(self, limit: int = 10) -> List[Dict]:
        """
        读取未读消息

        Args:
            limit: 限制返回数量

        Returns:
            消息列表
        """
        try:
            start_time = time.time()

            if self.enable_logging:
                logger.debug(f"读取未读消息，限制: {limit}")

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, sender, content, timestamp, priority, reply_to, metadata
                FROM messages
                WHERE read = 0 AND sender != ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (self.client_id, limit))

            messages = [
                {
                    'id': row['id'],
                    'sender': row['sender'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'priority': row['priority'] or 'normal',
                    'reply_to': row['reply_to'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            # 记录指标
            elapsed = time.time() - start_time
            self._metrics['messages_received'] += len(messages)
            self._metrics['total_response_time'] += elapsed

            if self.enable_logging:
                logger.info(f"读取到 {len(messages)} 条未读消息，耗时: {elapsed:.3f}秒")

            return messages

        except sqlite3.Error as e:
            error_msg = f"读取未读消息失败: {e}"
            logger.error(error_msg)
            self._metrics['errors'] += 1
            raise DatabaseError(error_msg)
    
    def read_all(self, limit: int = 20) -> List[Dict]:
        """
        读取所有消息（最近的）

        Args:
            limit: 限制返回数量

        Returns:
            消息列表
        """
        try:
            if self.enable_logging:
                logger.debug(f"读取所有消息，限制: {limit}")

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, sender, content, timestamp, priority, reply_to, read
                FROM messages
                WHERE sender != ? OR sender = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.client_id, self.client_id, limit))

            messages = [
                {
                    'id': row['id'],
                    'sender': row['sender'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'priority': row['priority'] or 'normal',
                    'reply_to': row['reply_to'],
                    'read': bool(row['read'])
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            if self.enable_logging:
                logger.info(f"读取到 {len(messages)} 条消息")

            return messages

        except sqlite3.Error as e:
            error_msg = f"读取消息失败: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def send_batch(self, messages: List[Dict]) -> List[str]:
        """
        批量发送消息

        Args:
            messages: 消息列表，每个消息包含 content, priority, reply_to, metadata

        Returns:
            消息 ID 列表

        Raises:
            ValidationError: 消息格式无效
            DatabaseError: 数据库操作失败
        """
        if not messages:
            logger.warning("批量发送空消息列表")
            return []

        try:
            if self.enable_logging:
                logger.info(f"批量发送 {len(messages)} 条消息")

            message_ids = []
            timestamp = int(time.time())

            if self.enable_pool:
                # 使用连接池批量插入
                with ConnectionContext(self._pool) as conn:
                    cursor = conn.cursor()

                    for msg in messages:
                        # 验证消息格式
                        if not isinstance(msg, dict) or 'content' not in msg:
                            raise ValidationError(f"无效的消息格式: {msg}")

                        content = msg.get('content', '')
                        priority = msg.get('priority', 'normal')
                        reply_to = msg.get('reply_to')
                        metadata = msg.get('metadata')

                        if not content or not content.strip():
                            raise ValidationError("消息内容不能为空")

                        message_id = str(uuid.uuid4())
                        metadata_json = json.dumps(metadata) if metadata else None

                        cursor.execute("""
                            INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (message_id, self.client_id, content, timestamp, 0, reply_to, priority, metadata_json))

                        message_ids.append(message_id)

                    conn.commit()
            else:
                # 直连模式批量插入
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                for msg in messages:
                    # 验证消息格式
                    if not isinstance(msg, dict) or 'content' not in msg:
                        raise ValidationError(f"无效的消息格式: {msg}")

                    content = msg.get('content', '')
                    priority = msg.get('priority', 'normal')
                    reply_to = msg.get('reply_to')
                    metadata = msg.get('metadata')

                    if not content or not content.strip():
                        raise ValidationError("消息内容不能为空")

                    message_id = str(uuid.uuid4())
                    metadata_json = json.dumps(metadata) if metadata else None

                    cursor.execute("""
                        INSERT INTO messages (id, sender, content, timestamp, read, reply_to, priority, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (message_id, self.client_id, content, timestamp, 0, reply_to, priority, metadata_json))

                    message_ids.append(message_id)

                conn.commit()
                conn.close()

            if self.enable_logging:
                logger.info(f"批量发送成功: {len(message_ids)} 条消息")

            return message_ids

        except Exception as e:
            error_msg = f"批量发送消息失败: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def mark_read(self, message_ids: List[str]) -> int:
        """
        标记消息已读

        Args:
            message_ids: 消息 ID 列表

        Returns:
            标记的数量
        """
        if not message_ids:
            logger.warning("尝试标记空的消息列表为已读")
            return 0

        try:
            if self.enable_logging:
                logger.info(f"标记 {len(message_ids)} 条消息为已读")

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            placeholders = ','.join(['?' for _ in message_ids])
            cursor.execute(
                f"UPDATE messages SET read = 1 WHERE id IN ({placeholders})",
                message_ids
            )

            count = cursor.rowcount
            conn.commit()
            conn.close()

            if self.enable_logging:
                logger.info(f"成功标记 {count} 条消息为已读")

            return count

        except sqlite3.Error as e:
            error_msg = f"标记消息已读失败: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def mark_all_read(self) -> int:
        """
        标记所有消息已读
        
        Returns:
            标记的数量
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE messages SET read = 1 WHERE sender != ? AND read = 0",
            (self.client_id,)
        )
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count
    
    def get_reply(self, original_message_id: str) -> Optional[Dict]:
        """
        获取对某条消息的回复
        
        Args:
            original_message_id: 原消息 ID
        
        Returns:
            回复消息，如果没有则返回 None
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sender, content, timestamp
            FROM messages
            WHERE reply_to = ? AND sender = ?
            ORDER BY timestamp ASC
            LIMIT 1
        """, (original_message_id, self.client_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row['id'],
                'sender': row['sender'],
                'content': row['content'],
                'timestamp': row['timestamp']
            }
        return None
    
    def wait_for_reply(
        self,
        original_message_id: str,
        timeout_minutes: int = 10,
        check_interval: int = 10
    ) -> Optional[Dict]:
        """
        等待回复

        Args:
            original_message_id: 原消息 ID
            timeout_minutes: 超时时间（分钟）
            check_interval: 检查间隔（秒）

        Returns:
            回复消息，如果超时则返回 None
        """
        try:
            if self.enable_logging:
                logger.info(f"等待回复，消息ID: {original_message_id}，超时: {timeout_minutes}分钟")

            start_time = time.time()
            timeout_seconds = timeout_minutes * 60

            while time.time() - start_time < timeout_seconds:
                reply = self.get_reply(original_message_id)

                if reply:
                    if self.enable_logging:
                        logger.info(f"收到回复: {reply['id']}")
                    return reply

                time.sleep(check_interval)

            if self.enable_logging:
                logger.warning(f"等待回复超时，消息ID: {original_message_id}")

            return None

        except Exception as e:
            error_msg = f"等待回复时发生错误: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)
    
    def send_and_wait(
        self,
        content: str,
        timeout_minutes: int = 10,
        priority: str = "normal"
    ) -> Optional[Dict]:
        """
        发送消息并等待回复
        
        Args:
            content: 消息内容
            timeout_minutes: 等待时间（分钟）
            priority: 优先级
        
        Returns:
            回复消息，如果超时则返回 None
        """
        msg_id = self.send(content, priority=priority)
        return self.wait_for_reply(msg_id, timeout_minutes=timeout_minutes)
    
    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # 总消息数
            cursor.execute("SELECT COUNT(*) FROM messages")
            total = cursor.fetchone()[0]

            # 未读消息数
            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE read = 0 AND sender != ?",
                (self.client_id,)
            )
            unread = cursor.fetchone()[0]

            # 最新消息时间
            cursor.execute("SELECT MAX(timestamp) FROM messages")
            latest = cursor.fetchone()[0]

            conn.close()

            return {
                'total_messages': total,
                'unread_messages': unread,
                'latest_message_time': datetime.fromtimestamp(latest).strftime('%Y-%m-%d %H:%M:%S') if latest else None,
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'cache_hit_rate': f"{(self._cache_hits / (self._cache_hits + self._cache_misses) * 100):.2f}%" if (self._cache_hits + self._cache_misses) > 0 else "0%"
            }

        except sqlite3.Error as e:
            error_msg = f"获取统计信息失败: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """
        从缓存获取消息

        Args:
            key: 缓存键（消息 ID）

        Returns:
            消息数据，如果缓存未命中则返回 None
        """
        if key in self._cache:
            data = self._cache[key]
            if time.time() - data['timestamp'] < 3600:  # 缓存有效期 1 小时
                self._cache_hits += 1
                logger.debug(f"缓存命中: {key}")
                return data['message']
            else:
                # 缓存过期，删除
                del self._cache[key]

        self._cache_misses += 1
        logger.debug(f"缓存未命中: {key}")
        return None

    def _set_cache(self, key: str, message: Dict):
        """
        设置缓存

        Args:
            key: 缓存键（消息 ID）
            message: 消息数据
        """
        # 如果缓存已满，删除最旧的缓存
        if len(self._cache) >= self._cache_max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]

        self._cache[key] = {
            'message': message,
            'timestamp': time.time()
        }
        logger.debug(f"缓存已设置: {key}")

    def _clear_cache(self):
        """清空缓存"""
        count = len(self._cache)
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info(f"缓存已清空: {count} 条")

    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        return {
            'cache_size': len(self._cache),
            'cache_max_size': self._cache_max_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': f"{(self._cache_hits / (self._cache_hits + self._cache_misses) * 100):.2f}%" if (self._cache_hits + self._cache_misses) > 0 else "0%"
        }

    def get_metrics(self) -> Dict:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        uptime = time.time() - self._metrics['start_time']
        avg_response_time = (
            self._metrics['total_response_time'] / (self._metrics['messages_sent'] + self._metrics['messages_received'])
            if (self._metrics['messages_sent'] + self._metrics['messages_received']) > 0
            else 0
        )

        return {
            'uptime_seconds': uptime,
            'uptime_formatted': f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
            'messages_sent': self._metrics['messages_sent'],
            'messages_received': self._metrics['messages_received'],
            'errors': self._metrics['errors'],
            'total_operations': self._metrics['messages_sent'] + self._metrics['messages_received'],
            'avg_response_time_ms': avg_response_time * 1000,
            'error_rate': f"{(self._metrics['errors'] / self._metrics['total_operations'] * 100):.2f}%" if self._metrics['total_operations'] > 0 else "0%"
        }

    def health_check(self) -> Dict:
        """
        系统健康检查

        Returns:
            健康检查结果字典
        """
        try:
            # 检查数据库
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            database_healthy = True
            database_error = None
        except Exception as e:
            database_healthy = False
            database_error = str(e)

        # 检查磁盘空间
        try:
            import shutil
            disk_usage = shutil.disk_usage(self.db_path.parent)
            disk_free_gb = disk_usage.free / (1024 ** 3)
            disk_healthy = disk_free_gb > 0.1  # 至少 100MB
        except Exception as e:
            disk_free_gb = 0
            disk_healthy = False

        # 检查连接池
        pool_healthy = True
        if self.enable_pool:
            pool_healthy = self._pool is not None

        # 综合健康状态
        all_healthy = database_healthy and disk_healthy and pool_healthy

        return {
            'status': 'healthy' if all_healthy else 'unhealthy',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'checks': {
                'database': {
                    'healthy': database_healthy,
                    'error': database_error
                },
                'disk': {
                    'healthy': disk_healthy,
                    'free_gb': round(disk_free_gb, 2)
                },
                'connection_pool': {
                    'healthy': pool_healthy,
                    'enabled': self.enable_pool,
                    'size': self.pool_size if self.enable_pool else 0
                }
            },
            'metrics': self.get_metrics()
        }

    def search_messages(
        self,
        keyword: str,
        sender: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        搜索消息

        Args:
            keyword: 搜索关键词
            sender: 发送者过滤（可选）
            start_time: 开始时间戳（可选）
            end_time: 结束时间戳（可选）
            limit: 限制返回数量

        Returns:
            匹配的消息列表

        Raises:
            ValidationError: 参数无效
            DatabaseError: 数据库操作失败
        """
        if not keyword or not keyword.strip():
            raise ValidationError("搜索关键词不能为空")

        try:
            if self.enable_logging:
                logger.info(f"搜索消息: {keyword[:50]}{'...' if len(keyword) > 50 else ''}")

            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 构建查询
            query = """
                SELECT id, sender, content, timestamp, priority, reply_to, read
                FROM messages
                WHERE content LIKE ?
            """
            params = [f"%{keyword}%"]

            # 添加过滤条件
            if sender:
                query += " AND sender = ?"
                params.append(sender)

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)

            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            # 执行查询
            cursor.execute(query, params)

            messages = [
                {
                    'id': row['id'],
                    'sender': row['sender'],
                    'content': row['content'],
                    'timestamp': row['timestamp'],
                    'priority': row['priority'] or 'normal',
                    'reply_to': row['reply_to'],
                    'read': bool(row['read'])
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            if self.enable_logging:
                logger.info(f"搜索完成，找到 {len(messages)} 条匹配消息")

            return messages

        except sqlite3.Error as e:
            error_msg = f"搜索消息失败: {e}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def clear_history(self, older_than_days: int = 30) -> int:
        """
        清理历史消息
        
        Args:
            older_than_days: 清理早于多少天的消息
        
        Returns:
            清理的数量
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff = int(time.time()) - (older_than_days * 24 * 60 * 60)
        cursor.execute(
            "DELETE FROM messages WHERE timestamp < ?",
            (cutoff,)
        )
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return count

    def create_task(self, title: str, description: str = "", assigned_to: str = "unknown", 
                    created_by: str = "unknown", priority: str = "normal") -> Dict:
        """
        创建新任务
        
        Args:
            title: 任务标题
            description: 任务描述
            assigned_to: 分配给谁
            created_by: 创建者
            priority: 优先级 (urgent/high/normal/low)
        
        Returns:
            任务信息
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        task_id = str(uuid.uuid4())
        now = int(time.time())
        
        cursor.execute("""
            INSERT INTO tasks (id, title, description, status, assigned_to, created_by, priority, created_at, updated_at)
            VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)
        """, (task_id, title, description, assigned_to, created_by, priority, now, now))
        
        conn.commit()
        conn.close()
        
        if self.enable_logging:
            logger.info(f"任务已创建: {task_id} - {title} (分配给: {assigned_to})")
        
        return {
            "task_id": task_id,
            "title": title,
            "status": "pending",
            "assigned_to": assigned_to,
            "created_at": now
        }

    def update_task(self, task_id: str, status: Optional[str] = None, 
                    result: Optional[str] = None) -> Dict:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态 (pending/running/completed/failed)
            result: 执行结果
        
        Returns:
            更新结果
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        now = int(time.time())
        
        if status and result:
            cursor.execute("""
                UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?
            """, (status, result, now, task_id))
        elif status:
            cursor.execute("""
                UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?
            """, (status, now, task_id))
        elif result:
            cursor.execute("""
                UPDATE tasks SET result = ?, updated_at = ? WHERE id = ?
            """, (result, now, task_id))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if self.enable_logging:
            logger.info(f"任务已更新: {task_id} (状态: {status})")
        
        return {
            "task_id": task_id,
            "updated": count > 0,
            "updated_at": now
        }

    def get_tasks(self, assigned_to: Optional[str] = None, status: Optional[str] = None, 
                  limit: int = 10) -> List[Dict]:
        """
        获取任务列表
        
        Args:
            assigned_to: 筛选分配给谁的任务
            status: 筛选状态
            limit: 限制数量
        
        Returns:
            任务列表
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if assigned_to:
            query += " AND assigned_to = ?"
            params.append(assigned_to)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append({
                "id": row["id"],
                "title": row["title"],
                "description": row["description"],
                "status": row["status"],
                "assigned_to": row["assigned_to"],
                "created_by": row["created_by"],
                "priority": row["priority"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "result": row["result"]
            })
        
        if self.enable_logging:
            logger.info(f"查询任务: 找到 {len(tasks)} 条")
        
        return tasks


# ==================== 便捷函数 ====================

def create_client(client_id: str) -> MessageBoardClient:
    """创建客户端实例"""
    return MessageBoardClient(client_id)


def quick_send(client_id: str, content: str) -> str:
    """快速发送消息"""
    client = MessageBoardClient(client_id)
    return client.send(content)


def quick_read(client_id: str, unread_only: bool = True) -> List[Dict]:
    """快速读取消息"""
    client = MessageBoardClient(client_id)
    if unread_only:
        return client.read_unread()
    else:
        return client.read_all()


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import sys
    
    def print_usage():
        print("""
Message Board SDK - 命令行接口

用法:
    python3 message_sdk.py <client_id> <command> [args]

命令:
    send <content>              发送消息
    read [unread]               读取消息 (unread=只读未读)
    stats                       查看统计
    wait <msg_id> [timeout]     等待回复
    mark-read <id1> [id2]...    标记已读

示例:
    python3 message_sdk.py ai_bot send "你好"
    python3 message_sdk.py ai_bot read
    python3 message_sdk.py ai_bot stats
        """)
    
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)
    
    client_id = sys.argv[1]
    command = sys.argv[2]
    client = MessageBoardClient(client_id)
    
    if command == "send":
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        msg_id = client.send(content)
        print(f"✓ 消息已发送 (ID: {msg_id})")
    
    elif command == "read":
        unread_only = len(sys.argv) > 3 and sys.argv[3] == "unread"
        messages = client.read_unread() if unread_only else client.read_all()
        
        if not messages:
            print("没有消息")
        else:
            for msg in messages:
                time_str = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')
                print(f"[{time_str}] {msg['sender']}: {msg['content']}")
    
    elif command == "stats":
        stats = client.get_stats()
        print(f"总消息数：{stats['total_messages']}")
        print(f"未读消息：{stats['unread_messages']}")
        print(f"最新消息：{stats['latest_message_time'] or '无'}")
    
    elif command == "wait":
        msg_id = sys.argv[3] if len(sys.argv) > 3 else None
        timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        
        if not msg_id:
            print("错误：需要消息 ID")
            sys.exit(1)
        
        print(f"等待回复（最多{timeout}分钟）...")
        reply = client.wait_for_reply(msg_id, timeout_minutes=timeout)
        
        if reply:
            print(f"[{reply['sender']}] {reply['content']}")
        else:
            print("等待超时，未收到回复")
    
    elif command == "mark-read":
        ids = sys.argv[3:]
        if not ids:
            print("错误：需要消息 ID")
            sys.exit(1)
        
        count = client.mark_read(ids)
        print(f"✓ 已标记 {count} 条消息为已读")
    
    else:
        print(f"未知命令：{command}")
        print_usage()
        sys.exit(1)
