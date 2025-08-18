"""
ダッシュボードタブ - システム状態とクイックアクション
"""

from typing import TYPE_CHECKING, Dict, Any, List
import asyncio
from datetime import datetime

from textual.widgets import Static, Button, DataTable
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.timer import Timer

if TYPE_CHECKING:
    from .main_app import MainTUIApp


class DashboardTab(Container):
    """ダッシュボードタブコンポーネント"""
    
    CSS = """
    .dashboard-container {
        height: 1fr;
        layout: vertical;
        padding: 1;
        overflow: hidden;
    }
    
    .status-section {
        height: 6;
        border: solid $primary;
        margin-bottom: 1;
        padding: 1;
    }
    
    .quick-section {
        height: 8;
        border: solid $secondary;
        margin-bottom: 1;
        padding: 1;
    }
    
    .recent-section {
        height: 1fr;
        border: solid $accent;
        margin-bottom: 1;
        padding: 1;
    }
    
    .system-info-section {
        height: 6;
        border: solid $warning;
        padding: 1;
    }
    
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .status-item {
        margin: 0 1;
    }
    
    .metric-table {
        height: 1fr;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
        width: 8;
        height: 2;
        max-height: 2;
    }
    """
    
    # リアクティブ変数
    system_uptime: reactive[str] = reactive("00:00:00")
    memory_usage: reactive[str] = reactive("0MB")
    active_sessions: reactive[int] = reactive(0)
    
    def __init__(self, app: "MainTUIApp"):
        super().__init__(classes="dashboard-container")
        self._app = app
        self.start_time = datetime.now()
        self.update_timer: Timer = None
    
    def compose(self):
        """ダッシュボードレイアウトを構成"""
        # システム状態セクション
        with Container(classes="status-section"):
            yield Static("📊 システム状態", classes="section-title")
            with Horizontal():
                yield Static("🟢 稼働中", classes="status-item", id="system_status")
                yield Static("🔧 MCP: 未初期化", classes="status-item", id="mcp_status")
                yield Static("⚡ 非同期モード", classes="status-item", id="execution_mode")
                yield Static("📈 セッション数: 0", classes="status-item", id="session_count")
        
        # クイックアクションセクション
        with Container(classes="quick-section"):
            yield Static("⚡ クイックアクション", classes="section-title")
            with Horizontal():
                yield Button("S式生成", id="quick_generate", variant="primary")
                yield Button("履歴表示", id="quick_history", variant="default")
                yield Button("ツール一覧", id="quick_tools", variant="default")
                yield Button("設定", id="quick_settings", variant="default")
            with Horizontal():
                yield Button("トレース", id="quick_trace", variant="success")
                yield Button("ベンチマーク", id="quick_benchmark", variant="warning")
                yield Button("MCP状態", id="quick_mcp", variant="default")
                yield Button("ヘルプ", id="quick_help", variant="default")
        
        # 最近の実行結果セクション
        with Container(classes="recent-section"):
            yield Static("📋 最近の実行結果", classes="section-title")
            yield DataTable(id="recent_executions", classes="metric-table")
        
        # システム情報セクション
        with Container(classes="system-info-section"):
            yield Static("💻 システム情報", classes="section-title")
            with Horizontal():
                yield Static("稼働時間: 00:00:00", id="uptime_display")
                yield Static("メモリ: 0MB", id="memory_display")
                yield Static("LLM: gpt-oss-20b", id="llm_display")
                yield Static("API: 接続中", id="api_display")
    
    async def on_mount(self) -> None:
        """マウント時の初期化"""
        # データテーブルの設定
        table = self.query_one("#recent_executions", DataTable)
        table.add_columns("時刻", "操作", "結果", "実行時間", "状態")
        
        # サンプルデータを追加
        table.add_row("12:34:56", "search", "カレーレシピ...", "0.8s", "✅")
        table.add_row("12:35:12", "calc", "5", "0.1s", "✅")
        table.add_row("12:35:45", "par", "[結果1, 結果2]", "0.3s", "✅")
        
        # 定期更新タイマーを開始（1秒間隔）
        self.update_timer = self.set_interval(1.0, self.update_system_metrics)
        
        # 初期状態を更新
        await self.update_dashboard_status()
    
    def update_system_metrics(self) -> None:
        """システムメトリクスを更新"""
        # 稼働時間を計算
        uptime = datetime.now() - self.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        seconds = int(uptime.total_seconds() % 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # UIを更新
        self.query_one("#uptime_display", Static).update(f"稼働時間: {uptime_str}")
        
        # メモリ使用量（仮の実装）
        # TODO: 実際のメモリ使用量を取得
        import psutil
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.query_one("#memory_display", Static).update(f"メモリ: {memory_mb:.1f}MB")
        except:
            self.query_one("#memory_display", Static).update("メモリ: 不明")
    
    async def update_dashboard_status(self) -> None:
        """ダッシュボードの状態表示を更新"""
        # MCPステータス
        mcp_status = "🟢 正常" if self._app.mcp_initialized else "🔴 未初期化"
        self.query_one("#mcp_status", Static).update(f"🔧 MCP: {mcp_status}")
        
        # 実行モード
        mode = "⚡ 非同期モード" if self._app.use_async else "🐌 同期モード"
        self.query_one("#execution_mode", Static).update(mode)
        
        # セッション数
        session_count = len(self._app.session_history)
        self.query_one("#session_count", Static).update(f"📈 セッション数: {session_count}")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        button_id = event.button.id
        
        if button_id == "quick_generate":
            await self._app.action_quick_generate()
        elif button_id == "quick_history":
            await self._app.action_show_history()
        elif button_id == "quick_tools":
            await self.show_tools_info()
        elif button_id == "quick_benchmark":
            await self.run_quick_benchmark()
        elif button_id == "quick_mcp":
            await self.show_mcp_status()

    async def show_tools_info(self) -> None:
        """ツール情報を表示"""
        # TODO: ツール一覧表示を実装
        tools_info = """
利用可能ツール:
🔧 内蔵ツール:
  • calc (数式計算)
  • notify (通知)
  • math (記号数学)
  
🌐 MCPツール:
  • search (Brave検索)
  
📊 システムツール:
  • par (並列実行)
  • seq (順次実行)
        """
        self._app.notify(tools_info, title="利用可能ツール", timeout=8)
    
    async def run_quick_benchmark(self) -> None:
        """クイックベンチマークを実行"""
        self._app.notify("ベンチマーク実行中...", severity="information")
        
        # 簡単なベンチマークを実行
        try:
            start_time = asyncio.get_event_loop().time()
            
            # サンプル計算
            # 共通サービスのベンチマーク機能を使用
            benchmark_result = await self._app.run_benchmark()
            
            sync_duration = benchmark_result["sync_duration_ms"]
            async_duration = benchmark_result["async_duration_ms"]
            improvement = benchmark_result["improvement_percent"]
            
            end_time = asyncio.get_event_loop().time()
            duration = (end_time - start_time) * 1000
            
            result = f"ベンチマーク完了: 同期 {sync_duration:.1f}ms vs 非同期 {async_duration:.1f}ms (改善: {improvement:.1f}%)"
            self._app.notify(result, severity="success")
            
            # 最近の実行結果テーブルに追加
            table = self.query_one("#recent_executions", DataTable)
            now = datetime.now().strftime("%H:%M:%S")
            table.add_row(now, "benchmark", f"3回実行比較", f"{async_duration:.1f}ms", "✅")
            
        except Exception as e:
            self._app.notify(f"ベンチマークエラー: {e}", severity="error")
    
    async def show_mcp_status(self) -> None:
        """MCP状態を表示"""
        status = "正常" if self._app.mcp_initialized else "未初期化"
        mcp_info = f"""
MCP (Model Context Protocol) 状態:
状態: {status}
初期化済み: {"Yes" if self._app.mcp_initialized else "No"}
利用可能サーバー: {"1 (brave-search)" if self._app.mcp_initialized else "0"}

【利用可能コマンド】
/mcp status  - 詳細状態表示
/mcp tools   - ツール一覧
/mcp health  - ヘルスチェック
        """
        self._app.notify(mcp_info, title="MCP状態", timeout=10)
    
    def add_recent_execution(self, operation: str, result: str, duration_ms: float, success: bool = True) -> None:
        """最近の実行結果に項目を追加"""
        table = self.query_one("#recent_executions", DataTable)
        now = datetime.now().strftime("%H:%M:%S")
        status = "✅" if success else "❌"
        
        # 結果を50文字で切り詰め
        result_short = result[:47] + "..." if len(result) > 50 else result
        
        table.add_row(now, operation, result_short, f"{duration_ms:.1f}ms", status)
        
        # テーブルが大きくなりすぎないよう、古い行を削除
        if table.row_count > 10:
            table.remove_row(0)
    
    async def refresh_data(self) -> None:
        """データを手動で更新"""
        await self.update_dashboard_status()
        self._app.notify("ダッシュボードデータを更新しました", severity="information")