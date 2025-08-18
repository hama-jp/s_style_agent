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
    Input, Label, DataTable, Log, Tree
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
        layout: vertical;
        overflow: hidden;
    }
    
    TabbedContent {
        height: 1fr;
        width: 1fr;
        overflow: hidden;
    }
    
    .tab-content {
        height: 1fr;
        width: 1fr;
        overflow: hidden;
    }
    
    .status-bar {
        dock: bottom;
        height: 3;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    

    
    .system-info {
        text-align: center;
        text-style: italic;
        color: $text-muted;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+w", "focus_workspace", "ワークスペース"),
        Binding("f2", "quick_generate", "S式生成"),
        Binding("f3", "focus_execution", "実行"),
        Binding("ctrl+l", "clear_all", "クリア"),
        Binding("ctrl+g", "focus_generation", "生成モード"),
        Binding("ctrl+e", "focus_execution", "実行モード"),
        Binding("ctrl+h", "focus_history", "履歴表示"),
        Binding("ctrl+q", "quit", "終了", priority=True),
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
            with TabbedContent(initial="workspace"):
                with TabPane("ワークスペース", id="workspace"):
                    yield WorkspaceTab(app=self)
                    
                with TabPane("ダッシュボード", id="dashboard"):
                    yield DashboardTab(app=self)
                    
                with TabPane("履歴管理", id="history"):
                    yield HistoryTab(app=self)
                    
                with TabPane("システム設定", id="settings"):
                    yield SettingsTab(app=self)
            
            # クイックアクションバー

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

    
    def on_tabbed_content_tab_activated(self, event) -> None:
        """タブが切り替えられた時の処理"""
        # レイアウトの強制再描画
        self.refresh(layout=True)
        
        # 子ウィジェットも再描画
        self.call_after_refresh(self._refresh_active_tab)

    def _refresh_active_tab(self) -> None:
        """アクティブなタブの再描画"""
        try:
            # TabbedContentウィジェットを探してアクティブタブを再描画
            tabbed_content = self.query_one("TabbedContent")
            if hasattr(tabbed_content, 'active_pane') and tabbed_content.active_pane:
                tabbed_content.active_pane.refresh(layout=True)
        except Exception:
            # エラーが発生しても処理を継続
            pass
    
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
    

    # アクション実装
    async def action_quick_generate(self) -> None:
        """クイックS式生成"""
        # ワークスペースタブに切り替えて生成モードに
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "workspace"
        
        # ワークスペースの生成機能を呼び出し
        workspace = self.query_one(WorkspaceTab)
        await workspace.focus_generation_input()
    
    async def action_clear_all(self) -> None:
        """全入力をクリア"""
        # ワークスペースの入力フィールドをクリア
        workspace = self.query_one(WorkspaceTab)
        await workspace.clear_all_inputs()
    
    async def action_show_history(self) -> None:
        """履歴表示"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "history"
    

    
    async def action_focus_execution(self) -> None:
        """実行モードにフォーカス"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "workspace"
        workspace = self.query_one(WorkspaceTab)
        await workspace.focus_execution_area()
    
    async def action_focus_history(self) -> None:
        """履歴表示にフォーカス"""
        await self.action_show_history()
    
    async def action_focus_workspace(self) -> None:
        """ワークスペースにフォーカス"""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "workspace"
        self.notify("ワークスペースに切り替えました")
    

    
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