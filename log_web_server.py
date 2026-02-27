#!/usr/bin/env python3
"""
日志管理 Web 服务器

功能:
1. 查看日志文件（分页）
2. 搜索日志
3. 清理日志
4. 下载日志
5. 时间范围过滤
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import os
import datetime
from typing import List

app = Flask(__name__)

# 允许跨域
CORS(app)

# 日志文件路径
LOG_DIR = Path("~/.message_board").expanduser()
LOG_FILE = LOG_DIR / "message_board.log"

# 确保日志目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)


def read_log_file(lines: int = 100, search: str = None, start_time: str = None, end_time: str = None) -> List[str]:
    """读取日志文件"""
    if not LOG_FILE.exists():
        return []
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        all_lines = f.readlines()
    
    # 时间过滤
    if start_time or end_time:
        filtered_lines = []
        for line in all_lines:
            try:
                # 提取时间戳（假设日志格式：2026-02-27 12:00:00,123 - ...）
                if " - " in line:
                    time_str = line.split(" - ")[0]
                    line_time = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S,%f")
                    
                    if start_time:
                        start_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                        if line_time < start_dt:
                            continue
                    
                    if end_time:
                        end_dt = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                        if line_time > end_dt:
                            continue
                    
                    filtered_lines.append(line)
                else:
                    filtered_lines.append(line)
            except:
                filtered_lines.append(line)
        
        all_lines = filtered_lines
    
    # 搜索过滤
    if search:
        all_lines = [line for line in all_lines if search.lower() in line.lower()]
    
    # 只返回最后 N 行
    return all_lines[-lines:]


@app.route("/")
def root():
    """主页"""
    return jsonify({
        "message": "日志管理 Web 服务器",
        "version": "1.0.0",
        "endpoints": [
            "/api/logs",
            "/api/log-stats",
            "/api/clear-logs",
            "/api/download-logs"
        ]
    })


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """获取日志 API"""
    lines = request.args.get('lines', 100, type=int)
    search = request.args.get('search', '')
    start_time = request.args.get('start_time', '')
    end_time = request.args.get('end_time', '')
    
    log_lines = read_log_file(lines, search, start_time, end_time)
    
    return jsonify({
        "success": True,
        "logs": log_lines,
        "total": len(log_lines),
        "filters": {
            "lines": lines,
            "search": search,
            "start_time": start_time,
            "end_time": end_time
        }
    })


@app.route("/api/log-stats", methods=["GET"])
def get_log_stats():
    """获取日志统计"""
    if not LOG_FILE.exists():
        return jsonify({
            "success": True,
            "size": 0,
            "lines": 0,
            "modified": None,
            "exists": False
        })
    
    stat = LOG_FILE.stat()
    
    # 统计不同级别的日志数量
    info_count = 0
    warning_count = 0
    error_count = 0
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_lower = line.lower()
            if ' - error - ' in line_lower:
                error_count += 1
            elif ' - warning - ' in line_lower or ' - warn - ' in line_lower:
                warning_count += 1
            elif ' - info - ' in line_lower:
                info_count += 1
    
    return jsonify({
        "success": True,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "lines": sum(1 for _ in open(LOG_FILE, 'r', encoding='utf-8', errors='ignore')),
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        "exists": True,
        "stats": {
            "info": info_count,
            "warning": warning_count,
            "error": error_count
        }
    })


@app.route("/api/clear-logs", methods=["POST"])
def clear_logs():
    """清理日志"""
    if LOG_FILE.exists():
        LOG_FILE.unlink()
        return jsonify({
            "success": True,
            "message": "日志已清理"
        })
    else:
        return jsonify({
            "success": False,
            "message": "日志文件不存在"
        })


@app.route("/api/download-logs", methods=["GET"])
def download_logs():
    """下载日志"""
    if LOG_FILE.exists():
        return send_file(
            LOG_FILE,
            as_attachment=True,
            download_name=f"message_board_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            mimetype="text/plain"
        )
    else:
        return jsonify({
            "success": False,
            "message": "日志文件不存在"
        })


if __name__ == "__main__":
    print("🌐 日志管理 Web 服务器启动中...")
    print(f"📁 日志目录: {LOG_DIR}")
    print(f"📄 日志文件: {LOG_FILE}")
    print("🚀 访问地址: http://localhost:8000")
    print("📋 可用接口:")
    print("   GET  / - 主页")
    print("   GET  /api/logs - 获取日志")
    print("   GET  /api/log-stats - 获取统计")
    print("   POST /api/clear-logs - 清理日志")
    print("   GET  /api/download-logs - 下载日志")
    print("\n按 Ctrl+C 停止服务器")
    
    app.run(host="0.0.0.0", port=8000, debug=False)