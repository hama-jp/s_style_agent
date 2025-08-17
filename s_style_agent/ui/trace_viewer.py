"""
S式実行トレースビューア（Textualベース）

リアルタイムでS式評価の実行状況を表示するTUIアプリケーション
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import time

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


class SExpressionNode:
    """S式ノードの表示用クラス"""
    def __init__(self, data: Any, path: List[int], depth: int = 0):
        self.data = data
        self.path = path
        self.depth = depth
        self.children: List['SExpressionNode'] = []
        self.execution_state = "pending"  # pending, executing, completed, error
        self.result = None
        self.duration_ms = 0
        
    def add_child(self, child: 'SExpressionNode'):
        self.children.append(child)
    
    @property
    def display_text(self) -> str:
        """表示用のテキストを生成"""
        if isinstance(self.data, str):
            return f"'{self.data}'"
        elif isinstance(self.data, list) and len(self.data) > 0:
            op = self.data[0]
            arg_count = len(self.data) - 1
            return f"({op} ...{arg_count}args)"
        else:
            return str(self.data)
    
    @property
    def status_emoji(self) -> str:
        """実行状態の絵文字"""
        status_map = {
            "pending": "⏳",
            "executing": "🔄", 
            "completed": "✅",
            "error": "❌"
        }
        return status_map.get(self.execution_state, "❓")


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
        Binding("space", "toggle_pause", "一時停止"),
        Binding("ctrl+w", "back_to_workspace", "ワークスペースに戻る"),
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
        # データテーブルの列を設定（MCP情報を追加）
        table = self.query_one("#trace_details", DataTable)
        table.add_columns("操作", "入力", "出力", "時間(ms)", "プロベナンス", "MCP", "状態")
        
        # 定期更新を設定（100ms間隔）
        self.set_interval(0.1, self.update_trace_display)
        
        # ログ設定
        log = self.query_one("#execution_log", Log)
        log.write_line("トレースビューア開始")
    
    def update_trace_display(self) -> None:
        """トレース表示を更新"""
        if self.is_paused:
            return
            
        # 新しいトレースエントリを取得
        recent_entries = self.trace_logger.get_recent_entries(50)
        
        if len(recent_entries) > self.last_processed_entry + 1:
            # 新しいエントリを処理
            for i in range(self.last_processed_entry + 1, len(recent_entries)):
                entry = recent_entries[i]
                self.process_trace_entry(entry)
            
            self.last_processed_entry = len(recent_entries) - 1
            self.current_trace_count = len(recent_entries)
    
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
        input_widget = self.query_one("#s_expr_input", Input)
        s_expr_text = input_widget.value.strip()
        
        if not s_expr_text:
            return
        
        status = self.query_one("#status_display", Static)
        status.update("実行中...")
        
        try:
            # トレースログをクリア
            self.trace_logger.clear()
            self.clear_display()
            
            # S式をパースして実行
            parsed_expr = parse_s_expression(s_expr_text)
            result = self.evaluator.evaluate_with_context(parsed_expr, self.env)
            
            status.update(f"完了: {result}")
            
            log = self.query_one("#execution_log", Log)
            log.write_line(f"実行完了: {result}")
            
        except Exception as e:
            status.update(f"エラー: {e}")
            log = self.query_one("#execution_log", Log)
            log.write_line(f"実行エラー: {e}")
    
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
        self.notify("ワークスペースに戻ります...")
        self.exit()





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