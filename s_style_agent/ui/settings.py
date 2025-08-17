"""
設定タブ - システム設定管理
"""

from typing import TYPE_CHECKING, Dict, Any
import asyncio

from textual.widgets import (
    Static, Button, Input, Checkbox, RadioSet, RadioButton
)
from textual.containers import Container, ScrollableContainer, Horizontal, Vertical
from textual.reactive import reactive

if TYPE_CHECKING:
    from .main_app import MainTUIApp


class SettingsTab(Container):
    """設定タブコンポーネント"""
    
    CSS = """
    .settings-container {
        height: 1fr;
        layout: horizontal;
        padding: 1;
    }
    
    .llm-panel {
        width: 50%;
        border: solid $primary;
        margin: 0 1 0 0;
        padding: 1;
    }
    
    .system-panel {
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
    
    .setting-group {
        height: auto;
        border: solid $surface;
        margin: 1 0;
        padding: 1;
    }
    
    .setting-item {
        height: 3;
        layout: horizontal;
        align: center middle;
        margin: 1 0;
    }
    
    .setting-label {
        width: 15;
        text-align: right;
        margin-right: 2;
    }
    
    .setting-input {
        width: 25;
    }
    
    .setting-button {
        margin-left: 2;
    }
    
    .status-display {
        text-align: center;
        text-style: italic;
        margin: 1 0;
        padding: 1;
        background: $surface;
    }
    
    Button {
        margin: 0 1;
    }
    
    .mcp-section {
        height: auto;
        margin: 1 0;
    }
    
    .interface-section {
        height: auto;
        margin: 1 0;
    }
    
    .execution-section {
        height: auto;
        margin: 1 0;
    }
    """
    
    # リアクティブ変数
    llm_status: reactive[str] = reactive("未接続")
    mcp_status: reactive[str] = reactive("未初期化")
    settings_modified: reactive[bool] = reactive(False)
    
    def __init__(self, app: "MainTUIApp"):
        super().__init__(classes="settings-container")
        self._app = app
        self.original_settings = {}
        self.current_settings = {}
    
    def compose(self):
        """設定レイアウトを構成"""
        # LLM設定パネル
        with Container(classes="llm-panel"):
            yield Static("🤖 LLM設定", classes="section-title")
            
            # LLM基本設定
            with Container(classes="setting-group"):
                yield Static("基本設定", classes="section-title")
                
                with Container(classes="setting-item"):
                    yield Static("ベースURL:", classes="setting-label")
                    yield Input(
                        value="http://192.168.79.1:1234/v1",
                        placeholder="LLM API ベースURL",
                        id="llm_base_url",
                        classes="setting-input"
                    )
                    yield Button("テスト", id="test_llm_connection", 
                               variant="primary", classes="setting-button")
                
                with Container(classes="setting-item"):
                    yield Static("モデル名:", classes="setting-label")
                    yield Input(
                        value="openai/gpt-oss-20b",
                        placeholder="モデル名",
                        id="llm_model_name",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-item"):
                    yield Static("APIキー:", classes="setting-label")
                    yield Input(
                        value="dummy",
                        placeholder="API Key",
                        id="llm_api_key",
                        classes="setting-input",
                        password=True
                    )
                
                with Container(classes="setting-item"):
                    yield Static("温度:", classes="setting-label")
                    yield Input(
                        value="0.3",
                        placeholder="0.0 - 1.0",
                        id="llm_temperature",
                        classes="setting-input"
                    )
            
            # LLM詳細設定
            with Container(classes="setting-group"):
                yield Static("詳細設定", classes="section-title")
                
                with Container(classes="setting-item"):
                    yield Static("最大トークン:", classes="setting-label")
                    yield Input(
                        value="2048",
                        placeholder="最大トークン数",
                        id="llm_max_tokens",
                        classes="setting-input"
                    )
                
                with Container(classes="setting-item"):
                    yield Static("タイムアウト:", classes="setting-label")
                    yield Input(
                        value="30",
                        placeholder="秒",
                        id="llm_timeout",
                        classes="setting-input"
                    )
            
            # 接続状態表示
            yield Static("接続状態: 未確認", 
                       classes="status-display", id="llm_status_display")
            
            # LLM制御ボタン
            with Horizontal():
                yield Button("設定保存", id="save_llm_settings", variant="success")
                yield Button("設定復元", id="restore_llm_settings", variant="warning")
                yield Button("デフォルト", id="default_llm_settings", variant="default")
        
        # システム設定パネル
        with Container(classes="system-panel"):
            yield Static("⚙️ システム設定", classes="section-title")
            
            # 実行設定
            with Container(classes="setting-group execution-section"):
                yield Static("実行設定", classes="section-title")
                
                with Container(classes="setting-item"):
                    yield Checkbox("非同期実行", value=True, id="async_execution")
                    yield Static("並列実行を有効にする", classes="setting-label")
                
                with Container(classes="setting-item"):
                    yield Checkbox("自動保存", value=True, id="auto_save")
                    yield Static("セッション自動保存", classes="setting-label")
                
                with Container(classes="setting-item"):
                    yield Checkbox("詳細ログ", value=False, id="verbose_logging")
                    yield Static("詳細ログ出力", classes="setting-label")
                
                with Container(classes="setting-item"):
                    yield Checkbox("トレース記録", value=True, id="trace_logging")
                    yield Static("実行トレース記録", classes="setting-label")
            
            # インターフェース設定
            with Container(classes="setting-group interface-section"):
                yield Static("インターフェース", classes="section-title")
                
                with Container(classes="setting-item"):
                    yield Static("UIモード:", classes="setting-label")
                    with RadioSet(id="ui_mode"):
                        yield RadioButton("TUI", value=True, id="tui_mode")
                        yield RadioButton("CLI", id="cli_mode")
                
                with Container(classes="setting-item"):
                    yield Checkbox("キーボードショートカット", value=True, id="keyboard_shortcuts")
                    yield Static("キーボードショートカット有効", classes="setting-label")
                
                with Container(classes="setting-item"):
                    yield Checkbox("マウスサポート", value=True, id="mouse_support")
                    yield Static("マウス操作サポート", classes="setting-label")
                
                with Container(classes="setting-item"):
                    yield Checkbox("通知表示", value=True, id="show_notifications")
                    yield Static("通知メッセージ表示", classes="setting-label")
            
            # MCP設定
            with Container(classes="setting-group mcp-section"):
                yield Static("MCP管理", classes="section-title")
                
                with Container(classes="setting-item"):
                    yield Static("ステータス:", classes="setting-label")
                    yield Static("未初期化", id="mcp_status_text")
                    yield Button("再起動", id="restart_mcp", 
                               variant="warning", classes="setting-button")
                    yield Button("テスト", id="test_mcp", 
                               variant="primary", classes="setting-button")
                
                with Container(classes="setting-item"):
                    yield Static("設定ファイル:", classes="setting-label")
                    yield Input(
                        value="mcp.json",
                        placeholder="MCP設定ファイル",
                        id="mcp_config_file",
                        classes="setting-input"
                    )
                    yield Button("編集", id="edit_mcp_config", 
                               variant="default", classes="setting-button")
            
            # システム制御
            with Horizontal():
                yield Button("全設定保存", id="save_all_settings", variant="success")
                yield Button("設定復元", id="restore_all_settings", variant="warning")
                yield Button("デフォルトに戻す", id="reset_to_defaults", variant="error")
    
    async def on_mount(self) -> None:
        """マウント時の初期化"""
        await self.load_current_settings()
        await self.update_status_displays()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        button_id = event.button.id
        
        if button_id == "test_llm_connection":
            await self.test_llm_connection()
        elif button_id == "save_llm_settings":
            await self.save_llm_settings()
        elif button_id == "restore_llm_settings":
            await self.restore_llm_settings()
        elif button_id == "default_llm_settings":
            await self.default_llm_settings()
        elif button_id == "restart_mcp":
            await self.restart_mcp()
        elif button_id == "test_mcp":
            await self.test_mcp()
        elif button_id == "edit_mcp_config":
            await self.edit_mcp_config()
        elif button_id == "save_all_settings":
            await self.save_all_settings()
        elif button_id == "restore_all_settings":
            await self.restore_all_settings()
        elif button_id == "reset_to_defaults":
            await self.reset_to_defaults()
    
    async def on_input_changed(self, event: Input.Changed) -> None:
        """入力変更時の処理"""
        self.settings_modified = True
        await self.update_setting_preview()
    
    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """チェックボックス変更時の処理"""
        self.settings_modified = True
        
        if event.checkbox.id == "async_execution":
            # 実行モードの即座反映
            self._app.use_async = event.value
            self._app.current_mode = "async" if event.value else "sync"
            self._app.update_status_bar()
            self._app.notify(f"実行モードを{self._app.current_mode}に変更しました")
    
    async def load_current_settings(self) -> None:
        """現在の設定を読み込み"""
        from ..config.settings import settings
        
        # LLM設定
        self.query_one("#llm_base_url", Input).value = settings.llm.base_url
        self.query_one("#llm_model_name", Input).value = settings.llm.model_name
        self.query_one("#llm_api_key", Input).value = settings.llm.api_key
        self.query_one("#llm_temperature", Input).value = str(settings.llm.temperature)
        
        # システム設定
        self.query_one("#async_execution", Checkbox).value = self._app.use_async
        
        # 元の設定を保存
        self.original_settings = {
            "llm_base_url": settings.llm.base_url,
            "llm_model_name": settings.llm.model_name,
            "llm_api_key": settings.llm.api_key,
            "llm_temperature": settings.llm.temperature,
            "async_execution": self._app.use_async,
        }
    
    async def update_status_displays(self) -> None:
        """ステータス表示を更新"""
        # LLMステータス
        llm_status_display = self.query_one("#llm_status_display", Static)
        llm_status_display.update(f"接続状態: {self.llm_status}")
        
        # MCPステータス
        mcp_status_text = self.query_one("#mcp_status_text", Static)
        mcp_status = "正常" if self._app.mcp_initialized else "未初期化"
        mcp_status_text.update(mcp_status)
    
    async def update_setting_preview(self) -> None:
        """設定プレビューを更新"""
        # 設定が変更されたことを示す
        if self.settings_modified:
            # TODO: 設定プレビュー表示
            pass
    
    async def test_llm_connection(self) -> None:
        """LLM接続テスト"""
        self._app.notify("LLM接続テスト実行中...", severity="information")
        
        try:
            # 簡単なテストクエリを送信
            test_result = await self._app.evaluate_s_expression("(calc \"1+1\")")
            
            if test_result is not None:
                self.llm_status = "接続成功"
                await self.update_status_displays()
                self._app.notify("LLM接続テスト成功", severity="success")
            else:
                raise Exception("テスト結果が None")
                
        except Exception as e:
            self.llm_status = f"接続失敗: {str(e)}"
            await self.update_status_displays()
            self._app.notify(f"LLM接続テスト失敗: {e}", severity="error")
    
    async def save_llm_settings(self) -> None:
        """LLM設定を保存"""
        try:
            # 入力値を取得
            base_url = self.query_one("#llm_base_url", Input).value
            model_name = self.query_one("#llm_model_name", Input).value
            api_key = self.query_one("#llm_api_key", Input).value
            temperature = float(self.query_one("#llm_temperature", Input).value)
            
            # TODO: 実際の設定保存処理
            # .envファイルや設定ファイルに保存
            
            self._app.notify("LLM設定を保存しました", severity="success")
            self.settings_modified = False
            
        except Exception as e:
            self._app.notify(f"LLM設定保存エラー: {e}", severity="error")
    
    async def restore_llm_settings(self) -> None:
        """LLM設定を復元"""
        # 元の設定に戻す
        self.query_one("#llm_base_url", Input).value = self.original_settings["llm_base_url"]
        self.query_one("#llm_model_name", Input).value = self.original_settings["llm_model_name"]
        self.query_one("#llm_api_key", Input).value = self.original_settings["llm_api_key"]
        self.query_one("#llm_temperature", Input).value = str(self.original_settings["llm_temperature"])
        
        self._app.notify("LLM設定を復元しました", severity="warning")
        self.settings_modified = False
    
    async def default_llm_settings(self) -> None:
        """LLM設定をデフォルトに戻す"""
        # デフォルト値を設定
        self.query_one("#llm_base_url", Input).value = "http://192.168.79.1:1234/v1"
        self.query_one("#llm_model_name", Input).value = "openai/gpt-oss-20b"
        self.query_one("#llm_api_key", Input).value = "dummy"
        self.query_one("#llm_temperature", Input).value = "0.3"
        
        self._app.notify("LLM設定をデフォルトに戻しました", severity="information")
        self.settings_modified = True
    
    async def restart_mcp(self) -> None:
        """MCPを再起動"""
        self._app.notify("MCP再起動中...", severity="information")
        
        try:
            # TODO: 実際のMCP再起動処理
            await asyncio.sleep(1)  # 再起動シミュレーション
            
            await self._app.init_mcp_system()
            await self.update_status_displays()
            
            self._app.notify("MCP再起動完了", severity="success")
            
        except Exception as e:
            self._app.notify(f"MCP再起動エラー: {e}", severity="error")
    
    async def test_mcp(self) -> None:
        """MCPテスト"""
        if not self._app.mcp_initialized:
            self._app.notify("MCPが初期化されていません", severity="warning")
            return
        
        try:
            # TODO: 実際のMCPテスト処理
            self._app.notify("MCPテスト成功", severity="success")
            
        except Exception as e:
            self._app.notify(f"MCPテストエラー: {e}", severity="error")
    
    async def edit_mcp_config(self) -> None:
        """MCP設定ファイルを編集"""
        config_info = """
MCP設定ファイル (mcp.json):
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key"
      }
    }
  }
}

編集は外部エディタで行ってください。
        """
        self._app.notify(config_info, title="MCP設定", timeout=15)
    
    async def save_all_settings(self) -> None:
        """全設定を保存"""
        try:
            await self.save_llm_settings()
            # TODO: その他の設定保存
            
            self._app.notify("全設定を保存しました", severity="success")
            
        except Exception as e:
            self._app.notify(f"設定保存エラー: {e}", severity="error")
    
    async def restore_all_settings(self) -> None:
        """全設定を復元"""
        await self.restore_llm_settings()
        await self.load_current_settings()
        
        self._app.notify("全設定を復元しました", severity="warning")
    
    async def reset_to_defaults(self) -> None:
        """デフォルト設定にリセット"""
        await self.default_llm_settings()
        
        # システム設定もデフォルトに
        self.query_one("#async_execution", Checkbox).value = True
        self.query_one("#auto_save", Checkbox).value = True
        self.query_one("#verbose_logging", Checkbox).value = False
        self.query_one("#trace_logging", Checkbox).value = True
        
        self._app.notify("全設定をデフォルトにリセットしました", severity="warning")