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
    
    # 階層構造メタデータ（サブツリー折りたたみ用）
    depth: int = 0                                # S式ツリー内の深度
    parent_path: Optional[List[int]] = None       # 親ノードのパス
    has_children: bool = False                    # 子ノードの有無
    child_count: int = 0                          # 子ノード数
    subtree_duration_ms: Optional[float] = None   # サブツリー全体の実行時間
    subtree_operation_count: int = 0              # サブツリー内の操作数
    is_collapsed: bool = False                    # 折りたたみ状態（UI用）            # MCP呼び出し成功フラグ


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
        
    def start_operation(self, operation: str, input_data: Any, explanation: str = "") -> int:
        """操作開始をログ"""
        entry_id = len(self.entries)
        entry = TraceEntry(
            timestamp=self._current_timestamp(),
            operation=operation,
            path=self.current_path.copy(),
            input=input_data,
            output=None,
            duration_ms=0,
            explanation=explanation,
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

    def analyze_tree_structure(self) -> None:
        """エントリ全体の階層構造を分析してメタデータを更新"""
        # パス -> エントリマップを作成
        path_to_entries: Dict[tuple, List[TraceEntry]] = {}
        for entry in self.entries:
            path_tuple = tuple(entry.path)
            if path_tuple not in path_to_entries:
                path_to_entries[path_tuple] = []
            path_to_entries[path_tuple].append(entry)
        
        # 各エントリの階層情報を更新
        for entry in self.entries:
            self._update_hierarchy_metadata(entry, path_to_entries)
    
    def _update_hierarchy_metadata(self, entry: TraceEntry, path_to_entries: Dict[tuple, List[TraceEntry]]) -> None:
        """個別エントリの階層メタデータを更新"""
        path_tuple = tuple(entry.path)
        
        # 深度を設定
        entry.metadata.depth = len(entry.path)
        
        # 親パスを設定
        if entry.path:
            entry.metadata.parent_path = entry.path[:-1]
        
        # 子ノードを検索
        children = self._find_child_entries(entry, path_to_entries)
        entry.metadata.has_children = len(children) > 0
        entry.metadata.child_count = len(children)
        
        # サブツリー統計を計算
        if children:
            self._calculate_subtree_stats(entry, children)
    
    def _find_child_entries(self, parent_entry: TraceEntry, path_to_entries: Dict[tuple, List[TraceEntry]]) -> List[TraceEntry]:
        """指定エントリの直接の子エントリを検索"""
        children = []
        parent_path_len = len(parent_entry.path)
        
        for entry in self.entries:
            # 子ノードの条件: パスの長さが親+1で、先頭部分が親パスと一致
            if (len(entry.path) == parent_path_len + 1 and 
                entry.path[:parent_path_len] == parent_entry.path):
                children.append(entry)
        
        return children
    
    def _calculate_subtree_stats(self, parent_entry: TraceEntry, children: List[TraceEntry]) -> None:
        """サブツリーの統計情報を計算"""
        # サブツリー内のすべてのエントリを収集
        subtree_entries = self._collect_subtree_entries(parent_entry)
        
        # 合計実行時間を計算
        total_duration = sum(entry.duration_ms for entry in subtree_entries if entry.duration_ms > 0)
        parent_entry.metadata.subtree_duration_ms = total_duration
        
        # 操作数をカウント
        parent_entry.metadata.subtree_operation_count = len(subtree_entries)
    
    def _collect_subtree_entries(self, root_entry: TraceEntry) -> List[TraceEntry]:
        """指定エントリをルートとするサブツリー内のすべてのエントリを収集"""
        subtree_entries = []
        root_path = root_entry.path
        
        for entry in self.entries:
            # サブツリーの条件: パスが親パスで始まる（親パス含む）
            if (len(entry.path) >= len(root_path) and 
                entry.path[:len(root_path)] == root_path):
                subtree_entries.append(entry)
        
        return subtree_entries
    
    def get_tree_summary(self) -> Dict[str, Any]:
        """ツリー構造のサマリーを取得"""
        self.analyze_tree_structure()
        
        # 深度別統計
        depth_stats = {}
        total_operations = len(self.entries)
        total_duration = sum(entry.duration_ms for entry in self.entries if entry.duration_ms > 0)
        
        for entry in self.entries:
            depth = entry.metadata.depth
            if depth not in depth_stats:
                depth_stats[depth] = {"count": 0, "duration_ms": 0}
            depth_stats[depth]["count"] += 1
            depth_stats[depth]["duration_ms"] += entry.duration_ms or 0
        
        return {
            "total_operations": total_operations,
            "total_duration_ms": total_duration,
            "max_depth": max(depth_stats.keys()) if depth_stats else 0,
            "depth_statistics": depth_stats,
            "tree_complexity": self._calculate_tree_complexity()
        }
    
    def _calculate_tree_complexity(self) -> Dict[str, int]:
        """ツリーの複雑度指標を計算"""
        complexity = {
            "leaf_nodes": 0,       # 葉ノード数
            "branch_nodes": 0,     # 分岐ノード数
            "max_children": 0,     # 最大子ノード数
            "total_nodes": len(self.entries)
        }
        
        for entry in self.entries:
            if entry.metadata.has_children:
                complexity["branch_nodes"] += 1
                complexity["max_children"] = max(complexity["max_children"], entry.metadata.child_count)
            else:
                complexity["leaf_nodes"] += 1
        
        return complexity


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