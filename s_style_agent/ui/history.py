"""
履歴管理タブ - セッション履歴とツール管理
"""

from typing import TYPE_CHECKING, List, Dict, Any, Optional
from datetime import datetime, timedelta

from textual.widgets import (
    Static, Button, DataTable, Tree, Input, Label
)
from textual.containers import Container, ScrollableContainer, Horizontal, Vertical
from textual.reactive import reactive

if TYPE_CHECKING:
    from .main_app import MainTUIApp


class HistoryTab(Container):
    """履歴管理タブコンポーネント"""
    
    CSS = """
    .history-container {
        height: 1fr;
        layout: horizontal;
        padding: 1;
    }
    
    .history-panel {
        width: 50%;
        border: solid $primary;
        margin: 0 1 0 0;
        padding: 1;
    }
    
    .tools-panel {
        width: 50%;
        border: solid $secondary;
        margin: 0 0 0 1;
        padding: 1;
    }
    
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .history-controls {
        height: 4;
        layout: horizontal;
        align: center middle;
        margin-bottom: 1;
    }
    
    .tools-controls {
        height: 4;
        layout: horizontal;
        align: center middle;
        margin-bottom: 1;
    }
    
    .history-table {
        height: 1fr;
        margin-top: 1;
    }
    
    .tools-list {
        height: 1fr;
        margin-top: 1;
    }
    
    .benchmark-section {
        height: 8;
        border: solid $warning;
        margin-top: 1;
        padding: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    .filter-input {
        width: 20;
        margin: 0 1;
    }
    
    .benchmark-display {
        text-align: center;
        margin: 1 0;
    }
    
    .tool-item {
        margin: 1 0;
        padding: 1;
        border: solid $surface;
    }
    
    .tool-status {
        text-align: right;
    }
    """
    
    # リアクティブ変数
    total_sessions: reactive[int] = reactive(0)
    successful_sessions: reactive[int] = reactive(0)
    filter_text: reactive[str] = reactive("")
    
    def __init__(self, app: "MainTUIApp"):
        super().__init__(classes="history-container")
        self._app = app
        self.displayed_history: List[Dict[str, Any]] = []
    
    def compose(self):
        """履歴管理レイアウトを構成"""
        # 履歴パネル
        with Container(classes="history-panel"):
            yield Static("📅 セッション履歴", classes="section-title")
            
            # 履歴制御
            with Container(classes="history-controls"):
                yield Button("更新", id="refresh_history", variant="primary")
                yield Button("クリア", id="clear_history", variant="error")
                yield Button("エクスポート", id="export_history", variant="default")
                yield Input(
                    placeholder="フィルター...",
                    id="history_filter",
                    classes="filter-input"
                )
            
            # 履歴テーブル
            yield DataTable(id="history_table", classes="history-table")
            
            # ベンチマークセクション
            with Container(classes="benchmark-section"):
                yield Static("📊 実行ベンチマーク", classes="section-title")
                with Horizontal():
                    yield Button("同期実行", id="sync_benchmark", variant="warning")
                    yield Button("非同期実行", id="async_benchmark", variant="success")
                    yield Button("比較実行", id="compare_benchmark", variant="default")
                
                yield Static("並列実行比較結果が表示されます", 
                           classes="benchmark-display", id="benchmark_result")
        
        # ツールパネル
        with Container(classes="tools-panel"):
            yield Static("🔧 利用可能ツール", classes="section-title")
            
            # ツール制御
            with Container(classes="tools-controls"):
                yield Button("更新", id="refresh_tools", variant="primary")
                yield Button("テスト", id="test_tools", variant="success")
                yield Button("追加", id="add_tool", variant="default")
                yield Button("設定", id="tool_settings", variant="default")
            
            # 内蔵ツールセクション
            yield Static("🔧 内蔵ツール", classes="section-title")
            yield ScrollableContainer(id="builtin_tools", classes="tools-list")
            
            # MCPツールセクション
            yield Static("🌐 MCPツール", classes="section-title")
            yield ScrollableContainer(id="mcp_tools", classes="tools-list")
            
            # カスタムツールセクション
            yield Static("⚙️ カスタムツール", classes="section-title")
            yield ScrollableContainer(id="custom_tools", classes="tools-list")
    
    async def on_mount(self) -> None:
        """マウント時の初期化"""
        # 履歴テーブルの設定
        table = self.query_one("#history_table", DataTable)
        table.add_columns("時刻", "操作", "入力", "出力", "実行時間", "状態")
        
        # 初期データをロード
        await self.refresh_history()
        await self.refresh_tools()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        button_id = event.button.id
        
        if button_id == "refresh_history":
            await self.refresh_history()
        elif button_id == "clear_history":
            await self.clear_history()
        elif button_id == "export_history":
            await self.export_history()
        elif button_id == "refresh_tools":
            await self.refresh_tools()
        elif button_id == "test_tools":
            await self.test_tools()
        elif button_id == "add_tool":
            await self.add_custom_tool()
        elif button_id == "tool_settings":
            await self.show_tool_settings()
        elif button_id == "sync_benchmark":
            await self.run_sync_benchmark()
        elif button_id == "async_benchmark":
            await self.run_async_benchmark()
        elif button_id == "compare_benchmark":
            await self.run_compare_benchmark()
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """入力変更時の処理"""
        if event.input.id == "history_filter":
            self.filter_text = event.value
            await self.apply_history_filter()
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """テーブル行選択時の処理"""
        if event.data_table.id == "history_table":
            await self.load_history_item(event.row_index)
    
    async def refresh_history(self) -> None:
        """履歴を更新"""
        table = self.query_one("#history_table", DataTable)
        table.clear()
        
        history = self._app.get_session_history()
        self.displayed_history = history.copy()
        
        for item in history:
            timestamp = item.get("timestamp", 0)
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            
            operation = item.get("operation", "unknown")
            input_str = str(item.get("input", ""))[:30] + "..." if len(str(item.get("input", ""))) > 30 else str(item.get("input", ""))
            
            if "error" in item:
                output_str = f"Error: {item['error']}"[:30] + "..."
                status = "❌"
                duration = "-"
            else:
                output_str = str(item.get("output", ""))[:30] + "..." if len(str(item.get("output", ""))) > 30 else str(item.get("output", ""))
                status = "✅" if item.get("success", True) else "❌"
                duration = f"{item.get('duration_ms', 0):.1f}ms" if "duration_ms" in item else "-"
            
            table.add_row(time_str, operation, input_str, output_str, duration, status)
        
        # 統計更新
        self.total_sessions = len(history)
        self.successful_sessions = sum(1 for item in history if item.get("success", True))
        
        self._app.notify(f"履歴を更新しました ({len(history)}件)", severity="information")
    
    async def apply_history_filter(self) -> None:
        """履歴フィルターを適用"""
        if not self.filter_text:
            await self.refresh_history()
            return
        
        table = self.query_one("#history_table", DataTable)
        table.clear()
        
        history = self._app.get_session_history()
        filtered_history = []
        
        for item in history:
            # フィルターテキストが操作、入力、出力のいずれかに含まれているかチェック
            operation = str(item.get("operation", "")).lower()
            input_text = str(item.get("input", "")).lower()
            output_text = str(item.get("output", "")).lower()
            filter_lower = self.filter_text.lower()
            
            if (filter_lower in operation or 
                filter_lower in input_text or 
                filter_lower in output_text):
                filtered_history.append(item)
        
        self.displayed_history = filtered_history
        
        for item in filtered_history:
            timestamp = item.get("timestamp", 0)
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%H:%M:%S")
            
            operation = item.get("operation", "unknown")
            input_str = str(item.get("input", ""))[:30] + "..." if len(str(item.get("input", ""))) > 30 else str(item.get("input", ""))
            
            if "error" in item:
                output_str = f"Error: {item['error']}"[:30] + "..."
                status = "❌"
                duration = "-"
            else:
                output_str = str(item.get("output", ""))[:30] + "..." if len(str(item.get("output", ""))) > 30 else str(item.get("output", ""))
                status = "✅" if item.get("success", True) else "❌"
                duration = f"{item.get('duration_ms', 0):.1f}ms" if "duration_ms" in item else "-"
            
            table.add_row(time_str, operation, input_str, output_str, duration, status)
    
    async def clear_history(self) -> None:
        """履歴をクリア"""
        self._app.session_history.clear()
        await self.refresh_history()
        self._app.notify("履歴をクリアしました", severity="warning")
    
    async def export_history(self) -> None:
        """履歴をエクスポート"""
        # TODO: 実際のエクスポート機能を実装
        history = self._app.get_session_history()
        
        export_info = f"""
履歴エクスポート情報:
総セッション数: {len(history)}
成功: {sum(1 for item in history if item.get('success', True))}
失敗: {sum(1 for item in history if not item.get('success', True))}

エクスポート先: session_history.json (予定)
        """
        self._app.notify(export_info, title="履歴エクスポート", timeout=8)
    
    async def load_history_item(self, row_index: int) -> None:
        """履歴項目をワークスペースに読み込み"""
        if 0 <= row_index < len(self.displayed_history):
            item = self.displayed_history[row_index]
            
            # ワークスペースタブに切り替えて項目を読み込み
            try:
                tabbed_content = self._app.query_one("TabbedContent")
                tabbed_content.active = "workspace"
                
                workspace = self._app.query_one("WorkspaceTab")
                workspace.load_from_history(item)
                
                self._app.notify("履歴項目をワークスペースに読み込みました", severity="success")
            except Exception as e:
                self._app.notify(f"読み込みエラー: {e}", severity="error")
    
    async def refresh_tools(self) -> None:
        """ツール一覧を更新"""
        # 内蔵ツール
        builtin_container = self.query_one("#builtin_tools", ScrollableContainer)
        builtin_container.remove_children()
        
        builtin_tools = [
            {"name": "calc", "description": "数式計算", "status": "✅"},
            {"name": "notify", "description": "通知表示", "status": "✅"},
            {"name": "math", "description": "記号数学計算", "status": "✅"},
            {"name": "par", "description": "並列実行", "status": "✅"},
            {"name": "seq", "description": "順次実行", "status": "✅"},
        ]
        
        for tool in builtin_tools:
            tool_widget = Container(classes="tool-item")
            tool_widget.compose_add_child(
                Horizontal(
                    Static(f"🔧 {tool['name']}", classes="tool-name"),
                    Static(tool["description"], classes="tool-description"),
                    Static(tool["status"], classes="tool-status")
                )
            )
            builtin_container.mount(tool_widget)
        
        # MCPツール
        mcp_container = self.query_one("#mcp_tools", ScrollableContainer)
        mcp_container.remove_children()
        
        mcp_tools = []
        if self._app.mcp_initialized:
            mcp_tools = [
                {"name": "search", "description": "Brave検索", "status": "✅"},
            ]
        
        if not mcp_tools:
            mcp_container.mount(Static("MCPツールは利用できません"))
        else:
            for tool in mcp_tools:
                tool_widget = Container(classes="tool-item")
                tool_widget.compose_add_child(
                    Horizontal(
                        Static(f"🌐 {tool['name']}", classes="tool-name"),
                        Static(tool["description"], classes="tool-description"),
                        Static(tool["status"], classes="tool-status")
                    )
                )
                mcp_container.mount(tool_widget)
        
        # カスタムツール
        custom_container = self.query_one("#custom_tools", ScrollableContainer)
        custom_container.remove_children()
        custom_container.mount(Static("カスタムツールはありません"))
        
        self._app.notify("ツール一覧を更新しました", severity="information")
    
    async def test_tools(self) -> None:
        """ツールテストを実行"""
        # 共通サービスのツールテスト機能を使用
        try:
            test_results_dict = await self._app.test_tools()
            
            # 結果を整形
            test_results = []
            for tool_name, result in test_results_dict.items():
                if result["status"] == "success":
                    test_results.append(f"{tool_name}: ✅")
                elif result["status"] == "failed":
                    test_results.append(f"{tool_name}: ❌ (期待値と異なる)")
                else:  # error
                    test_results.append(f"{tool_name}: ❌ (エラー: {result['error']})")
            
            # テスト結果を表示
            result_text = "ツールテスト結果:\n" + "\n".join(test_results)
            self._app.notify(result_text, title="ツールテスト", timeout=10)
            
        except Exception as e:
            self._app.notify(f"ツールテストエラー: {e}", severity="error")

    
    async def add_custom_tool(self) -> None:
        """カスタムツールを追加"""
        self._app.notify("カスタムツール追加機能は実装中です", severity="information")
    
    async def show_tool_settings(self) -> None:
        """ツール設定を表示"""
        settings_info = """
ツール設定:
内蔵ツール: 常時利用可能
MCPツール: mcp.json で設定
カスタムツール: 未実装

設定ファイル: .env, mcp.json
        """
        self._app.notify(settings_info, title="ツール設定", timeout=8)
    
    async def run_sync_benchmark(self) -> None:
        """同期実行ベンチマーク"""
        if self._app.use_async:
            self._app.toggle_execution_mode()  # 同期モードに切り替え
        
        start_time = datetime.now()
        
        try:
            await self._app.evaluate_s_expression("(calc \"10*10\")")
            await self._app.evaluate_s_expression("(calc \"20+20\")")
            await self._app.evaluate_s_expression("(calc \"30-10\")")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds() * 1000
            
            result_display = self.query_one("#benchmark_result", Static)
            result_display.update(f"同期実行: {duration:.1f}ms (3回実行)")
            
            self._app.notify(f"同期ベンチマーク完了: {duration:.1f}ms", severity="success")
            
        except Exception as e:
            self._app.notify(f"同期ベンチマークエラー: {e}", severity="error")
    
    async def run_async_benchmark(self) -> None:
        """非同期実行ベンチマーク"""
        if not self._app.use_async:
            self._app.toggle_execution_mode()  # 非同期モードに切り替え
        
        start_time = datetime.now()
        
        try:
            # 並列実行
            import asyncio
            tasks = [
                self._app.evaluate_s_expression("(calc \"10*10\")"),
                self._app.evaluate_s_expression("(calc \"20+20\")"),
                self._app.evaluate_s_expression("(calc \"30-10\")")
            ]
            await asyncio.gather(*tasks)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds() * 1000
            
            result_display = self.query_one("#benchmark_result", Static)
            result_display.update(f"非同期実行: {duration:.1f}ms (3回並列)")
            
            self._app.notify(f"非同期ベンチマーク完了: {duration:.1f}ms", severity="success")
            
        except Exception as e:
            self._app.notify(f"非同期ベンチマークエラー: {e}", severity="error")
    
    async def run_compare_benchmark(self) -> None:
        """比較ベンチマーク"""
        self._app.notify("比較ベンチマーク実行中...", severity="information")
        
        # 同期実行
        original_mode = self._app.use_async
        self._app.use_async = False
        
        start_sync = datetime.now()
        try:
            await self._app.evaluate_s_expression("(calc \"100*100\")")
            await self._app.evaluate_s_expression("(calc \"200+200\")")
            await self._app.evaluate_s_expression("(calc \"300-100\")")
        except Exception:
            pass
        end_sync = datetime.now()
        sync_duration = (end_sync - start_sync).total_seconds() * 1000
        
        # 非同期実行
        self._app.use_async = True
        
        start_async = datetime.now()
        try:
            import asyncio
            tasks = [
                self._app.evaluate_s_expression("(calc \"100*100\")"),
                self._app.evaluate_s_expression("(calc \"200+200\")"),
                self._app.evaluate_s_expression("(calc \"300-100\")")
            ]
            await asyncio.gather(*tasks)
        except Exception:
            pass
        end_async = datetime.now()
        async_duration = (end_async - start_async).total_seconds() * 1000
        
        # 元のモードに戻す
        self._app.use_async = original_mode
        
        # 結果表示
        improvement = ((sync_duration - async_duration) / sync_duration * 100) if sync_duration > 0 else 0
        
        result_display = self.query_one("#benchmark_result", Static)
        result_display.update(
            f"比較結果: 同期 {sync_duration:.1f}ms vs 非同期 {async_duration:.1f}ms "
            f"(改善: {improvement:.1f}%)"
        )
        
        self._app.notify(f"比較ベンチマーク完了", severity="success")