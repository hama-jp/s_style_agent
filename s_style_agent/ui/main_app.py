"""
S式エージェント メインTUIアプリケーション

Textualベースの4タブ構成TUIアプリケーション
"""

from typing import Optional, Dict, Any, List
import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, TabbedContent, TabPane, 
    Button, Input, Label, DataTable, Log, Tree
)
from textual.binding import Binding
from textual.reactive import reactive

# 共通サービスをインポート
from ..core.agent_service import AgentService

# TUIタブコンポーネント
from .dashboard import DashboardTab
from .workspace import WorkspaceTab
from .history import HistoryTab
from .settings import SettingsTab


class MainTUIApp(App):
    """S式エージェント メインTUIアプリケーション"""
    
    TITLE = "S式エージェント システム"
    SUB_TITLE = "Terminal User Interface"
    
    CSS = """
    .main-container {
        height: 100vh;
        width: 100vw;
    }
    
    .tab-content {
        height: 1fr;
        width: 1fr;
        margin: 1;
    }
    
    .status-bar {
        dock: bottom;
        height: 3;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    
    .quick-actions {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    .system-info {
        text-align: center;
        text-style: italic;
        color: $text-muted;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+q", "quit", "終了", priority=True),
        Binding("ctrl+c", "switch_to_cli", "CLIモード", priority=True),
        Binding("f1", "show_help", "ヘルプ"),
        Binding("f2", "quick_generate", "S式生成"),
        Binding("f3", "show_history", "履歴"),
        Binding("f4", "show_settings", "設定"),
        Binding("f5", "execute", "実行"),
        Binding("ctrl+g", "focus_generation", "生成モード"),
        Binding("ctrl+e", "focus_execution", "実行モード"),
        Binding("ctrl+h", "focus_history", "履歴表示"),
        Binding("ctrl+t", "show_trace", "トレース表示"),
    ]
    
    # リアクティブ変数
    current_mode: reactive[str] = reactive("async")
    mcp_status: reactive[str] = reactive("未初期化")
    system_status: reactive[str] = reactive("起動中")
    
    def __init__(self):
        super().__init__()
        
        # 共通サービスを初期化
        self.agent_service = AgentService(use_async=True)
        
        # 便利なプロパティ
        self.use_async = self.agent_service.use_async
        self.session_history = self.agent_service.session_history
        self.mcp_initialized = self.agent_service.mcp_initialized
        self.trace_logger = self.agent_service.trace_logger
        
        # タブコンポーネントの初期化（後で設定）
        self.dashboard = None
        self.workspace = None
        self.history_tab = None
        self.settings_tab = None
    
    def compose(self) -> ComposeResult:
        """UIレイアウトを構成"""
        yield Header()
        
        with Container(classes="main-container"):
            with TabbedContent(initial="dashboard"):
                with TabPane("ダッシュボード", id="dashboard"):
                    yield DashboardTab(app=self)
                    
                with TabPane("ワークスペース", id="workspace"):
                    yield WorkspaceTab(app=self)
                    
                with TabPane("履歴管理", id="history"):
                    yield HistoryTab(app=self)
                    
                with TabPane("システム設定", id="settings"):
                    yield SettingsTab(app=self)
            
            # クイックアクションバー
            with Container(classes="quick-actions"):
                yield Button("ヘルプ (F1)", id="help_btn", variant="primary")
                yield Button("生成 (F2)", id="generate_btn", variant="success")
                yield Button("履歴 (F3)", id="history_btn")
                yield Button("設定 (F4)", id="settings_btn")
                yield Button("実行 (F5)", id="execute_btn", variant="warning")
            
            # ステータスバー
            with Container(classes="status-bar"):
                yield Static(f"モード: {self.current_mode} | MCP: {self.mcp_status} | ステータス: {self.system_status}", 
                           classes="system-info", id="status_info")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """アプリ起動時の初期化"""
        # MCP自動初期化
        await self.init_mcp_system()
        
        # システム状態更新
        self.system_status = "稼働中"
        self.update_status_bar()
        
        # ウェルカムメッセージ
        self.notify("S式エージェントシステムが起動しました", severity="information")
    
    async def init_mcp_system(self) -> None:
        """MCPシステムの初期化"""
        success = await self.agent_service.init_mcp_system()
        if success:
            self.mcp_status = "正常"
            self.mcp_initialized = self.agent_service.mcp_initialized
            self.notify("MCPシステムが初期化されました", severity="information")
        else:
            self.mcp_status = "エラー"
            self.notify("MCP初期化失敗", severity="error")
    
    def update_status_bar(self) -> None:
        """ステータスバーを更新"""
        status_widget = self.query_one("#status_info", Static)
        status_text = f"モード: {self.current_mode} | MCP: {self.mcp_status} | ステータス: {self.system_status}"
        status_widget.update(status_text)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        button_id = event.button.id
        
        if button_id == "help_btn":
            await self.action_show_help()
        elif button_id == "generate_btn":
            await self.action_quick_generate()
        elif button_id == "history_btn":
            await self.action_show_history()
        elif button_id == "settings_btn":
            await self.action_show_settings()
        elif button_id == "execute_btn":
            await self.action_execute()
    
    # アクション実装
    async def action_show_help(self) -> None:
        """ヘルプを表示"""
        help_text = """
