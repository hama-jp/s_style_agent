#!/usr/bin/env python3
"""
handle構文シンプルテスト
"""

from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression

def test_simple_handle():
    """シンプルなhandle構文テスト"""
    print("=== handle構文シンプルテスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 1. 成功例
    print("\n1. 正常ケース:")
    expr = parse_s_expression('(handle err (notify "成功") (notify "失敗"))')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")
    
    # 2. エラーケース - 未定義オペレーション
    print("\n2. エラーキャッチケース:")
    expr = parse_s_expression('(handle err (undefined_op "test") (notify "エラーをキャッチしました！"))')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")
    
    # 3. ネストしたhandle
    print("\n3. ネストhandle:")
    expr = parse_s_expression('''
    (handle outer
        (handle inner
            (bad_operation)
            (notify "内側でキャッチ"))
        (notify "外側でキャッチ"))
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")
    
    # 4. エラー情報の簡単な確認（辞書アクセスではなく通知）
    print("\n4. エラー情報確認:")
    expr = parse_s_expression('''
    (handle error_var
        (bad_op "test")
        (notify "エラー情報を受信しました"))
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")

if __name__ == "__main__":
    test_simple_handle()