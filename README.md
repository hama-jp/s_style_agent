# S式エージェントシステム

S式を応用した説明可能なエージェントシステムの試作実装です。

## 概要

このシステムは、LLMが生成するS式（S-expression）を通じてタスクを実行する、説明可能なエージェントアーキテクチャを提供します。

### 主な特徴

- **説明可能性**: S式による明示的な実行計画
- **ユーザー制御**: 生成されたS式の確認・編集が可能
- **文脈考慮**: タスク全体の文脈を考慮したS式評価
- **MCP対応設計**: 将来的なMCP（Model Context Protocol）拡張に対応
- **langchain統合**: langchain/langgraphによるトレース機能

## セットアップ

### 必要条件

- Python 3.12+
- uv (Pythonパッケージマネージャー)
- ローカルLLMサーバー（OpenAI API互換）

### インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd s-style-agent

# uvで依存関係をインストール
uv sync
```

### 環境設定

環境変数で設定をカスタマイズできます：

```bash
# LLM設定
export LLM_BASE_URL="http://192.168.79.1:1234/v1"
export LLM_MODEL_NAME="unsloth/gpt-oss-120b"
export LLM_TEMPERATURE="0.3"

# システム設定
export DEBUG="false"
export LANGSMITH_PROJECT="s-style-agent"
```

## 使用方法

### 基本的な使い方

```bash
# システムを起動
uv run python main.py
```

### CLIコマンド

- `/help` - ヘルプを表示
- `/generate` - LLMでS式を生成
- `/parse` - S式の構文をチェック
- `/execute` - S式を実行
- `/history` - セッション履歴を表示
- `/tools` - 利用可能ツール一覧
- `/exit` - システムを終了

### 使用例

```
> 2足す3を計算して
生成されたS式: (calc "2 + 3")
実行しますか？ (y/n/e=編集): y
実行結果: 5

> (seq (notify "開始") (calc "10 * 5") (notify "終了"))
[NOTIFY] 開始
[NOTIFY] 終了
実行結果: 終了
```

## S式構文

### 基本構文

- `(seq step1 step2 ...)` - 順次実行
- `(par stepA stepB ...)` - 並列実行
- `(if cond then else)` - 条件分岐
- `(let ((var expr) ...) body)` - 変数束縛

### 利用可能ツール

- `(notify "message")` - ユーザー通知
- `(calc "expression")` - 数式計算
- `(search "query")` - 情報検索
- `(db-query "query")` - データベースクエリ

## アーキテクチャ

```
s-style-agent/
├── s_style_agent/
│   ├── core/              # コア機能
│   │   ├── parser.py      # S式パーサー
│   │   └── evaluator.py   # 評価エンジン
│   ├── tools/             # ツール実装
│   │   ├── base.py        # ベースクラス
│   │   └── builtin_tools.py # 組み込みツール
│   ├── cli/               # CLIインターフェース
│   │   └── main.py        # メインCLI
│   └── config/            # 設定管理
│       └── settings.py    # 設定クラス
├── concept/               # 既存プロトタイプ
└── tests/                 # テストコード
```

## テスト

```bash
# 統合テストを実行
uv run python test_integration.py

# 個別コンポーネントのテスト
uv run python s_style_agent/core/parser.py
uv run python s_style_agent/core/evaluator.py
uv run python s_style_agent/tools/builtin_tools.py
```

## 拡張

### 新しいツールの追加

```python
from s_style_agent.tools.base import BaseTool, ToolSchema, ToolParameter, ToolResult

class MyTool(BaseTool):
    def __init__(self):
        super().__init__("my-tool", "カスタムツールの説明")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="param1",
                    type="string",
                    description="パラメータの説明",
                    required=True
                )
            ]
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # ツールの実装
        return ToolResult(success=True, result="結果")

# ツールを登録
from s_style_agent.tools.base import global_registry
global_registry.register(MyTool())
```

## ライセンス

MIT License

## 貢献

プルリクエストや Issue の報告を歓迎します。

## 今後の予定

- [ ] MCP（Model Context Protocol）統合
- [ ] より多くの組み込みツール
- [ ] Webインターフェース
- [ ] 詳細なログ・監視機能
- [ ] パフォーマンス最適化