S式エージェントシステム - ヘルプ

【キーボードショートカット】
F1: ヘルプ表示      F2: S式生成
F3: 履歴表示        F4: 設定表示
F5: 実行            

Ctrl+G: 生成モード  Ctrl+E: 実行モード
Ctrl+H: 履歴表示    Ctrl+T: トレース表示
Ctrl+C: CLIモード   Ctrl+Q: 終了

【基本操作】
1. ワークスペースタブでS式を入力・生成
2. 実行ボタンまたはF5で実行
3. 履歴タブで過去の実行結果を確認
4. 設定タブでシステム設定を変更
        """
        self.notify(help_text, title="ヘルプ", timeout=10)
    
    async def action_quick_generate(self) -> None:
        """クイックS式生成"""
        # ワークスペースタブに切り替えて生成モードに
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "workspace"
        
        # ワークスペースの生成機能を呼び出し
        workspace = self.query_one(WorkspaceTab)
        await workspace.focus_generation_input()
    
    async def action_show_history(self) -> None:
        """履歴表示"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "history"
    
    async def action_show_settings(self) -> None:
        """設定表示"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "settings"
    
    async def action_execute(self) -> None:
        """実行"""
        # 現在のタブに応じて実行処理
        tabbed_content = self.query_one(TabbedContent)
        if tabbed_content.active == "workspace":
            workspace = self.query_one(WorkspaceTab)
            await workspace.execute_current_expression()
    
    async def action_switch_to_cli(self) -> None:
        """CLIモードに切り替え"""
        self.notify("CLIモードに切り替えます...")
        # TODO: CLIモード切り替え実装
        # 現在は通知のみ
        await asyncio.sleep(1)
        self.exit()
    
    async def action_focus_generation(self) -> None:
        """生成モードにフォーカス"""
        await self.action_quick_generate()
    
    async def action_focus_execution(self) -> None:
        """実行モードにフォーカス"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "workspace"
        workspace = self.query_one(WorkspaceTab)
        await workspace.focus_execution_area()
    
    async def action_focus_history(self) -> None:
        """履歴表示にフォーカス"""
        await self.action_show_history()
    
    async def action_show_trace(self) -> None:
        """トレース表示"""
        # トレースビューアを起動
        from .trace_viewer import launch_trace_viewer
        await launch_trace_viewer(self.trace_logger)
    
    # 共通機能メソッド（AgentServiceへのデリゲート）
    async def evaluate_s_expression(self, s_expr: str, context: Optional[Dict] = None) -> Any:
        """S式を評価"""
        return await self.agent_service.evaluate_s_expression(s_expr, context)
    
    async def generate_s_expression(self, natural_language: str) -> str:
        """自然言語からS式を生成"""
        return await self.agent_service.generate_s_expression(natural_language)
    
    def add_to_history(self, operation: str, input_data: Any, output_data: Any, success: bool = True) -> None:
        """履歴に項目を追加"""
        self.agent_service.add_to_history(operation, input_data, output_data, success)
    
    def get_session_history(self) -> List[Dict[str, Any]]:
        """セッション履歴を取得"""
        return self.agent_service.get_session_history()
    
    def toggle_execution_mode(self) -> None:
        """実行モードを切り替え"""
        new_mode = self.agent_service.toggle_execution_mode()
        self.use_async = self.agent_service.use_async
        self.current_mode = new_mode
        self.update_status_bar()
        self.notify(f"実行モードを{new_mode}に切り替えました")
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """ベンチマークを実行"""
        return await self.agent_service.run_benchmark()
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """利用可能ツール一覧を取得"""
        return self.agent_service.get_available_tools()
    
    async def test_tools(self) -> Dict[str, Any]:
        """ツールテストを実行"""
        return await self.agent_service.test_tools()


async def launch_main_tui() -> None:
    """メインTUIアプリを起動"""
    app = MainTUIApp()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(launch_main_tui())