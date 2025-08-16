#!/usr/bin/env python3
"""
AST Schema + ゲート検証テスト
"""

import os
from s_style_agent.core.schema_validator import SExpressionValidator, LLMOutputGate
from s_style_agent.core.parser import parse_s_expression

# LangSmith設定
os.environ['LANGSMITH_PROJECT'] = 's-style-agent'
os.environ['LANGSMITH_TRACING'] = 'true'

def test_schema_validation():
    """スキーマ検証のテスト"""
    print("=== スキーマ検証テスト ===")
    
    validator = SExpressionValidator(validation_level="strict")
    
    # 1. 正常なS式
    print("\n1. 正常なS式:")
    valid_expressions = [
        ["notify", "Hello World"],
        ["seq", ["notify", "Step 1"], ["notify", "Step 2"]],
        ["while", ["<", "x", 10], ["set", "x", ["+", "x", 1]], 5],
        ["handle", "err", ["calc", "1+1"], ["notify", "Error occurred"]]
    ]
    
    for expr in valid_expressions:
        is_valid, errors = validator.validate(expr, source="test", llm_model="test-model")
        status = "✅ 通過" if is_valid else "❌ 失敗"
        print(f"  {expr} → {status}")
        if errors:
            for error in errors:
                print(f"    エラー: {error}")

def test_security_checks():
    """セキュリティチェックのテスト"""
    print("\n=== セキュリティチェックテスト ===")
    
    validator = SExpressionValidator(validation_level="strict")
    
    # 2. セキュリティ違反S式
    print("\n2. セキュリティ違反S式:")
    malicious_expressions = [
        ["__import__", "os"],
        ["eval", "malicious_code"],
        ["exec", "dangerous_code"],
        # 深すぎるネスト（テスト用に小さく設定）
        ["seq"] + [["notify", f"deep_{i}"] for i in range(25)]  # 深度制限テスト
    ]
    
    for expr in malicious_expressions:
        is_valid, errors = validator.validate(expr, source="malicious", llm_model="test-model")
        status = "✅ 正しく拒否" if not is_valid else "❌ 通過してしまった"
        print(f"  {str(expr)[:60]}... → {status}")
        if errors:
            for error in errors[:2]:  # 最初の2個のエラーのみ表示
                print(f"    エラー: {error}")

def test_llm_output_gate():
    """LLM出力ゲートのテスト"""
    print("\n=== LLM出力ゲートテスト ===")
    
    gate = LLMOutputGate(validation_level="strict")
    
    # 3. LLM出力シミュレーション
    print("\n3. LLM出力シミュレーション:")
    llm_outputs = [
        '(notify "Hello from LLM")',
        '(seq (notify "Starting task") (calc "2+2"))',
        '(handle err (calc "invalid") (notify "Error caught"))',
        '(while (< counter 3) (set counter (+ counter 1)) 5)',
        # 無効な出力
        '(eval "dangerous code")',
        'invalid s-expression syntax',
        '(unknown_operation "test")'
    ]
    
    for output in llm_outputs:
        is_approved, parsed_expr, errors = gate.validate_llm_output(output, "test-llm")
        status = "✅ 承認" if is_approved else "❌ 拒否"
        print(f"  '{output}' → {status}")
        if errors:
            for error in errors[:1]:  # 最初のエラーのみ表示
                print(f"    理由: {error}")
    
    # 統計表示
    print(f"\n統計: {gate.get_stats()}")

def test_validation_levels():
    """検証レベルのテスト"""
    print("\n=== 検証レベルテスト ===")
    
    # 実験的操作のテスト
    experimental_expr = ["db-query", "SELECT * FROM users"]
    
    print("\n4. 検証レベル別テスト:")
    for level in ["strict", "permissive", "experimental"]:
        validator = SExpressionValidator(validation_level=level)
        is_valid, errors = validator.validate(experimental_expr, source="test", llm_model="test")
        status = "✅ 通過" if is_valid else "❌ 拒否"
        print(f"  {level}モード: {experimental_expr} → {status}")
        if errors:
            for error in errors:
                print(f"    エラー: {error}")

def test_edge_cases():
    """エッジケースのテスト"""
    print("\n=== エッジケーステスト ===")
    
    validator = SExpressionValidator(validation_level="strict")
    
    # 5. エッジケース
    print("\n5. エッジケース:")
    edge_cases = [
        [],  # 空リスト
        [""],  # 空文字列演算子
        ["notify"],  # 引数不足
        ["if", True, "then", "else", "extra"],  # 引数過多
        ["set", 123, "value"],  # 変数名が数値
        ["while", True, "body", -1],  # 負の最大反復数
    ]
    
    for expr in edge_cases:
        is_valid, errors = validator.validate(expr, source="edge_test", llm_model="test")
        status = "✅ 通過" if is_valid else "❌ 拒否"
        print(f"  {expr} → {status}")
        if errors:
            for error in errors[:1]:  # 最初のエラーのみ表示
                print(f"    エラー: {error}")

def main():
    """メインテスト実行"""
    print("AST Schema + ゲート検証テスト開始")
    
    test_schema_validation()
    test_security_checks()
    test_llm_output_gate()
    test_validation_levels()
    test_edge_cases()
    
    print("\n✅ ゲート検証システムテスト完了！")
    print("📊 LangSmithで詳細なトレースを確認: https://smith.langchain.com/")

if __name__ == "__main__":
    main()