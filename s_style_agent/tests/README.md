# S式エージェントシステム テストスイート

## テストファイル構成

### 必須テスト
- `test_integration.py` - システム統合テスト
- `test_math_engine.py` - 記号数学エンジンテスト
- `test_local_llm.py` - LLMサーバー接続テスト

### テスト実行方法

#### 個別テスト実行
```bash
# 数学エンジンテスト
uv run python s_style_agent/tests/test_math_engine.py

# 統合テスト
uv run python s_style_agent/tests/test_integration.py

# LLMサーバーテスト
uv run python s_style_agent/tests/test_local_llm.py
```

#### 全テスト実行
```bash
# プロジェクトルートから
uv run python -m pytest s_style_agent/tests/ -v
```

## テスト内容

### test_math_engine.py
- ✅ 因数分解、展開、微分、積分
- ✅ 極限、テイラー展開、方程式求解
- ✅ S式統合（mathツール）
- ✅ エラーハンドリング

### test_integration.py
- ✅ 数学エンジン直接テスト
- ⚠️ LLM統合テスト（タイムアウト問題）

### test_local_llm.py
- ✅ LLMサーバー接続確認
- ✅ モデル一覧取得
- ✅ S式生成テスト

## 期待される結果

### 数学エンジン: 100% 成功
```
✅ 因数分解: x²+6x+9 → (x + 3)²
✅ 展開: (x+1)² → x²+2x+1
✅ 微分: x³+2x → 3x²+2
✅ 積分: 2x+1 → x²+x
✅ 簡約: sin²(x)+cos²(x) → 1
```

### 統合テスト: 数学エンジン合格、LLM統合要調整

## 必要な前提条件

1. **LLMサーバー**: http://192.168.79.1:1234/v1 で動作
2. **Python環境**: uv + Python 3.12
3. **依存関係**: sympy, langchain, langgraph等

## 設定

### タイムアウト設定
- **LLM応答**: 60秒 (thinking モデル対応)
- **S式実行**: 60秒
- **HTTP リクエスト**: 60秒

ローカルLLMとthinkingモデルの長い推論時間に対応した設定です。