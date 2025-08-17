# S式エージェントシステム - 次期フェーズ実装計画

## 🎯 実装目標: インタラクティブUI強化（Phase 2）

**期間**: 2-3週間  
**優先度**: 高  
**目標**: トレース機能の大幅なUX向上とデバッグ効率化

---

## 📊 現状分析

### ✅ 完了済み（Phase 1）
- [x] JSON-L形式での実行ログ出力
- [x] 基本TUIビューア実装（4タブ構成）
- [x] 操作レベルメタデータ収集
- [x] MCPトレース表示
- [x] 自動エラー修復機能
- [x] 統一アーキテクチャ（AgentService）

### 🎯 次期実装対象
**インタラクティブUI強化** - より直感的で効率的なS式実行トレース体験

---

## 🚀 具体的実装計画

### 1. サブツリー折りたたみ・展開機能 📁

#### 目標
複雑なS式の実行トレースを階層的に表示し、ユーザーが関心のある部分にフォーカスできるようにする。

#### 実装内容
```python
# s_style_agent/ui/trace_viewer.py に追加
class ExpandableTraceNode:
    def __init__(self, operation: str, s_expr: str, children: List['ExpandableTraceNode']):
        self.operation = operation
        self.s_expr = s_expr
        self.children = children
        self.is_expanded = True  # デフォルトは展開
        self.execution_status = "pending"  # pending, running, completed, error
        self.duration_ms = 0
        self.result = None
```

#### 技術仕様
- **Textual Tree Widget拡張**: 既存のTreeを拡張してカスタムノード表示
- **状態管理**: 各ノードの展開/折りたたみ状態を保持
- **キーバインディング**: Space キーで展開/折りたたみ切り替え
- **視覚的表現**: 
  - `▶` 折りたたみ状態
  - `▼` 展開状態
  - `🟡` 実行中
  - `🟢` 完了
  - `🔴` エラー

#### ファイル変更
- `s_style_agent/ui/trace_viewer.py`: メインビューア機能
- `s_style_agent/core/trace_logger.py`: 階層構造メタデータ追加

### 2. ブレークポイント・ステップオーバー機能 🔍

#### 目標
S式実行の任意の点で停止し、ステップ実行でデバッグできる機能を提供。

#### 実装内容
```python
# s_style_agent/core/debug_controller.py（新規作成）
class DebugController:
    def __init__(self):
        self.breakpoints: Set[str] = set()  # S式のハッシュまたはパス
        self.is_debugging = False
        self.current_step = None
        self.step_mode = "over"  # over, into, out
        
    async def should_break(self, s_expr: str, path: List[int]) -> bool:
        """ブレークポイントチェック"""
        
    async def step_execute(self, evaluator, s_expr, env):
        """ステップ実行制御"""
```

#### 技術仕様
- **ブレークポイント設定**: 
  - TUIでS式ノードをクリック/選択してブレークポイント設定
  - 設定されたブレークポイントは赤い●で表示
- **ステップ実行モード**:
  - `F10`: Step Over（同レベルの次のステップへ）
  - `F11`: Step Into（子ノードに入る）
  - `Shift+F11`: Step Out（親ノードに戻る）
  - `F5`: Continue（次のブレークポイントまで実行）
- **実行制御**:
  - 実行一時停止時のインタラクティブな状態検査
  - 変数値の表示・変更機能

#### ファイル変更
- `s_style_agent/core/debug_controller.py`: 新規作成
- `s_style_agent/core/async_evaluator.py`: デバッグ制御統合
- `s_style_agent/ui/trace_viewer.py`: デバッグUI追加

### 3. LLMプロンプト・レスポンス差分表示 📝

#### 目標
LLM呼び出し時のプロンプトと応答を詳細に可視化し、AI動作の透明性を向上。

#### 実装内容
```python
# s_style_agent/core/llm_trace.py（新規作成）
@dataclass
class LLMTraceEntry:
    timestamp: str
    model_name: str
    prompt: str
    response: str
    tokens_used: int
    duration_ms: float
    temperature: float
    system_prompt: str
    context: Dict[str, Any]
```

#### 技術仕様
- **詳細表示パネル**: 
  - プロンプト全文（システムプロンプト + ユーザープロンプト）
  - レスポンス全文（生のレスポンス + パースされた結果）
  - メタデータ（トークン数、実行時間、温度設定）
- **差分表示**:
  - 連続するLLM呼び出しでのプロンプト差分
  - Rich diff表示ライブラリ使用
- **コンテキスト追跡**:
  - どのS式評価でLLMが呼ばれたかの明確な紐付け
  - エラー再生成時の変更履歴

#### ファイル変更
- `s_style_agent/core/llm_trace.py`: 新規作成
- `s_style_agent/core/agent_service.py`: LLMトレース統合
- `s_style_agent/ui/trace_viewer.py`: LLM詳細表示タブ追加

### 4. パフォーマンス・メモリ監視ダッシュボード 📊

#### 目標
システムのリアルタイムパフォーマンス監視とボトルネック特定機能。

