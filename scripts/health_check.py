#!/usr/bin/env python3
"""
健康检查工具
功能：
- 检查数据库文件状态
- 检查数据库完整性
- 检查索引状态
- 检查性能指标
- 生成健康报告
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, db_path: str = "~/.message_board/board.db"):
        self.db_path = Path(db_path).expanduser()
    
    def check_database_file(self) -> dict:
        """检查数据库文件状态"""
        result = {
            "exists": self.db_path.exists(),
            "size_bytes": 0,
            "size_mb": 0,
            "readable": False,
            "writable": False
        }
        
        if result["exists"]:
            result["size_bytes"] = self.db_path.stat().st_size
            result["size_mb"] = round(result["size_bytes"] / (1024 * 1024), 2)
            result["readable"] = os.access(self.db_path, os.R_OK)
            result["writable"] = os.access(self.db_path, os.W_OK)
        
        return result
    
    def check_database_integrity(self) -> dict:
        """检查数据库完整性"""
        result = {
            "accessible": False,
            "corrupted": False,
            "tables": [],
            "error": None
        }
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 检查数据库完整性
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            result["corrupted"] = integrity_result != "ok"
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            result["tables"] = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            result["accessible"] = True
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def check_indexes(self) -> dict:
        """检查索引状态"""
        result = {
            "indexes": [],
            "missing_indexes": []
        }
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 获取所有索引
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            result["indexes"] = [row[0] for row in cursor.fetchall()]
            
            # 检查期望的索引
            expected_indexes = [
                "idx_messages_sender",
                "idx_messages_session_id",
                "idx_messages_msg_type"
            ]
            
            for index in expected_indexes:
                if index not in result["indexes"]:
                    result["missing_indexes"].append(index)
            
            conn.close()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def check_performance(self) -> dict:
        """检查性能指标"""
        result = {
            "message_count": 0,
            "unread_count": 0,
            "index_count": 0
        }
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 消息总数
            cursor.execute("SELECT COUNT(*) FROM messages")
            result["message_count"] = cursor.fetchone()[0]
            
            # 未读消息数
            cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
            result["unread_count"] = cursor.fetchone()[0]
            
            # 索引数量
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
            result["index_count"] = cursor.fetchone()[0]
            
            conn.close()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def generate_health_report(self) -> str:
        """生成健康报告"""
        report = []
        report.append("=" * 60)
        report.append("系统健康检查报告")
        report.append("=" * 60)
        report.append(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 数据库文件检查
        file_status = self.check_database_file()
        report.append("【数据库文件】")
        if file_status["exists"]:
            report.append(f"  状态: ✓ 存在")
            report.append(f"  大小: {file_status['size_mb']} MB")
            report.append(f"  可读: {'✓' if file_status['readable'] else '✗'}")
            report.append(f"  可写: {'✓' if file_status['writable'] else '✗'}")
        else:
            report.append(f"  状态: ✗ 不存在")
        report.append("")
        
        # 数据库完整性检查
        integrity = self.check_database_integrity()
        report.append("【数据库完整性】")
        if integrity["accessible"]:
            report.append(f"  可访问: ✓")
            report.append(f"  完整性: {'✓ 正常' if not integrity['corrupted'] else '✗ 损坏'}")
            report.append(f"  表数量: {len(integrity['tables'])}")
            report.append(f"  表列表: {', '.join(integrity['tables'])}")
        else:
            report.append(f"  可访问: ✗")
            if integrity["error"]:
                report.append(f"  错误: {integrity['error']}")
        report.append("")
        
        # 索引检查
        indexes = self.check_indexes()
        report.append("【索引状态】")
        report.append(f"  索引数量: {len(indexes['indexes'])}")
        if indexes["missing_indexes"]:
            report.append(f"  缺失索引: {', '.join(indexes['missing_indexes'])}")
        else:
            report.append(f"  缺失索引: 无")
        report.append("")
        
        # 性能指标
        performance = self.check_performance()
        report.append("【性能指标】")
        if "error" not in performance:
            report.append(f"  消息总数: {performance['message_count']}")
            report.append(f"  未读消息: {performance['unread_count']}")
            report.append(f"  索引数量: {performance['index_count']}")
        else:
            report.append(f"  错误: {performance['error']}")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def check_health(self) -> bool:
        """执行健康检查，返回是否健康"""
        file_status = self.check_database_file()
        if not file_status["exists"] or not file_status["readable"]:
            return False
        
        integrity = self.check_database_integrity()
        if not integrity["accessible"] or integrity["corrupted"]:
            return False
        
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="健康检查工具")
    parser.add_argument("--db", type=str,
                       default="~/.message_board/board.db",
                       help="数据库路径")
    parser.add_argument("--report", action="store_true",
                       help="生成详细报告")
    parser.add_argument("--quick", action="store_true",
                       help="快速检查（只返回健康状态）")
    
    args = parser.parse_args()
    
    checker = HealthChecker(args.db)
    
    if args.quick:
        # 快速检查
        is_healthy = checker.check_health()
        print(f"健康状态: {'✓ 正常' if is_healthy else '✗ 异常'}")
        exit(0 if is_healthy else 1)
    elif args.report:
        # 详细报告
        print(checker.generate_health_report())
    else:
        # 默认显示摘要
        file_status = checker.check_database_file()
        integrity = checker.check_database_integrity()
        performance = checker.check_performance()
        
        print("=" * 40)
        print("健康检查摘要")
        print("=" * 40)
        
        if file_status["exists"]:
            print(f"数据库: ✓ 存在 ({file_status['size_mb']} MB)")
        else:
            print(f"数据库: ✗ 不存在")
        
        if integrity["accessible"]:
            print(f"完整性: {'✓ 正常' if not integrity['corrupted'] else '✗ 损坏'}")
        else:
            print(f"完整性: ✗ 无法访问")
        
        if "error" not in performance:
            print(f"消息数: {performance['message_count']}")
            print(f"未读数: {performance['unread_count']}")
        
        print()
        print("使用 --report 查看详细报告")
        print("使用 --quick 执行快速检查")


if __name__ == "__main__":
    main()