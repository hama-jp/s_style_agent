#!/usr/bin/env python3
"""
TUIデバッグ用ログ出力機能

リアルタイムでTUIの動作状況、S式評価、ユーザー操作をログ出力
"""

import os
import time
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Dict, List
from dataclasses import dataclass


class DebugLogLevel(Enum):
    """デバッグログレベル"""
    TRACE = 0    # 最詳細（全ての操作）
    DEBUG = 1    # デバッグ情報
    INFO = 2     # 一般情報
    WARN = 3     # 警告
    ERROR = 4    # エラー


@dataclass
class DebugLogEntry:
    """デバッグログエントリ"""
    timestamp: str
    level: DebugLogLevel
    category: str     # UI, EVAL, NODE, KEY, ERROR等
    operation: str    # 具体的な操作名
    message: str      # ログメッセージ
    context: Optional[Dict[str, Any]] = None  # 追加コンテキスト情報


class TUIDebugLogger:
    """TUI専用デバッグログ機能"""
    
    def __init__(self, log_file: Optional[Path] = None, min_level: DebugLogLevel = DebugLogLevel.INFO):
        self.log_file = log_file or Path("tui_debug.log")
        self.min_level = min_level
        self.entries: List[DebugLogEntry] = []
        self.console_output = True  # コンソールにも出力するか
        
        # ログファイルを初期化
        self._init_log_file()
        
        # 起動ログ
        self.info("INIT", "startup", "TUIデバッグログ開始", {
            "log_file": str(self.log_file),
            "min_level": self.min_level.name,
            "pid": os.getpid()
        })
    
    def _init_log_file(self):
        """ログファイルを初期化"""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"# TUI Debug Log - {datetime.now().isoformat()}\n")
                f.write(f"# PID: {os.getpid()}\n")
                f.write("# Format: [TIMESTAMP] [LEVEL] [CATEGORY:OPERATION] MESSAGE\n\n")
        except Exception as e:
            print(f"⚠️ ログファイル初期化エラー: {e}")
    
    def _should_log(self, level: DebugLogLevel) -> bool:
        """ログレベルチェック"""
        return level.value >= self.min_level.value
    
    def _format_message(self, entry: DebugLogEntry) -> str:
        """ログメッセージをフォーマット"""
        level_icon = {
            DebugLogLevel.TRACE: "🔍",
            DebugLogLevel.DEBUG: "🐛", 
            DebugLogLevel.INFO: "ℹ️",
            DebugLogLevel.WARN: "⚠️",
            DebugLogLevel.ERROR: "❌"
        }
        
        icon = level_icon.get(entry.level, "📝")
        base_msg = f"[{entry.timestamp}] {icon} [{entry.category}:{entry.operation}] {entry.message}"
        
        if entry.context:
            context_str = ", ".join(f"{k}={v}" for k, v in entry.context.items())
            base_msg += f" | {context_str}"
        
        return base_msg
    
    def _write_entry(self, entry: DebugLogEntry):
        """ログエントリを書き込み"""
        if not self._should_log(entry.level):
            return
        
        formatted_msg = self._format_message(entry)
        
        # コンソール出力
        if self.console_output:
            print(formatted_msg)
        
        # ファイル出力
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_msg + "\n")
                f.flush()
        except Exception as e:
            print(f"⚠️ ログ書き込みエラー: {e}")
        
        # メモリ内保存（最大1000件）
        self.entries.append(entry)
        if len(self.entries) > 1000:
            self.entries = self.entries[-500:]  # 半分にカット
    
    def _log(self, level: DebugLogLevel, category: str, operation: str, 
             message: str, context: Optional[Dict[str, Any]] = None):
        """基本ログ記録メソッド"""
        entry = DebugLogEntry(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            level=level,
            category=category,
            operation=operation,
            message=message,
            context=context
        )
        self._write_entry(entry)
    
    # ログレベル別メソッド
    def trace(self, category: str, operation: str, message: str, context: Optional[Dict[str, Any]] = None):
        """トレースレベルログ"""
        self._log(DebugLogLevel.TRACE, category, operation, message, context)
    
    def debug(self, category: str, operation: str, message: str, context: Optional[Dict[str, Any]] = None):
        """デバッグレベルログ"""
        self._log(DebugLogLevel.DEBUG, category, operation, message, context)
    
    def info(self, category: str, operation: str, message: str, context: Optional[Dict[str, Any]] = None):
        """情報レベルログ"""
        self._log(DebugLogLevel.INFO, category, operation, message, context)
    
    def warn(self, category: str, operation: str, message: str, context: Optional[Dict[str, Any]] = None):
        """警告レベルログ"""
        self._log(DebugLogLevel.WARN, category, operation, message, context)
    
    def error(self, category: str, operation: str, message: str, context: Optional[Dict[str, Any]] = None):
        """エラーレベルログ"""
        self._log(DebugLogLevel.ERROR, category, operation, message, context)
    
    # 専用ログメソッド
    def log_ui_event(self, event_type: str, widget_id: str, details: str, **kwargs):
        """UI イベントログ"""
        self.debug("UI", event_type, f"{widget_id}: {details}", kwargs)
    
    def log_key_event(self, key: str, action: str, **kwargs):
        """キーイベントログ"""
        self.debug("KEY", "press", f"{key} → {action}", kwargs)
    
    def log_s_expr_evaluation(self, s_expr: str, operation: str, result: Any = None, **kwargs):
        """S式評価ログ"""
        context = {"s_expr": s_expr, "result": str(result)[:100] if result else None}
        context.update(kwargs)
        self.info("EVAL", operation, f"S式評価: {operation}", context)
    
    def log_node_operation(self, node_operation: str, node_path: List[int], details: str, **kwargs):
        """ノード操作ログ"""
        context = {"path": node_path, "details": details}
        context.update(kwargs)
        self.debug("NODE", node_operation, f"ノード{node_operation}: {details}", context)
    
    def log_trace_update(self, entry_count: int, new_entries: int, **kwargs):
        """トレース更新ログ"""
        context = {"total_entries": entry_count, "new_entries": new_entries}
        context.update(kwargs)
        self.trace("TRACE", "update", f"トレース更新: +{new_entries}件 (計{entry_count}件)", context)
    
    def log_error_with_traceback(self, error: Exception, operation: str, **kwargs):
        """エラーとトレースバックをログ"""
        tb_str = traceback.format_exc()
        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": tb_str
        }
        context.update(kwargs)
        self.error("ERROR", operation, f"例外発生: {type(error).__name__}: {error}", context)
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """パフォーマンスログ"""
        context = {"duration_ms": duration_ms}
        context.update(kwargs)
        
        if duration_ms > 1000:  # 1秒以上
            level = DebugLogLevel.WARN
            message = f"🐌 重い処理: {operation} ({duration_ms:.1f}ms)"
        elif duration_ms > 100:  # 100ms以上
            level = DebugLogLevel.INFO
            message = f"⏱️ 処理時間: {operation} ({duration_ms:.1f}ms)"
        else:
            level = DebugLogLevel.TRACE
            message = f"⚡ 高速処理: {operation} ({duration_ms:.1f}ms)"
        
        self._log(level, "PERF", operation, message, context)
    
    def set_log_level(self, level: DebugLogLevel):
        """ログレベルを変更"""
        old_level = self.min_level
        self.min_level = level
        self.info("INIT", "level_change", f"ログレベル変更: {old_level.name} → {level.name}")
    
    def enable_console_output(self, enable: bool = True):
        """コンソール出力の有効/無効"""
        self.console_output = enable
        self.info("INIT", "console_toggle", f"コンソール出力: {'有効' if enable else '無効'}")
    
    def get_recent_logs(self, count: int = 50, level: Optional[DebugLogLevel] = None) -> List[DebugLogEntry]:
        """最近のログエントリを取得"""
        entries = self.entries
        if level:
            entries = [e for e in entries if e.level.value >= level.value]
        return entries[-count:]
    
    def clear_logs(self):
        """メモリ内ログをクリア"""
        count = len(self.entries)
        self.entries.clear()
        self.info("INIT", "clear", f"メモリ内ログクリア: {count}件削除")
    
    def shutdown(self):
        """ログ機能終了"""
        self.info("INIT", "shutdown", "TUIデバッグログ終了", {
            "total_entries": len(self.entries),
            "log_file": str(self.log_file)
        })


