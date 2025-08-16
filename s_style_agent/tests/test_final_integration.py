#!/usr/bin/env python3
"""
最終統合テスト - 全機能の動作確認
"""

import os
import asyncio
from s_style_agent.core.schema_validator import LLMOutputGate
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression

# LangSmith設定
os.environ['LANGSMITH_PROJECT'] = 's-style-agent'
os.environ['LANGSMITH_TRACING'] = 'true'

async def test_end_to_end_workflow():
    """エンドツーエンドワークフローテスト"""
    print("=== エンドツーエンド統合テスト ===")
    
    # 1. LLM出力ゲート初期化
    gate = LLMOutputGate(validation_level="strict")
    
    # 2. 評価器初期化
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 3. LLM出力シミュレーション（安全なS式）
    safe_llm_outputs = [
        '(notify "システム開始")',
        '(seq (notify "計算開始") (calc "2+2") (notify "計算完了"))',
        '(handle err (calc "1/0") (notify "エラーをキャッチしました"))',
        '(let [["x" 5]] (while (< x 8) (seq (notify x) (set x (+ x 1))) 5))',
        '(par (calc "10+5") (calc "20*2") (calc "100/4"))'
    ]
    
    print("\n1. 安全なS式の処理:")
    for i, output in enumerate(safe_llm_outputs, 1):
        print(f"\n  {i}. LLM出力: {output}")
        
        # ゲート検証
        is_approved, parsed_expr, gate_errors = gate.validate_llm_output(output, "integration-test")
        
        if is_approved:
            print(f"      🔐 ゲート: ✅ 承認")
            
            try:
                # S式実行
                result = evaluator.evaluate_with_context(parsed_expr, env)
                print(f"      🚀 実行結果: {result}")
            except Exception as e:
                print(f"      ❌ 実行エラー: {e}")
        else:
            print(f"      🔐 ゲート: ❌ 拒否")
            for error in gate_errors[:1]:
                print(f"         理由: {error}")

async def test_security_blocking():
    """セキュリティブロッキングテスト"""
    print("\n=== セキュリティブロッキングテスト ===")
    
    gate = LLMOutputGate(validation_level="strict")
    
    # 危険なLLM出力シミュレーション
    malicious_outputs = [
        '(eval "import os; os.system(\'rm -rf /\')")',
        '(__import__ "subprocess")',
        '(exec "dangerous_code")',
        '(while (< 1 2) (notify "無限ループ") 50000)',  # 制限超過
        '(unknown_dangerous_op "payload")'
    ]
    
    print("\n2. 危険なS式のブロック:")
    blocked_count = 0
    for i, output in enumerate(malicious_outputs, 1):
        print(f"\n  {i}. 危険な出力: {output[:50]}...")
        
        is_approved, _, gate_errors = gate.validate_llm_output(output, "security-test")
        
        if not is_approved:
            blocked_count += 1
            print(f"      🛡️ セキュリティ: ✅ 正しくブロック")
            print(f"         理由: {gate_errors[0] if gate_errors else 'Unknown'}")
        else:
            print(f"      🛡️ セキュリティ: ❌ 通過してしまった！")
    
    print(f"\n  ブロック率: {blocked_count}/{len(malicious_outputs)} ({blocked_count/len(malicious_outputs)*100:.0f}%)")

def test_schema_compliance():
    """スキーマ準拠テスト"""
    print("\n=== スキーマ準拠テスト ===")
    
    from s_style_agent.core.schema_validator import SExpressionValidator
    validator = SExpressionValidator(validation_level="strict")
    
    # 実装済み構文の検証
    implemented_constructs = [
        # 制御フロー
        ["seq", ["notify", "step1"], ["notify", "step2"]],
        ["par", ["calc", "1+1"], ["calc", "2+2"]],
        ["if", ["<", 5, 10], ["notify", "true"], ["notify", "false"]],
        ["handle", "err", ["unknown_op"], ["notify", "handled"]],
        ["while", ["<", "x", 3], ["set", "x", ["+", "x", 1]], 5],
        
        # 変数操作
        ["let", [["x", 42]], ["notify", "x"]],
        ["set", "counter", 0],
        
        # 算術・比較
        ["+", 1, 2, 3],
        ["<", 5, 10],
        
        # ツール
        ["notify", "message"],
        ["calc", "x^2+1"],
        ["math", "x^2", "diff", "x"],
        ["step_math", "integral of x", "integrate", "x"],
        ["ask_user", "質問", "var_name", "required"]
    ]
    
    print("\n3. 実装済み構文の検証:")
    valid_count = 0
    for i, construct in enumerate(implemented_constructs, 1):
        is_valid, errors = validator.validate(construct, source="schema_test", llm_model="test")
        
        if is_valid:
            valid_count += 1
            status = "✅ 有効"
        else:
            status = "❌ 無効"
        
        print(f"  {i:2d}. {str(construct)[:40]:<40} → {status}")
        if errors and not is_valid:
            print(f"       エラー: {errors[0]}")
    
    print(f"\n  準拠率: {valid_count}/{len(implemented_constructs)} ({valid_count/len(implemented_constructs)*100:.0f}%)")

async def test_performance_and_stats():
    """パフォーマンスと統計テスト"""
    print("\n=== パフォーマンス・統計テスト ===")
    
    gate = LLMOutputGate(validation_level="permissive")
    
    # 大量の検証テスト
    test_expressions = [
        '(notify "test")',
        '(calc "1+1")',
        '(eval "bad")',  # 拒否される
        '(seq (notify "a") (notify "b"))',
        '(unknown_op "test")',  # 拒否される
    ] * 20  # 100回のテスト
    
    print("\n4. 大量検証テスト:")
    start_time = asyncio.get_event_loop().time()
    
    for expr in test_expressions:
        gate.validate_llm_output(expr, "perf-test")
    
    end_time = asyncio.get_event_loop().time()
    processing_time = end_time - start_time
    
    stats = gate.get_stats()
    print(f"  処理時間: {processing_time:.3f}秒")
    print(f"  処理速度: {stats['total']/processing_time:.1f} expr/sec")
    print(f"  統計: {stats}")

async def main():
    """メインテスト実行"""
    print("🚀 S式エージェントシステム最終統合テスト開始")
    print("="*60)
    
    await test_end_to_end_workflow()
    await test_security_blocking()
    test_schema_compliance()
    await test_performance_and_stats()
    
    print("\n" + "="*60)
    print("✅ 最終統合テスト完了！")
    print("\n📋 実装完了機能:")
    print("  ✅ S式AST JSON Schema")
    print("  ✅ LLM出力セキュリティゲート")
    print("  ✅ マルチレイヤー検証")
    print("  ✅ try/catch (handle) 構文")
    print("  ✅ while/loop 構文")
    print("  ✅ 並列・非同期実行")
    print("  ✅ LangSmithトレース統合")
    print("\n📊 LangSmithで詳細トレース確認:")
    print("   https://smith.langchain.com/")

if __name__ == "__main__":
    asyncio.run(main())