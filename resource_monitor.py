#!/usr/bin/env python3
"""
资源监控工具
监控系统资源使用情况，帮助优化性能
"""
import psutil
import time
from pathlib import Path
from typing import Dict, List


class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.history: List[Dict] = []
        self.max_history = 100
    
    def get_stats(self) -> Dict:
        """获取当前资源统计"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # 计算资源占用（百分比）
            memory_percent = self.process.memory_percent()
            
            stats = {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_info.rss / 1024 / 1024,
                "memory_percent": memory_percent,
                "num_threads": self.process.num_threads(),
                "num_fds": len(self.process.open_files()) if hasattr(self.process, 'open_files') else 0,
                "timestamp": time.time()
            }
            
            # 记录历史
            self.history.append(stats)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def get_average_stats(self, last_n: int = 10) -> Dict:
        """获取平均统计"""
        if not self.history:
            return {}
        
        recent = self.history[-last_n:]
        return {
            "avg_cpu": sum(s.get("cpu_percent", 0) for s in recent) / len(recent),
            "avg_memory_mb": sum(s.get("memory_mb", 0) for s in recent) / len(recent),
            "avg_memory_percent": sum(s.get("memory_percent", 0) for s in recent) / len(recent),
            "max_memory_mb": max(s.get("memory_mb", 0) for s in recent),
            "max_cpu": max(s.get("cpu_percent", 0) for s in recent)
        }
    
    def get_warnings(self) -> List[str]:
        """获取资源警告"""
        warnings = []
        stats = self.get_stats()
        
        if stats.get("memory_percent", 0) > 80:
            warnings.append(f"内存占用过高: {stats['memory_percent']:.1f}%")
        
        if stats.get("cpu_percent", 0) > 80:
            warnings.append(f"CPU占用过高: {stats['cpu_percent']:.1f}%")
        
        if stats.get("num_threads", 0) > 50:
            warnings.append(f"线程数过多: {stats['num_threads']}")
        
        if stats.get("memory_mb", 0) > 500:
            warnings.append(f"内存使用过大: {stats['memory_mb']:.1f}MB")
        
        return warnings
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        avg = self.get_average_stats()
        warnings = self.get_warnings()
        
        print("\n" + "="*50)
        print("资源监控统计")
        print("="*50)
        print(f"CPU 使用率: {stats.get('cpu_percent', 0):.1f}%")
        print(f"内存使用: {stats.get('memory_mb', 0):.1f}MB ({stats.get('memory_percent', 0):.1f}%)")
        print(f"线程数: {stats.get('num_threads', 0)}")
        print(f"打开文件数: {stats.get('num_fds', 0)}")
        
        if avg:
            print("\n" + "-"*50)
            print("最近10次平均值:")
            print(f"平均 CPU: {avg.get('avg_cpu', 0):.1f}%")
            print(f"平均内存: {avg.get('avg_memory_mb', 0):.1f}MB")
            print(f"最大内存: {avg.get('max_memory_mb', 0):.1f}MB")
        
        if warnings:
            print("\n" + "!"*50)
            print("警告:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
        
        print("="*50 + "\n")


def check_system_resources() -> Dict:
    """检查系统资源"""
    try:
        return {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory_total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "memory_available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 resource_monitor.py <command>")
        print("命令:")
        print("  stats      - 显示当前资源统计")
        print("  system     - 显示系统资源")
        print("  monitor    - 持续监控（按Ctrl+C退出）")
        print("  check      - 检查资源警告")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stats":
        monitor = ResourceMonitor()
        monitor.print_stats()
    
    elif command == "system":
        stats = check_system_resources()
        print("\n系统资源:")
        print(f"CPU核心数: {stats.get('cpu_count', 0)}")
        print(f"CPU使用率: {stats.get('cpu_percent', 0):.1f}%")
        print(f"总内存: {stats.get('memory_total_gb', 0):.1f}GB")
        print(f"可用内存: {stats.get('memory_available_gb', 0):.1f}GB")
        print(f"内存使用率: {stats.get('memory_percent', 0):.1f}%")
        print(f"磁盘使用率: {stats.get('disk_usage_percent', 0):.1f}%")
    
    elif command == "monitor":
        monitor = ResourceMonitor()
        try:
            while True:
                monitor.print_stats()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n监控已停止")
    
    elif command == "check":
        monitor = ResourceMonitor()
        warnings = monitor.get_warnings()
        if warnings:
            print("发现警告:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
        else:
            print("✓ 资源使用正常")


if __name__ == "__main__":
    main()