"""
Message Board 异常定义

提供清晰的异常层次结构，便于错误处理和调试
"""

class MessageBoardError(Exception):
    """留言簿基础异常"""
    pass

class DatabaseError(MessageBoardError):
    """数据库相关异常"""
    pass

class ConnectionError(DatabaseError):
    """数据库连接异常"""
    pass

class QueryError(DatabaseError):
    """数据库查询异常"""
    pass

class MessageNotFoundError(MessageBoardError):
    """消息未找到异常"""
    pass

class ClientNotFoundError(MessageBoardError):
    """客户端未找到异常"""
    pass

class TimeoutError(MessageBoardError):
    """操作超时异常"""
    pass

class ValidationError(MessageBoardError):
    """数据验证异常"""
    pass

class ConfigurationError(MessageBoardError):
    """配置异常"""
    pass

class MigrationError(MessageBoardError):
    """数据库迁移异常"""
    pass