# グローバルインスタンス
_debug_logger: Optional[TUIDebugLogger] = None


def get_debug_logger() -> TUIDebugLogger:
    """デバッグログインスタンスを取得"""
    global _debug_logger
    if _debug_logger is None:
        # 環境変数でログレベルを制御
        level_name = os.getenv("TUI_DEBUG_LEVEL", "INFO").upper()
        try:
            level = DebugLogLevel[level_name]
        except KeyError:
            level = DebugLogLevel.INFO
        
        _debug_logger = TUIDebugLogger(min_level=level)
    return _debug_logger


def setup_debug_logging(log_file: Optional[Path] = None, level: DebugLogLevel = DebugLogLevel.INFO):
    """デバッグログを設定"""
    global _debug_logger
    _debug_logger = TUIDebugLogger(log_file, level)
    return _debug_logger


# 便利関数
def debug_log(category: str, operation: str, message: str, **kwargs):
    """クイックデバッグログ"""
    get_debug_logger().debug(category, operation, message, kwargs)


def info_log(category: str, operation: str, message: str, **kwargs):
    """クイック情報ログ"""
    get_debug_logger().info(category, operation, message, kwargs)


def error_log(category: str, operation: str, message: str, **kwargs):
    """クイックエラーログ"""
    get_debug_logger().error(category, operation, message, kwargs)