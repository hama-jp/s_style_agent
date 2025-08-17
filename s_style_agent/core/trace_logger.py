"""
S式実行のトレースログ機能

JSON-L形式での実行ログ出力とメタデータ収集を提供します。
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class ProvenanceType(Enum):
    """実行元の種別"""
    BUILTIN = "builtin"     # 組み込み関数
    LLM = "llm"            # LLM呼び出し
    TOOL = "tool"          # 外部ツール
    MCP = "mcp"            # MCPサーバー経由
    USER = "user"          # ユーザー入力          # ユーザー入力


@dataclass
class ExecutionMetadata:
    """実行メタデータ"""
    llm_tokens: Optional[Dict[str, int]] = None  # {"prompt": 50, "completion": 20}
    tool_called: Optional[str] = None
    provenance: ProvenanceType = ProvenanceType.BUILTIN
    error: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    # MCP関連メタデータ
    mcp_server: Optional[str] = None              # MCPサーバー名
    mcp_tool: Optional[str] = None                # 呼び出されたMCPツール名
    mcp_params: Optional[Dict[str, Any]] = None   # MCPツールパラメータ
    mcp_duration_ms: Optional[float] = None       # MCP呼び出し時間
    mcp_success: Optional[bool] = None            # MCP呼び出し成功フラグ


@dataclass
class TraceEntry:
    """トレースログエントリ"""
    timestamp: str
    operation: str
    path: List[int]  # S式内の位置パス
    input: Any
    output: Any
    duration_ms: float
    explanation: str
    metadata: ExecutionMetadata
    
    def to_json_line(self) -> str:
        """JSON-L形式で出力"""
        data = asdict(self)
        # Enumを文字列に変換
        data['metadata']['provenance'] = data['metadata']['provenance'].value
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


class TraceLogger:
    """S式実行のトレースロガー"""
    
    def __init__(self, output_file: Optional[Path] = None):
        self.output_file = output_file
        self.entries: List[TraceEntry] = []
        self.current_path: List[int] = []
        
    def start_operation(self, operation: str, input_data: Any) -> int:
        """操作開始をログ"""
        entry_id = len(self.entries)
        entry = TraceEntry(
            timestamp=self._current_timestamp(),
            operation=operation,
            path=self.current_path.copy(),
            input=input_data,
            output=None,
            duration_ms=0,
            explanation="",
            metadata=ExecutionMetadata()
        )
        self.entries.append(entry)
        return entry_id
    
    def end_operation(self, entry_id: int, output: Any, metadata: Optional[ExecutionMetadata] = None):
        """操作終了とログ出力"""
        if entry_id >= len(self.entries):
            return
            
        entry = self.entries[entry_id]
        start_time = self._parse_timestamp(entry.timestamp)
        current_time = time.time()
        
        # エントリを更新
        entry.output = output
        entry.duration_ms = (current_time - start_time) * 1000
        if metadata:
            entry.metadata = metadata
            
        # ファイル出力
        if self.output_file:
            self._write_to_file(entry)
    
    def update_metadata(self, entry_id: int, metadata: ExecutionMetadata):
        """既存エントリのメタデータを更新"""
        if entry_id < len(self.entries):
            entry = self.entries[entry_id]
            entry.metadata = metadata
    
    def log_error(self, operation: str, input_data: Any, error: Exception, explanation: str = ""):
        """エラーログ"""
        metadata = ExecutionMetadata(
            error=str(error),
            provenance=ProvenanceType.BUILTIN
        )
        
        entry = TraceEntry(
            timestamp=self._current_timestamp(),
            operation=operation,
            path=self.current_path.copy(),
            input=input_data,
            output=None,
            duration_ms=0,
            explanation=f"エラー: {explanation}",
            metadata=metadata
        )
        
        self.entries.append(entry)
        if self.output_file:
            self._write_to_file(entry)
    
    def push_path(self, index: int):
        """パスに要素を追加（子ノードに入る）"""
        self.current_path.append(index)
    
    def pop_path(self):
        """パスから要素を削除（親ノードに戻る）"""
        if self.current_path:
            self.current_path.pop()
    
    def get_recent_entries(self, count: int = 10) -> List[TraceEntry]:
        """最近のエントリを取得"""
        return self.entries[-count:]
    
    def clear(self):
        """ログをクリア"""
        self.entries.clear()
        self.current_path.clear()
    
    def _current_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        return time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """タイムスタンプをパース"""
        # 簡易実装：現在時刻を返す（本来はISO形式パース）
        return time.time()
    
    def _write_to_file(self, entry: TraceEntry):
        """ファイルに書き込み"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(entry.to_json_line() + '\n')
        except Exception as e:
            print(f"ログ書き込みエラー: {e}")


# グローバルロガーインスタンス
_global_logger: Optional[TraceLogger] = None


def get_global_logger() -> TraceLogger:
    """グローバルロガーを取得"""
    global _global_logger
    if _global_logger is None:
        _global_logger = TraceLogger()
    return _global_logger


def set_global_logger(logger: TraceLogger):
    """グローバルロガーを設定"""
    global _global_logger
    _global_logger = logger


def configure_trace_logging(output_file: Optional[Union[str, Path]] = None) -> TraceLogger:
    """トレースログを設定"""
    output_path = Path(output_file) if output_file else None
    logger = TraceLogger(output_path)
    set_global_logger(logger)
    return logger