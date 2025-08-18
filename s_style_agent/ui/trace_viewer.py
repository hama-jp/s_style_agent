"""
S式実行トレースビューア（Textualベース）

リアルタイムでS式評価の実行状況を表示するTUIアプリケーション
"""

from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import json
import time
import os

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Tree, Header, Footer, Static, DataTable, Log, 
    Button, Input, Label, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.binding import Binding
from rich.syntax import Syntax
from rich.text import Text
from rich.panel import Panel
from rich.json import JSON

from ..core.trace_logger import TraceEntry, TraceLogger, get_global_logger
from ..core.parser import parse_s_expression
from ..core.evaluator import ContextualEvaluator, Environment


class ExpandableTraceNode:
    """S式実行トレースの展開可能ノード（NEXT_PHASE_PLANに従った設計）"""
    
    def __init__(self, operation: str, s_expr: str, children: List['ExpandableTraceNode'] = None):
        self.operation = operation
        self.s_expr = s_expr
        self.children = children or []
        self.is_expanded = True  # デフォルトは展開
        self.execution_status = "pending"  # pending, running, completed, error
        self.duration_ms = 0
        self.result = None
        self.path: List[int] = []  # ツリー内でのパス
        self.depth = 0
        
        # トレース情報
        self.metadata = {}
        self.trace_entry = None
        
        # UI状態
        self.textual_node = None  # TextualのTreeNodeへの参照
        self.parent_node = None
    
    def add_child(self, child: 'ExpandableTraceNode'):
        """子ノードを追加"""
        child.parent_node = self
        child.depth = self.depth + 1
        child.path = self.path + [len(self.children)]
        self.children.append(child)
        return child
    
    def toggle_expansion(self):
        """展開/折りたたみを切り替え"""
        old_state = self.is_expanded
        self.is_expanded = not self.is_expanded
        
        # デバッグログ（必要時のみ）
        try:
            from .debug_logger import get_debug_logger
            logger = get_debug_logger()
            logger.trace("NODE", "toggle", f"{self.operation}: {old_state} → {self.is_expanded}", {
                "path": self.path,
                "children_count": len(self.children),
                "depth": self.depth
            })
        except:
            pass  # ログエラーは無視
        
        return self.is_expanded
    
    def set_execution_status(self, status: str, duration_ms: float = 0, result=None):
        """実行状態を更新"""
        self.execution_status = status
        self.duration_ms = duration_ms
        self.result = result
    
    @property
    def status_emoji(self) -> str:
        """実行状態の絵文字"""
        status_map = {
            "pending": "⚪",  # 待機中
            "running": "🟡",  # 実行中
            "completed": "🟢",  # 完了
            "error": "🔴"     # エラー
        }
        return status_map.get(self.execution_status, "❓")
    
    @property
    def expansion_emoji(self) -> str:
        """展開状態の絵文字"""
        if not self.children:
            return "  "  # 子ノードなしは空白
        return "▼" if self.is_expanded else "▶"
    
    @property
    def display_label(self) -> str:
        """表示用ラベル"""
        duration_text = f" ({self.duration_ms:.1f}ms)" if self.duration_ms > 0 else ""
        expansion = self.expansion_emoji
        status = self.status_emoji
        
        # S式を適切に短縮
        s_expr_display = self.s_expr
        if len(s_expr_display) > 60:
            s_expr_display = s_expr_display[:57] + "..."
        
        return f"{expansion} {status} {self.operation}: {s_expr_display}{duration_text}"
    
    def get_visible_children(self) -> List['ExpandableTraceNode']:
        """展開されている場合のみ子ノードを返す"""
        return self.children if self.is_expanded else []
    
    def find_node_by_path(self, path: List[int]) -> Optional['ExpandableTraceNode']:
        """パスを指定してノードを検索"""
        if not path:
            return self
            
        if path[0] >= len(self.children):
            return None
            
        return self.children[path[0]].find_node_by_path(path[1:])
    
    def collect_all_descendants(self) -> List['ExpandableTraceNode']:
        """すべての子孫ノードを収集（展開状態に関係なく）"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.collect_all_descendants())
        return descendants
    
    def to_dict(self) -> dict:
        """シリアライゼーション用辞書変換"""
        return {
            "operation": self.operation,
            "s_expr": self.s_expr,
            "is_expanded": self.is_expanded,
            "execution_status": self.execution_status,
            "duration_ms": self.duration_ms,
            "result": str(self.result) if self.result is not None else None,
            "path": self.path,
            "depth": self.depth,
            "children": [child.to_dict() for child in self.children]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExpandableTraceNode':
        """辞書からの復元"""
        node = cls(
            operation=data["operation"],
            s_expr=data["s_expr"]
        )
        node.is_expanded = data.get("is_expanded", True)
        node.execution_status = data.get("execution_status", "pending")
        node.duration_ms = data.get("duration_ms", 0)
        node.path = data.get("path", [])
        node.depth = data.get("depth", 0)
        
        # 子ノードを再帰的に復元
        for child_data in data.get("children", []):
            child = cls.from_dict(child_data)
            node.add_child(child)
        
        return node


class TraceViewer(App):
    """S式実行トレースビューア"""
    
    TITLE = "S式エージェント トレースビューア"
    
    # CSSを直接定義
    CSS = """
    .tree-panel {
        width: 50%;
        border: solid $primary;
        margin: 1;
    }
    
    .detail-panel {
        width: 50%;
        border: solid $secondary;
        margin: 1;
    }
    
    .panel-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #s_expr_tree {
        height: 1fr;
        scrollbar-gutter: stable;
    }
    
    #trace_details {
        height: 1fr;
    }
    
    #execution_log {
        height: 1fr;
    }
    
    Button {
        margin: 1;
        height: 2;
        max-height: 2;
    }
    
    #s_expr_input {
        margin: 1;
    }
    
    #status_display {
        margin: 1;
        text-align: center;
        text-style: italic;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "終了"),
        Binding("r", "refresh", "更新"),
        Binding("c", "clear", "クリア"),
        Binding("s", "step", "ステップ実行"),
        Binding("space", "toggle_expansion", "展開/折りたたみ"),
        Binding("enter", "select_node", "ノード選択"),
        Binding("up", "navigate_up", "上に移動"),
        Binding("down", "navigate_down", "下に移動"),
        Binding("ctrl+w", "back_to_workspace", "ワークスペースに戻る"),
        Binding("d", "toggle_debug_level", "デバッグレベル切替"),
        Binding("l", "show_debug_log", "デバッグログ表示"),
        # デバッグ制御キー
        Binding("f5", "debug_continue", "実行継続 (F5)"),
        Binding("f10", "debug_step_over", "ステップオーバー (F10)"),
        Binding("f11", "debug_step_into", "ステップイン (F11)"),
        Binding("shift+f11", "debug_step_out", "ステップアウト (Shift+F11)"),
        Binding("b", "toggle_breakpoint", "ブレークポイント切替 (B)"),
    ]
    
    # リアクティブ変数
    current_trace_count: reactive[int] = reactive(0)
    is_paused: reactive[bool] = reactive(False)
    
    def __init__(self, trace_logger: Optional[TraceLogger] = None):
        super().__init__()
        self.trace_logger = trace_logger or get_global_logger()
        self.execution_tree = None
        self.current_s_expr = None
        self.evaluator = ContextualEvaluator()
        self.env = Environment()
        self.last_processed_entry = -1
        
        # 新機能: 展開可能ツリー管理
        self.root_trace_node: Optional[ExpandableTraceNode] = None
        self.trace_node_map: Dict[tuple, ExpandableTraceNode] = {}  # パス -> ノードのマップ
        self.selected_node: Optional[ExpandableTraceNode] = None
        
        # デバッグログ機能
        from .debug_logger import get_debug_logger
        self.debug_logger = get_debug_logger()
        
        # デバッグ制御機能
        from ..core.debug_controller import get_debug_controller
        self.debug_controller = get_debug_controller()
        self.debug_enabled = False
        self.debug_logger.info("TUI", "init", "TraceViewer初期化開始", {
            "trace_logger": str(type(self.trace_logger).__name__),
            "evaluator": str(type(self.evaluator).__name__)
        })
        
    def compose(self) -> ComposeResult:
        """UIレイアウトを構成"""
        with TabbedContent(initial="trace"):
            with TabPane("実行トレース", id="trace"):
                with Horizontal():
                    # 左側：S式構造ツリー
                    with Vertical(classes="tree-panel"):
                        yield Label("S式実行ツリー", classes="panel-title")
                        yield Tree("Root", id="s_expr_tree")
                        
                    # 右側：詳細情報
                    with Vertical(classes="detail-panel"):
                        yield Label("実行詳細", classes="panel-title")
                        yield DataTable(id="trace_details")
                        
            with TabPane("ログ出力", id="logs"):
                yield Log(id="execution_log")
                
            with TabPane("入力/制御", id="control"):
                with Vertical():
                    yield Label("S式入力")
                    yield Input(placeholder="S式を入力してください...", id="s_expr_input")
                    with Horizontal():
                        yield Button("実行", id="execute_btn", variant="primary")
                        yield Button("ステップ実行", id="step_btn")
                        yield Button("クリア", id="clear_btn")
                    
                    yield Label("実行状態")
                    yield Static("待機中...", id="status_display")
        
        yield Header()
        yield Footer()
    
    def on_mount(self) -> None:
        """アプリ起動時の初期化"""
        self.debug_logger.info("TUI", "mount", "TraceViewer UI構築開始")
        
        # データテーブルの列を設定（MCP情報を追加）
        table = self.query_one("#trace_details", DataTable)
        table.add_columns("操作", "入力", "出力", "時間(ms)", "プロベナンス", "MCP", "状態")
        self.debug_logger.debug("TUI", "table_setup", "データテーブル列設定完了")
        
        # 定期更新を設定（100ms間隔）
        self.set_interval(0.1, self.update_trace_display)
        self.debug_logger.info("TUI", "interval_setup", "定期更新タイマー設定完了", {"interval_ms": 100})
        
        # ログ設定
        log = self.query_one("#execution_log", Log)
        log.write_line("トレースビューア開始")
        self.debug_logger.info("TUI", "mount", "TraceViewer UI構築完了")
    
    def update_trace_display(self) -> None:
        """トレース表示を更新（展開可能ツリー対応）"""
        if self.is_paused:
            return
            
        try:
            # 新しいトレースエントリを取得
            recent_entries = self.trace_logger.get_recent_entries(50)
            
            if len(recent_entries) > self.last_processed_entry + 1:
                # 新しいエントリを処理
                new_entries = recent_entries[self.last_processed_entry + 1:]
                
                self.debug_logger.log_trace_update(len(recent_entries), len(new_entries))
                
                # 展開可能ツリーを構築/更新
                self.build_expandable_tree(new_entries)
                
                # Textualツリーを更新
                self.refresh_textual_tree()
                
                # 従来の処理も実行（データテーブル、ログ）
                for entry in new_entries:
                    self.process_trace_entry(entry)
                
                self.last_processed_entry = len(recent_entries) - 1
                self.current_trace_count = len(recent_entries)
                
        except Exception as e:
            self.debug_logger.log_error_with_traceback(e, "update_trace_display",
                last_processed=self.last_processed_entry,
                paused=self.is_paused)
    
    def process_trace_entry(self, entry: TraceEntry) -> None:
        """トレースエントリを処理して表示を更新"""
        # データテーブルに追加
        table = self.query_one("#trace_details", DataTable)
        
        input_str = str(entry.input)[:50] + "..." if len(str(entry.input)) > 50 else str(entry.input)
        output_str = str(entry.output)[:50] + "..." if len(str(entry.output)) > 50 else str(entry.output)
        
        # MCP情報を取得
        provenance = entry.metadata.provenance.value if hasattr(entry.metadata, 'provenance') else "builtin"
        mcp_info = ""
        
        if hasattr(entry.metadata, 'mcp_server') and entry.metadata.mcp_server:
            mcp_tool = getattr(entry.metadata, 'mcp_tool', 'unknown')
            mcp_duration = getattr(entry.metadata, 'mcp_duration_ms', 0)
            mcp_success = getattr(entry.metadata, 'mcp_success', False)
            mcp_status = "✅" if mcp_success else "❌"
            mcp_info = f"{mcp_tool} ({mcp_duration:.1f}ms) {mcp_status}"
        
        table.add_row(
            entry.operation,
            input_str,
            output_str,
            f"{entry.duration_ms:.1f}",
            provenance,
            mcp_info or "-",
            "✅" if entry.metadata.error is None else "❌"
        )
        
        # ログに追加（MCP情報を含む）
        log = self.query_one("#execution_log", Log)
        log_text = f"[{entry.timestamp}] {entry.operation}: {entry.explanation}"
        
        # MCP詳細情報を追加
        if hasattr(entry.metadata, 'mcp_server') and entry.metadata.mcp_server:
            mcp_server = entry.metadata.mcp_server
            mcp_tool = getattr(entry.metadata, 'mcp_tool', 'unknown')
            mcp_duration = getattr(entry.metadata, 'mcp_duration_ms', 0)
            mcp_success = getattr(entry.metadata, 'mcp_success', False)
            log_text += f" [MCP: {mcp_server}/{mcp_tool}, {mcp_duration:.1f}ms, {'SUCCESS' if mcp_success else 'FAILED'}]"
            
            # MCPパラメータも表示
            if hasattr(entry.metadata, 'mcp_params') and entry.metadata.mcp_params:
                params_str = str(entry.metadata.mcp_params)[:100]
                log_text += f" params: {params_str}"
        
        if entry.metadata.error:
            log_text += f" (ERROR: {entry.metadata.error})"
        log.write_line(log_text)
        
        # S式ツリーの更新
        self.update_s_expr_tree(entry)
    
    def update_s_expr_tree(self, entry: TraceEntry) -> None:
        """S式ツリー表示を更新"""
        tree = self.query_one("#s_expr_tree", Tree)
        
        # パスに基づいてノードを特定・更新
        current_node = tree.root
        
        try:
            for path_idx in entry.path:
                if path_idx < len(current_node.children):
                    current_node = current_node.children[path_idx]
                else:
                    # 新しいノードを作成
                    node_label = self.format_node_label(entry.input, entry.operation)
                    new_node = current_node.add(node_label)
                    current_node = new_node
            
            # ノードの状態を更新
            status_emoji = "✅" if entry.metadata.error is None else "❌"
            duration_text = f" ({entry.duration_ms:.1f}ms)" if entry.duration_ms > 0 else ""
            current_node.set_label(f"{status_emoji} {entry.operation}{duration_text}")
            
        except Exception as e:
            log = self.query_one("#execution_log", Log)
            log.write_line(f"ツリー更新エラー: {e}")
    
    def format_node_label(self, input_data: Any, operation: str) -> str:
        """ノードラベルをフォーマット（完全なS式表示対応）"""
        if isinstance(input_data, dict) and "s_expr" in input_data:
            # S式評価の場合、完全なS式を表示
            s_expr = input_data["s_expr"]
            return f"{operation}: {s_expr}"
        elif isinstance(input_data, list) and len(input_data) > 0:
            # S式リストの場合、完全な形式で表示
            if len(input_data) == 1:
                return f"{operation}: ({input_data[0]})"
            elif len(input_data) == 2:
                return f"{operation}: ({input_data[0]} {input_data[1]})"
            else:
                args = " ".join(str(arg) for arg in input_data[1:])
                return f"{operation}: ({input_data[0]} {args})"
        else:
            # その他の場合、適切に省略
            input_str = str(input_data)
            if len(input_str) > 50:
                input_str = input_str[:47] + "..."
            return f"{operation}: {input_str}"

    def build_expandable_tree(self, trace_entries: List[TraceEntry]) -> None:
        """トレースエントリから展開可能ツリーを構築"""
        if not trace_entries:
            self.debug_logger.trace("TREE", "build", "空のトレースエントリ - ツリー構築スキップ")
            return
            
        try:
            # ルートノードを作成
            if self.root_trace_node is None:
                self.root_trace_node = ExpandableTraceNode(
                    operation="root",
                    s_expr="S式実行ルート"
                )
                self.trace_node_map[()] = self.root_trace_node
                self.debug_logger.debug("TREE", "build", "ルートノード作成完了")
            
            # 各トレースエントリを処理
            for entry in trace_entries:
                self.add_trace_entry_to_tree(entry)
                
            self.debug_logger.debug("TREE", "build", f"ツリー構築完了", {
                "entries_processed": len(trace_entries),
                "total_nodes": len(self.trace_node_map)
            })
            
        except Exception as e:
            self.debug_logger.log_error_with_traceback(e, "build_expandable_tree",
                entries_count=len(trace_entries),
                existing_nodes=len(self.trace_node_map))
    
    def add_trace_entry_to_tree(self, entry: TraceEntry) -> None:
        """トレースエントリをツリーに追加"""
        path_tuple = tuple(entry.path)
        
        # 既存ノードをチェック
        if path_tuple in self.trace_node_map:
            node = self.trace_node_map[path_tuple]
            node.set_execution_status(
                "completed" if entry.metadata.error is None else "error",
                entry.duration_ms,
                entry.output
            )
            node.trace_entry = entry
            return
        
        # 新しいノードを作成
        s_expr_str = self.extract_s_expr_from_entry(entry)
        node = ExpandableTraceNode(
            operation=entry.operation,
            s_expr=s_expr_str
        )
        node.trace_entry = entry
        node.path = entry.path.copy()
        
        # 実行状態を設定
        if entry.duration_ms > 0:
            status = "completed" if entry.metadata.error is None else "error"
        else:
            status = "running"
        node.set_execution_status(status, entry.duration_ms, entry.output)
        
        # 親ノードを探して追加
        parent_path = tuple(entry.path[:-1]) if entry.path else ()
        parent_node = self.trace_node_map.get(parent_path, self.root_trace_node)
        
        if parent_node:
            parent_node.add_child(node)
            self.trace_node_map[path_tuple] = node
    
    def extract_s_expr_from_entry(self, entry: TraceEntry) -> str:
        """トレースエントリからS式文字列を抽出"""
        if isinstance(entry.input, dict) and "s_expr" in entry.input:
            return str(entry.input["s_expr"])
        elif isinstance(entry.input, list) and len(entry.input) > 0:
            if len(entry.input) == 1:
                return f"({entry.input[0]})"
            else:
                args = " ".join(str(arg) for arg in entry.input[1:])
                return f"({entry.input[0]} {args})"
        else:
            return str(entry.input)
    
    def refresh_textual_tree(self) -> None:
        """TextualのTreeウィジェットを更新"""
        tree_widget = self.query_one("#s_expr_tree", Tree)
        tree_widget.clear()
        
        if self.root_trace_node:
            self.populate_textual_tree_node(tree_widget.root, self.root_trace_node)
    
    def populate_textual_tree_node(self, textual_node, trace_node: ExpandableTraceNode) -> None:
        """TextualのTreeNodeに展開可能ノードの内容を設定"""
        # ノードラベルを設定
        textual_node.set_label(trace_node.display_label)
        trace_node.textual_node = textual_node
        
        # 展開されている場合のみ子ノードを追加
        if trace_node.is_expanded:
            for child_trace_node in trace_node.children:
                child_textual_node = textual_node.add("")
                self.populate_textual_tree_node(child_textual_node, child_trace_node)
    
    def find_trace_node_by_textual_node(self, textual_node) -> Optional[ExpandableTraceNode]:
        """TextualのNodeから対応するTraceNodeを検索"""
        if not self.root_trace_node:
            return None
            
        def search_recursive(trace_node: ExpandableTraceNode) -> Optional[ExpandableTraceNode]:
            if trace_node.textual_node == textual_node:
                return trace_node
            for child in trace_node.children:
                result = search_recursive(child)
                if result:
                    return result
            return None
        
        return search_recursive(self.root_trace_node)

    def action_toggle_expansion(self) -> None:
        """Spaceキー: 選択ノードの展開/折りたたみ切り替え"""
        self.debug_logger.log_key_event("Space", "toggle_expansion")
        
        tree_widget = self.query_one("#s_expr_tree", Tree)
        cursor_node = tree_widget.cursor_node
        
        if cursor_node:
            trace_node = self.find_trace_node_by_textual_node(cursor_node)
            if trace_node and trace_node.children:
                old_state = trace_node.is_expanded
                trace_node.toggle_expansion()
                self.refresh_textual_tree()
                
                # ステータス更新
                expansion_status = "展開" if trace_node.is_expanded else "折りたたみ"
                self.notify(f"ノード{expansion_status}: {trace_node.operation}")
                
                self.debug_logger.log_node_operation("toggle_expansion", trace_node.path, 
                    f"{trace_node.operation}: {old_state} → {trace_node.is_expanded}",
                    children_count=len(trace_node.children))
            else:
                self.debug_logger.debug("KEY", "toggle_expansion", "選択ノードに子がないため展開/折りたたみ不可")
        else:
            self.debug_logger.debug("KEY", "toggle_expansion", "カーソルノードが選択されていません")
    
    def action_select_node(self) -> None:
        """Enterキー: ノード選択とトレース詳細表示"""
        self.debug_logger.log_key_event("Enter", "select_node")
        
        tree_widget = self.query_one("#s_expr_tree", Tree)
        cursor_node = tree_widget.cursor_node
        
        if cursor_node:
            trace_node = self.find_trace_node_by_textual_node(cursor_node)
            if trace_node:
                self.selected_node = trace_node
                self.show_node_details(trace_node)
                self.notify(f"選択: {trace_node.operation}")
                
                self.debug_logger.log_node_operation("select", trace_node.path,
                    f"ノード選択: {trace_node.operation}",
                    status=trace_node.execution_status,
                    duration_ms=trace_node.duration_ms)
            else:
                self.debug_logger.debug("KEY", "select_node", "対応するTraceNodeが見つかりません")
        else:
            self.debug_logger.debug("KEY", "select_node", "カーソルノードが選択されていません")
    
    def action_navigate_up(self) -> None:
        """上矢印キー: ツリー内で上に移動"""
        tree_widget = self.query_one("#s_expr_tree", Tree)
        tree_widget.action_cursor_up()
    
    def action_navigate_down(self) -> None:
        """下矢印キー: ツリー内で下に移動"""
        tree_widget = self.query_one("#s_expr_tree", Tree)
        tree_widget.action_cursor_down()
    
    def show_node_details(self, node: ExpandableTraceNode) -> None:
        """選択されたノードの詳細を表示"""
        table = self.query_one("#trace_details", DataTable)
        
        # テーブルをクリアして選択ノードの詳細を表示
        table.clear()
        
        if node.trace_entry:
            entry = node.trace_entry
            
            # 基本情報
            table.add_row("操作", entry.operation)
            table.add_row("入力", str(entry.input)[:100])
            table.add_row("出力", str(entry.output)[:100])
            table.add_row("実行時間", f"{entry.duration_ms:.1f}ms")
            table.add_row("状態", node.execution_status)
            table.add_row("パス", str(entry.path))
            
            # MCP情報があれば表示
            if hasattr(entry.metadata, 'mcp_server') and entry.metadata.mcp_server:
                table.add_row("MCPサーバー", entry.metadata.mcp_server)
                table.add_row("MCPツール", getattr(entry.metadata, 'mcp_tool', 'unknown'))
                mcp_duration = getattr(entry.metadata, 'mcp_duration_ms', 0)
                table.add_row("MCP実行時間", f"{mcp_duration:.1f}ms")
            
            # エラー情報
            if entry.metadata.error:
                table.add_row("エラー", str(entry.metadata.error)[:200])
        else:
            table.add_row("情報", "トレースエントリなし")
            table.add_row("子ノード数", str(len(node.children)))
            table.add_row("展開状態", "展開" if node.is_expanded else "折りたたみ")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        if event.button.id == "execute_btn":
            await self.execute_s_expression()
        elif event.button.id == "step_btn":
            await self.step_execute()
        elif event.button.id == "clear_btn":
            self.clear_display()
    
    async def execute_s_expression(self) -> None:
        """S式を実行"""
        start_time = time.time()
        input_widget = self.query_one("#s_expr_input", Input)
        s_expr_text = input_widget.value.strip()
        
        self.debug_logger.info("EVAL", "start", f"S式実行開始", {"s_expr": s_expr_text})
        
        if not s_expr_text:
            self.debug_logger.warn("EVAL", "empty", "空のS式入力")
            return
        
        status = self.query_one("#status_display", Static)
        status.update("実行中...")
        self.debug_logger.debug("UI", "status_update", "ステータス更新: 実行中")
        
        try:
            # トレースログをクリア
            self.trace_logger.clear()
            self.clear_display()
            self.debug_logger.debug("EVAL", "clear", "トレースログとUI表示をクリア")
            
            # S式をパースして実行
            parse_start = time.time()
            parsed_expr = parse_s_expression(s_expr_text)
            parse_duration = (time.time() - parse_start) * 1000
            self.debug_logger.log_performance("parse", parse_duration, {"parsed": str(parsed_expr)})
            
            eval_start = time.time()
            result = self.evaluator.evaluate_with_context(parsed_expr, self.env)
            eval_duration = (time.time() - eval_start) * 1000
            self.debug_logger.log_s_expr_evaluation(s_expr_text, "evaluate", result, duration_ms=eval_duration)
            
            status.update(f"完了: {result}")
            self.debug_logger.debug("UI", "status_update", f"ステータス更新: 完了", {"result": str(result)})
            
            log = self.query_one("#execution_log", Log)
            log.write_line(f"実行完了: {result}")
            
            total_duration = (time.time() - start_time) * 1000
            self.debug_logger.log_performance("execute_total", total_duration, {
                "s_expr": s_expr_text,
                "result": str(result),
                "parse_ms": parse_duration,
                "eval_ms": eval_duration
            })
            
        except Exception as e:
            error_duration = (time.time() - start_time) * 1000
            status.update(f"エラー: {e}")
            log = self.query_one("#execution_log", Log)
            log.write_line(f"実行エラー: {e}")
            
            self.debug_logger.log_error_with_traceback(e, "execute_s_expression", 
                s_expr=s_expr_text, duration_ms=error_duration)
    
    async def step_execute(self) -> None:
        """ステップ実行（未実装）"""
        status = self.query_one("#status_display", Static)
        status.update("ステップ実行は未実装")
    
    def clear_display(self) -> None:
        """表示をクリア"""
        # データテーブルをクリア
        table = self.query_one("#trace_details", DataTable)
        table.clear()
        
        # ツリーをクリア
        tree = self.query_one("#s_expr_tree", Tree)
        tree.clear()
        tree.root.set_label("Root")
        
        # ログをクリア
        log = self.query_one("#execution_log", Log)
        log.clear()
        
        # 状態リセット
        self.last_processed_entry = -1
        self.current_trace_count = 0
        
        status = self.query_one("#status_display", Static)
        status.update("待機中...")
    
    def action_refresh(self) -> None:
        """表示を手動更新"""
        self.update_trace_display()
    
    def action_clear(self) -> None:
        """表示をクリア"""
        self.clear_display()
    
    def action_step(self) -> None:
        """ステップ実行"""
        self.run_action("step_execute")
    
    def action_toggle_pause(self) -> None:
        """一時停止を切り替え"""
        self.is_paused = not self.is_paused
        status = self.query_one("#status_display", Static)
        if self.is_paused:
            status.update("一時停止中...")
        else:
            status.update("実行中...")

    
    def action_back_to_workspace(self) -> None:
        """ワークスペースに戻る"""
        # トレースビューアを終了してメインアプリのワークスペースタブに戻る
        self.debug_logger.info("UI", "exit", "ワークスペースに戻る")
        self.notify("ワークスペースに戻ります...")
        self.debug_logger.shutdown()
        self.exit()
    
    def action_toggle_debug_level(self) -> None:
        """Dキー: デバッグログレベルを循環切り替え"""
        from .debug_logger import DebugLogLevel
        
        current_level = self.debug_logger.min_level
        levels = list(DebugLogLevel)
        current_index = levels.index(current_level)
        next_index = (current_index + 1) % len(levels)
        new_level = levels[next_index]
        
        self.debug_logger.set_log_level(new_level)
        
        # レベル別のアイコンで通知
        level_icons = {
            DebugLogLevel.TRACE: "🔍",
            DebugLogLevel.DEBUG: "🐛", 
            DebugLogLevel.INFO: "ℹ️",
            DebugLogLevel.WARN: "⚠️",
            DebugLogLevel.ERROR: "❌"
        }
        
        icon = level_icons.get(new_level, "📝")
        self.notify(f"{icon} デバッグレベル: {new_level.name}")
        
        # 即座にログを更新表示
        log_widget = self.query_one("#execution_log", Log)
        log_widget.write_line(f"🔄 ログレベル変更: {current_level.name} → {new_level.name}")
        
        self.debug_logger.info("UI", "level_change", f"{icon} {new_level.name}レベルに変更されました")
        
        # TRACEレベル時は特別なメッセージ
        if new_level == DebugLogLevel.TRACE:
            self.debug_logger.trace("UI", "level_change", "🔍 TRACEレベルに変更されました")
        elif new_level == DebugLogLevel.ERROR:
            self.debug_logger.error("UI", "visible", "❌ ERRORレベルなので表示されます")
    
    def action_show_debug_log(self) -> None:
        """Lキー: 詳細デバッグログを全画面表示"""
        recent_logs = self.debug_logger.get_recent_logs(50)  # より多くのログを取得
        
        log_widget = self.query_one("#execution_log", Log)
        log_widget.clear()  # 既存ログをクリア
        
        # ヘッダー情報
        log_widget.write_line("🔍 === TUIデバッグログ (最新50件) ===")
        log_widget.write_line(f"📊 ログレベル: {self.debug_logger.min_level.name}")
        log_widget.write_line(f"📁 ログファイル: {self.debug_logger.log_file}")
        log_widget.write_line(f"⏰ 取得時刻: {datetime.now().strftime('%H:%M:%S')}")
        log_widget.write_line("")
        
        # ログレベル別統計
        level_counts = {}
        for entry in recent_logs:
            level_counts[entry.level.name] = level_counts.get(entry.level.name, 0) + 1
        
        if level_counts:
            stats = ", ".join(f"{level}: {count}件" for level, count in level_counts.items())
            log_widget.write_line(f"📈 統計: {stats}")
            log_widget.write_line("")
        
        # ログエントリ表示
        if recent_logs:
            for i, entry in enumerate(recent_logs, 1):
                formatted = self.debug_logger._format_message(entry)
                log_widget.write_line(f"{i:2d}. {formatted}")
        else:
            log_widget.write_line("❌ ログエントリが見つかりません")
            log_widget.write_line("💡 ヒント: 環境変数 S_STYLE_DEBUG_LEVEL=TRACE で詳細ログを有効化")
            
        log_widget.write_line("")
        log_widget.write_line("🎮 操作: D キー(レベル切替), L キー(更新), ESC (戻る)")
        log_widget.write_line("=== デバッグログ終了 ===")
        
        self.debug_logger.info("UI", "show_log", f"デバッグログ表示: {len(recent_logs)}件", {
            "log_level": self.debug_logger.min_level.name,
            "total_entries": len(self.debug_logger.entries)
        })

    
    # デバッグ制御アクション
    def action_debug_continue(self) -> None:
        """F5キー: 実行継続"""
        if self.debug_enabled:
            self.debug_controller.continue_execution()
            self.notify("実行継続")
            self.debug_logger.info("DEBUG", "continue", "F5: 実行継続")
        else:
            self.notify("デバッグモードが無効です")
    
    def action_debug_step_over(self) -> None:
        """F10キー: ステップオーバー"""
        if self.debug_enabled:
            self.debug_controller.step_over()
            self.notify("ステップオーバー")
            self.debug_logger.info("DEBUG", "step_over", "F10: ステップオーバー")
        else:
            self.notify("デバッグモードが無効です")
    
    def action_debug_step_into(self) -> None:
        """F11キー: ステップイン"""
        if self.debug_enabled:
            self.debug_controller.step_into()
            self.notify("ステップイン")
            self.debug_logger.info("DEBUG", "step_into", "F11: ステップイン")
        else:
            self.notify("デバッグモードが無効です")
    
    def action_debug_step_out(self) -> None:
        """Shift+F11キー: ステップアウト"""
        if self.debug_enabled:
            self.debug_controller.step_out()
            self.notify("ステップアウト")
            self.debug_logger.info("DEBUG", "step_out", "Shift+F11: ステップアウト")
        else:
            self.notify("デバッグモードが無効です")
    
    def action_toggle_breakpoint(self) -> None:
        """Bキー: ブレークポイント切り替え"""
        tree_widget = self.query_one("#s_expr_tree", Tree)
        cursor_node = tree_widget.cursor_node
        
        if cursor_node:
            trace_node = self.find_trace_node_by_textual_node(cursor_node)
            if trace_node:
                # 既存のブレークポイントをチェック
                existing_bp = None
                for bp in self.debug_controller.get_breakpoints():
                    if bp.path == trace_node.path and bp.operation == trace_node.operation:
                        existing_bp = bp
                        break
                
                if existing_bp:
                    # ブレークポイント削除
                    self.debug_controller.remove_breakpoint(existing_bp.id)
                    self.notify(f"ブレークポイント削除: {trace_node.operation}")
                    self.debug_logger.info("DEBUG", "remove_breakpoint", 
                        f"ブレークポイント削除: {trace_node.operation}", {"path": trace_node.path})
                else:
                    # ブレークポイント追加
                    bp = self.debug_controller.add_breakpoint(trace_node.path, trace_node.operation)
                    self.notify(f"ブレークポイント追加: {trace_node.operation}")
                    self.debug_logger.info("DEBUG", "add_breakpoint", 
                        f"ブレークポイント追加: {trace_node.operation}", {
                            "path": trace_node.path, 
                            "breakpoint_id": bp.id
                        })
                
                # ツリー表示更新
                self.refresh_textual_tree()
            else:
                self.notify("トレースノードが見つかりません")
        else:
            self.notify("ノードが選択されていません")
    
    def enable_debug_mode(self) -> None:
        """デバッグモード有効化"""
        self.debug_enabled = True
        # AsyncContextualEvaluatorとの統合
        if hasattr(self.evaluator, 'enable_debug_mode'):
            self.evaluator.enable_debug_mode(self.debug_controller)
        
        # デバッグコールバック設定
        self.debug_controller.set_debug_callbacks(
            on_breakpoint_hit=self.on_breakpoint_hit,
            on_step_complete=self.on_step_complete,
            on_execution_paused=self.on_execution_paused
        )
        
        self.debug_controller.start_debug_session()
        self.notify("デバッグモード有効")
        self.debug_logger.info("DEBUG", "enable", "デバッグモード有効化")
    
    def disable_debug_mode(self) -> None:
        """デバッグモード無効化"""
        self.debug_enabled = False
        if hasattr(self.evaluator, 'disable_debug_mode'):
            self.evaluator.disable_debug_mode()
        
        self.debug_controller.stop_debug_session()
        self.notify("デバッグモード無効")
        self.debug_logger.info("DEBUG", "disable", "デバッグモード無効化")
    
    async def on_breakpoint_hit(self, frame, breakpoint) -> None:
        """ブレークポイントヒット時のコールバック"""
        self.notify(f"ブレークポイント: {frame.operation}")
        
        # ブレークポイントの詳細をログに表示
        log = self.query_one("#execution_log", Log)
        log.write_line(f"🔴 ブレークポイントヒット: {frame.operation}")
        log.write_line(f"   パス: {frame.path}")
        log.write_line(f"   S式: {frame.s_expr}")
        
        self.debug_logger.warn("DEBUG", "breakpoint_hit", 
            f"ブレークポイントヒット: {frame.operation}", {
                "path": frame.path,
                "breakpoint_id": breakpoint.id if breakpoint else None
            })
    
    async def on_step_complete(self, frame) -> None:
        """ステップ実行完了時のコールバック"""
        self.notify(f"ステップ完了: {frame.operation}")
        self.debug_logger.debug("DEBUG", "step_complete", f"ステップ完了: {frame.operation}")
    
    async def on_execution_paused(self, frame) -> None:
        """実行一時停止時のコールバック"""
        self.notify("実行一時停止")
        self.debug_logger.info("DEBUG", "paused", "実行一時停止")
    
    def get_debug_status(self) -> str:
        """デバッグ状態文字列取得"""
        if not self.debug_enabled:
            return "デバッグ無効"
        
        state = self.debug_controller.get_debug_state()
        return f"デバッグ: {state['state']} | {state['step_mode']}"





async def launch_trace_viewer(trace_logger: Optional[TraceLogger] = None):
    """トレースビューアを起動"""
    app = TraceViewer(trace_logger)
    await app.run_async()


if __name__ == "__main__":
    import asyncio
    
    # テスト用のトレースログを生成
    from ..core.trace_logger import configure_trace_logging
    
    logger = configure_trace_logging("trace_test.jsonl")
    
    # サンプルトレースエントリを追加
    entry_id = logger.start_operation("test", "(+ 2 3)", "テスト実行")
    logger.end_operation(entry_id, 5)
    
    # ビューアを起動
    asyncio.run(launch_trace_viewer(logger))