#### 実装内容
```python
# s_style_agent/monitoring/performance_monitor.py（新規作成）
class PerformanceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.memory_usage = []
        self.cpu_usage = []
        self.operation_times = {}
        
    def record_operation(self, operation: str, duration_ms: float):
        """操作実行時間を記録"""
        
    def get_system_stats(self) -> Dict[str, Any]:
        """システム統計情報を取得"""
```

#### 技術仕様
- **リアルタイム監視**:
  - メモリ使用量グラフ
  - CPU使用率監視
  - S式評価レイテンシ分布
- **ボトルネック分析**:
  - 最も時間のかかる操作TOP10
  - MCPツール呼び出し時間分析
  - 並列実行効率の可視化

#### ファイル変更
- `s_style_agent/monitoring/performance_monitor.py`: 新規作成
- `s_style_agent/ui/dashboard.py`: パフォーマンス表示追加

---

## 📅 実装スケジュール

### Week 1: 基盤整備
- [ ] **Day 1-2**: ExpandableTraceNode設計・実装
- [ ] **Day 3-4**: サブツリー折りたたみUI実装
- [ ] **Day 5-7**: DebugController基盤作成

### Week 2: デバッグ機能
- [ ] **Day 8-10**: ブレークポイント機能実装
- [ ] **Day 11-12**: ステップ実行機能実装
- [ ] **Day 13-14**: デバッグUI統合・テスト

### Week 3: LLM可視化・監視
- [ ] **Day 15-17**: LLMプロンプト/レスポンス表示機能
- [ ] **Day 18-19**: パフォーマンス監視ダッシュボード
- [ ] **Day 20-21**: 統合テスト・ドキュメント更新

---

## 🧪 テスト計画

### 機能テスト
1. **サブツリー操作**: 複雑なネストしたS式での展開/折りたたみ
2. **ブレークポイント**: 各種S式パターンでの停止・再開
3. **ステップ実行**: Step Over/Into/Outの正確な動作
4. **LLM可視化**: 複数LLM呼び出しでの差分表示
5. **パフォーマンス**: 長時間実行でのメモリリーク検証

### ユーザビリティテスト
- 新規ユーザーによるデバッグ機能の直感的操作
- 複雑なS式デバッグシナリオでの効率性検証

### パフォーマンステスト
- 大量ノード（1000+）でのUI応答性
- 長時間実行（30分+）でのメモリ安定性

---

## 🎯 成功指標

### 定量的指標
- [ ] **ノード操作**: 1000+ノードでも < 100ms 応答
- [ ] **ブレークポイント**: 設定から停止まで < 50ms
- [ ] **メモリ効率**: 長時間実行でメモリ増加 < 10MB/hour
- [ ] **ユーザビリティ**: 新規ユーザーが10分で基本操作習得

### 定性的指標
- [ ] **直感性**: クリックベースの操作で混乱なし
- [ ] **デバッグ効率**: 従来比50%の時間でバグ特定
- [ ] **透明性**: LLM動作の完全な可視化
- [ ] **安定性**: 24時間連続実行でクラッシュなし

---

## 🔧 技術的考慮事項

### アーキテクチャ
- **疎結合設計**: デバッグ機能はオプショナルで無効化可能
- **プラグイン型**: 将来的な機能拡張を容易にする設計
- **パフォーマンス**: UIレスポンス性を最優先

### 互換性
- **既存機能**: 現在のTUI機能への影響最小化
- **CLI互換**: CLIモードでもデバッグ情報アクセス可能
- **設定保存**: ブレークポイント等の永続化

### セキュリティ
- **サンドボックス**: デバッグ中のコード実行制限
- **プライバシー**: LLMプロンプト/レスポンスの適切なマスキング

---

## 📚 必要なライブラリ・依存関係

### 新規追加
```toml
# pyproject.toml に追加
[tool.uv.dependencies]
rich-diff = "^1.0.0"      # 差分表示用
psutil = "^5.9.0"         # システム監視用
memory-profiler = "^0.61" # メモリプロファイリング
```

### 既存ライブラリ拡張
- **Textual**: カスタムウィジェット作成
- **Rich**: 高度なテキスト表示

---

## 🚦 リスク・制約事項

### 技術的リスク
- **複雑性増加**: UI応答性への影響
- **メモリ使用量**: 大量トレースデータの処理
- **並行性**: デバッグ中の状態管理

### 軽減策
- **段階的実装**: 機能を小さく分割して安全に追加
- **パフォーマンステスト**: 各段階での性能検証
- **フォールバック**: 問題発生時の既存UI維持

---

## 🎉 期待される効果

### 開発者体験
- **デバッグ効率**: 複雑なS式のトラブルシューティング時間50%短縮
- **学習効果**: AI動作の可視化による理解深化
- **生産性**: 直感的なブレークポイント・ステップ実行

### プロダクト価値
- **差別化**: 他のAIエージェントシステムにない説明可能性
- **信頼性**: 透明な実行過程による信頼向上
- **拡張性**: 将来的な高度なデバッグ機能の基盤

---

**作成日**: 2025-01-17  
**作成者**: Claude Code  
**承認**: 実装開始前にレビュー必須  

🤖 Generated with [Claude Code](https://claude.ai/code)