"""
ワークスペースタブ - S式生成・実行・トレース
"""

from typing import TYPE_CHECKING, Optional, Dict, Any
import asyncio
from datetime import datetime

from textual.widgets import (
    Static, Button, Input, TextArea, DataTable, Tree,
    RadioSet, RadioButton, Checkbox
)
from textual.containers import Container, ScrollableContainer, Horizontal, Vertical
from textual.reactive import reactive

if TYPE_CHECKING:
    from .main_app import MainTUIApp


class WorkspaceTab(Container):
    """ワークスペースタブコンポーネント"""
    
    CSS = """
    .workspace-container {
        height: 1fr;
        layout: vertical;
        padding: 1;
    }
    
    .input-section {
        min-height: 16;
        height: auto;
        border: solid $primary;
        margin-bottom: 1;
        padding: 1;
        display: block;
    }
    
    .execution-section {
        height: 1fr;
        layout: horizontal;
    }
    
    .trace-panel {
        width: 50%;
        border: solid $secondary;
        margin: 0 1 1 0;
        padding: 1;
    }
    
    .results-panel {
        width: 50%;
        border: solid $accent;
        margin: 0 0 1 1;
        padding: 1;
    }
    
    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .input-area {
        height: 4;
        margin: 1 0;
    }
    
    .input-controls {
        height: 6;
        layout: horizontal;
        align: center middle;
        margin: 1 0;
    }
    
    .execution-controls {
        height: 4;
        layout: horizontal;
        align: center middle;
        margin-bottom: 1;
    }
    
    .trace-tree {
        height: 1fr;
        margin-top: 1;
    }
    
    .results-display {
        height: 1fr;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
        min-width: 8;
        height: 3;
    }
    
    .status-display {
        text-align: center;
        text-style: italic;
        margin: 1 0;
    }
    
    .mode-selection {
        margin: 0 1;
    }
    
    .button-controls {
        height: 4;
        layout: horizontal;
        align: center middle;
        margin: 1 0;
    }
    """
    
    # リアクティブ変数
    current_expression: reactive[str] = reactive("")
    execution_status: reactive[str] = reactive("待機中")
    last_result: reactive[str] = reactive("")
    
    def __init__(self, app: "MainTUIApp"):
        super().__init__(classes="workspace-container")
        self._app = app
        self.is_executing = False
    
    def compose(self):
        """ワークスペースレイアウトを構成"""
        # 入力セクション
        with Container(classes="input-section"):
            yield Static("📝 S式入力・生成", classes="section-title")
            
            # 入力モード選択
            with Horizontal(classes="input-controls"):
                yield Static("入力モード:", classes="mode-selection")
                with RadioSet(id="input_mode"):
                    yield RadioButton("自然言語", value=True, id="natural_mode")
                    yield RadioButton("直接S式", id="direct_mode")
                    yield RadioButton("履歴選択", id="history_mode")
            
            # ボタン行を別のコンテナに分離
            with Horizontal(classes="button-controls"):
                yield Button("🎯 生成", id="generate_btn", variant="primary")
                yield Button("🗑️ クリア", id="clear_btn", variant="default")
            
            # 入力エリア
            yield Static("自然言語で指示を入力してください（例: カレーの作り方を教えて）", id="input_instruction")
            yield TextArea(
                text="",
                id="input_area",
                classes="input-area"
            )
            
            # 生成されたS式表示
            yield Static("生成されたS式:", classes="section-title")
            yield TextArea(
                text="(ここに生成されたS式が表示されます)",
                id="generated_expr",
                classes="input-area"
            )
        
        # 実行セクション
        with Container(classes="execution-section"):
            # トレースパネル
            with Container(classes="trace-panel"):
                yield Static("🔍 実行トレース", classes="section-title")
                
                # 実行制御
                with Container(classes="execution-controls"):
                    yield Button("実行", id="execute_btn", variant="success")
                    yield Button("ステップ", id="step_btn", variant="warning")
                    yield Button("停止", id="stop_btn", variant="error")
                    yield Checkbox("詳細ログ", id="verbose_log", value=True)
                
                yield Static("待機中...", classes="status-display", id="execution_status")
                
                # トレースツリー
                yield Tree("実行トレース", id="trace_tree", classes="trace-tree")
            
            # 結果パネル
            with Container(classes="results-panel"):
                yield Static("📊 実行結果", classes="section-title")
                
                # 結果表示
                yield ScrollableContainer(
                    Static("まだ実行されていません", id="result_display"),
                    classes="results-display"
                )
                
                # 実行統計
                yield Static("実行時間: -", id="execution_time")
                yield Static("メモリ使用量: -", id="memory_usage")
                yield Static("ステップ数: -", id="step_count")
    
    async def on_mount(self) -> None:
        """マウント時の初期化"""
        # トレースツリーの初期化
        tree = self.query_one("#trace_tree", Tree)
        tree.root.set_label("🌳 実行ツリー")
        
        # 初期状態の設定
        await self.update_input_mode()
    
    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """入力モード変更時の処理"""
        await self.update_input_mode()
    
    async def update_input_mode(self) -> None:
        """入力モードに応じてUIを更新"""
        try:
            radio_set = self.query_one("#input_mode", RadioSet)
            selected = radio_set.pressed_button
            
            input_instruction = self.query_one("#input_instruction", Static)
            input_area = self.query_one("#input_area", TextArea)
            
            if selected and selected.id == "natural_mode":
                input_instruction.update("自然言語で指示を入力してください（例: カレーの作り方を教えて）")
            elif selected and selected.id == "direct_mode":
                input_instruction.update = "S式を直接入力してください（例: (search \"カレー 作り方\")）"
            elif selected and selected.id == "history_mode":
                input_instruction.update = "履歴から選択するか、過去のS式を編集してください"
                # 履歴があれば最新のものを表示
                if self._app.session_history:
                    latest = self._app.session_history[-1]
                    if "input" in latest:
                        input_area.text = str(latest["input"])
        except Exception:
            # 初期化中はエラーを無視
            pass
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタンクリック処理"""
        button_id = event.button.id
        
        if button_id == "generate_btn":
            await self.generate_s_expression()
        elif button_id == "clear_btn":
            await self.clear_input()
        elif button_id == "execute_btn":
            await self.execute_current_expression()
        elif button_id == "step_btn":
            await self.step_execute()
        elif button_id == "stop_btn":
            await self.stop_execution()
    
    async def generate_s_expression(self) -> None:
        """S式を生成"""
        input_area = self.query_one("#input_area", TextArea)
        user_input = input_area.text.strip()
        
        if not user_input:
            self._app.notify("入力が空です", severity="warning")
            return
        
        radio_set = self.query_one("#input_mode", RadioSet)
        selected = radio_set.pressed_button
        
        try:
            # 生成中表示
            generated_area = self.query_one("#generated_expr", TextArea)
            generated_area.text = "生成中..."
            
            # デバッグログ
            print(f"=== S式生成開始 ===")
            print(f"入力: {user_input}")
            print(f"選択モード: {selected.id if selected else 'None'}")
            print(f"AgentService: {self._app.agent_service}")
            print(f"LLM URL: {self._app.agent_service.llm_base_url}")
            
            if selected and selected.id == "natural_mode":
                # 自然言語からS式生成
                print("自然言語モードで生成中...")
                generated_expr = await self._app.generate_s_expression(user_input)
                print(f"生成されたS式: {generated_expr}")
                
            elif selected and selected.id == "direct_mode":
                # 直接入力されたS式をそのまま使用
                print("直接モードで処理中...")
                generated_expr = user_input
            
            else:  # history_mode
                # 履歴から選択された式をそのまま使用
                print("履歴モードで処理中...")
                generated_expr = user_input
            
            # 生成されたS式を表示
            generated_area.text = generated_expr
            self.current_expression = generated_expr
            
            self._app.notify("S式が生成されました", severity="success")
            print("=== S式生成完了 ===")
            
        except Exception as e:
            print(f"=== S式生成エラー ===")
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
            
            generated_area = self.query_one("#generated_expr", TextArea)
            generated_area.text = f"エラー: {e}"
            self._app.notify(f"生成エラー: {e}", severity="error")
    
    async def execute_current_expression(self) -> None:
        """現在のS式を実行（自動再生成機能付き）"""
        if self.is_executing:
            self._app.notify("既に実行中です", severity="warning")
            return
        
        generated_area = self.query_one("#generated_expr", TextArea)
        s_expr = generated_area.text.strip()
        
        if not s_expr or s_expr == "生成中..." or s_expr.startswith("エラー:"):
            self._app.notify("実行可能なS式がありません", severity="warning")
            return
        
        try:
            self.is_executing = True
            self.execution_status = "実行中"
            
            # 実行状態を更新
            status_display = self.query_one("#execution_status", Static)
            status_display.update("🔄 実行中...")
            
            # トレースツリーをクリア
            tree = self.query_one("#trace_tree", Tree)
            tree.clear()
            tree.root.set_label("🌳 実行中...")
            
            # 実行開始
            start_time = asyncio.get_event_loop().time()
            
            # 自然言語の元クエリを取得
            input_area = self.query_one("#input_area", TextArea)
            original_query = input_area.text.strip()
            
            # 共通サービス経由で実行（自動再生成機能付き）
            context = {"original_query": original_query} if original_query else None
            result = await self._app.agent_service.evaluate_s_expression(s_expr, context, auto_retry=True)
            
            end_time = asyncio.get_event_loop().time()
            duration = (end_time - start_time) * 1000
            
            # 結果を表示
            result_display = self.query_one("#result_display", Static)
            result_display.update(f"✅ 実行完了\n\n結果: {result}")
            
            # 統計情報を更新
            self.query_one("#execution_time", Static).update(f"実行時間: {duration:.1f}ms")
            self.query_one("#step_count", Static).update("ステップ数: 1")  # TODO: 実際のステップ数
            
            # トレースツリーを更新
            tree.root.set_label("🌳 実行完了")
            tree.root.add(f"✅ {s_expr} → {result}")
            
            self.execution_status = "完了"
            status_display.update("✅ 実行完了")
            
            self._app.notify(f"実行完了: {duration:.1f}ms", severity="success")
            
            # ダッシュボードに結果を追加
            if hasattr(self._app, 'query_one'):
                try:
                    dashboard = self._app.query_one("DashboardTab")
                    dashboard.add_recent_execution("execute", str(result), duration, True)
                except:
                    pass  # ダッシュボードが見つからない場合は無視
            
        except Exception as e:
            # エラー処理
            result_display = self.query_one("#result_display", Static)
            result_display.update(f"❌ 実行エラー\n\nエラー: {e}")
            
            tree = self.query_one("#trace_tree", Tree)
            tree.root.set_label("🌳 実行エラー")
            tree.root.add(f"❌ {s_expr} → Error: {e}")
            
            self.execution_status = "エラー"
            status_display.update(f"❌ エラー: {e}")
            
            self._app.notify(f"実行エラー: {e}", severity="error")
            
        finally:
            self.is_executing = False
    
    async def step_execute(self) -> None:
        """ステップ実行（未実装）"""
        self._app.notify("ステップ実行機能は実装中です", severity="information")
    
    async def stop_execution(self) -> None:
        """実行を停止"""
        if not self.is_executing:
            self._app.notify("実行中の処理がありません", severity="warning")
            return
        
        # TODO: 実際の停止ロジック
        self.is_executing = False
        self.execution_status = "停止"
        
        status_display = self.query_one("#execution_status", Static)
        status_display.update("⏹️ 停止されました")
        
        self._app.notify("実行を停止しました", severity="warning")
    
    async def clear_input(self) -> None:
        """入力をクリア"""
        input_area = self.query_one("#input_area", TextArea)
        generated_area = self.query_one("#generated_expr", TextArea)
        result_display = self.query_one("#result_display", Static)
        
        input_area.text = ""
        generated_area.text = ""
        result_display.update("まだ実行されていません")
        
        # トレースツリーをクリア
        tree = self.query_one("#trace_tree", Tree)
        tree.clear()
        tree.root.set_label("🌳 実行トレース")
        
        # 統計情報をリセット
        self.query_one("#execution_time", Static).update("実行時間: -")
        self.query_one("#step_count", Static).update("ステップ数: -")
        
        self.execution_status = "待機中"
        status_display = self.query_one("#execution_status", Static)
        status_display.update("待機中...")
        
        self._app.notify("入力をクリアしました", severity="information")
    
    async def focus_generation_input(self) -> None:
        """生成入力にフォーカス"""
        input_area = self.query_one("#input_area", TextArea)
        input_area.focus()
    
    async def focus_execution_area(self) -> None:
        """実行エリアにフォーカス"""
        execute_btn = self.query_one("#execute_btn", Button)
        execute_btn.focus()
    
    def load_from_history(self, history_item: Dict[str, Any]) -> None:
        """履歴から項目を読み込み"""
        if "input" in history_item:
            input_area = self.query_one("#input_area", TextArea)
            generated_area = self.query_one("#generated_expr", TextArea)
            
            input_text = str(history_item["input"])
            input_area.text = input_text
            generated_area.text = input_text
            
            # 履歴モードに切り替え
            radio_set = self.query_one("#input_mode", RadioSet)
            history_radio = self.query_one("#history_mode", RadioButton)
            radio_set.pressed_button = history_radio

    async def save_current_content(self) -> None:
        """現在のワークスペース内容を保存"""
        try:
            # S式入力の内容を取得
            s_expr_input = self.query_one("#s_expr_input", TextArea)
            current_s_expr = s_expr_input.text.strip()
            
            # 自然言語入力の内容を取得
            natural_input = self.query_one("#natural_input", TextArea)
            current_query = natural_input.text.strip()
            
            if not current_s_expr and not current_query:
                self.app.notify("保存する内容がありません", severity="warning")
                return
            
            # 現在の日時でファイル名を生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workspace_save_{timestamp}.txt"
            
            # 保存内容を構築
            save_content = []
            save_content.append(f"# S式エージェント ワークスペース保存")
            save_content.append(f"# 保存日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            save_content.append("")
            
            if current_query:
                save_content.append("## 自然言語入力")
                save_content.append(current_query)
                save_content.append("")
            
            if current_s_expr:
                save_content.append("## S式")
                save_content.append(current_s_expr)
                save_content.append("")
            
            if self.last_result:
                save_content.append("## 最後の実行結果")
                save_content.append(str(self.last_result))
                save_content.append("")
            
            # ファイルに保存
            save_path = f"./{filename}"
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(save_content))
            
            self.app.notify(f"ワークスペースを {filename} に保存しました", severity="information")
            
        except Exception as e:
            self.app.notify(f"保存エラー: {e}", severity="error")
