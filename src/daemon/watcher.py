"""文件监听器 - 使用 watchdog 库实现跨平台文件监控"""
import time
import asyncio
from pathlib import Path
from typing import Callable, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class DatabaseFileHandler(FileSystemEventHandler):
    """数据库文件变化处理器"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
        self._last_modified: float = 0
        self._debounce_seconds: float = 0.5
    
    def on_modified(self, event):
        """文件修改事件"""
        if isinstance(event, FileModifiedEvent):
            # 只处理 WAL 文件和主数据库文件
            if event.src_path.endswith(('.db', '.db-wal')):
                current_time = time.time()
                # 防抖处理
                if current_time - self._last_modified > self._debounce_seconds:
                    self._last_modified = current_time
                    self.callback(event.src_path)


class FileWatcher:
    """文件监听器"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path).expanduser()
        self.watch_dir = self.db_path.parent
        self.observer: Optional[Observer] = None
        self.callbacks: Set[Callable] = set()
        self._running = False
    
    def on_modify(self, callback: Callable):
        """注册修改回调"""
        self.callbacks.add(callback)
    
    def _handle_modify(self, src_path: str):
        """处理修改事件"""
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.run(callback(src_path))
                else:
                    callback(src_path)
            except Exception as e:
                print(f"[Watcher Error] {callback.__name__}: {e}")
    
    def start(self):
        """启动监听"""
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        
        handler = DatabaseFileHandler(self._handle_modify)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.watch_dir), recursive=False)
        self.observer.start()
        self._running = True
        
        print(f"[Watcher] 开始监听：{self.watch_dir}")
    
    def stop(self):
        """停止监听"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self._running = False
            print("[Watcher] 已停止监听")
    
    def run_forever(self):
        """运行监听循环"""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
