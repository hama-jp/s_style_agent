#!/usr/bin/env python3
"""
while構文の制限・エラーケーステスト
"""

import os
import asyncio
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.async_evaluator import AsyncContextualEvaluator, AsyncEnvironment
from s_style_agent.core.parser import parse_s_expression

# LangSmith設定
os.environ['LANGSMITH_PROJECT'] = 's-style-agent'
os.environ['LANGSMITH_TRACING'] = 'true'

def test_max_iterations_limit():
    """最大反復数制限テスト"""
    print("=== 最大反復数制限テスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 1. 制限内での実行
    print("\n1. 制限内（5回）:")
    env.define("count", 0)
    expr = parse_s_expression('''
    (while (< count 100)
        (set count (+ count 1))
        5)
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}, 最終count: {env.lookup('count')}")
    
    # 2. 制限を超える場合
    print("\n2. 制限超過テスト（10000超過でエラー）:")
    try:
        expr = parse_s_expression('(while (< 1 2) (notify "無限ループ") 20000)')
        result = evaluator.evaluate_with_context(expr, env)
        print(f"エラーが発生すべきでした: {result}")
    except Exception as e:
        print(f"期待通りエラー: {type(e).__name__}: {e}")
    
    # 3. 無効な最大反復数
    print("\n3. 無効な最大反復数:")
    try:
        expr = parse_s_expression('(while (< 1 2) (notify "test") -5)')
        result = evaluator.evaluate_with_context(expr, env)
        print(f"エラーが発生すべきでした: {result}")
    except Exception as e:
        print(f"期待通りエラー: {type(e).__name__}: {e}")

def test_error_cases():
    """その他のエラーケーステスト"""
    print("\n=== エラーケーステスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 1. 引数数エラー
    print("\n1. 引数数エラー:")
    try:
        expr = parse_s_expression('(while (< 1 2))')  # bodyがない
        result = evaluator.evaluate_with_context(expr, env)
        print(f"エラーが発生すべきでした: {result}")
    except Exception as e:
        print(f"期待通りエラー: {type(e).__name__}: {e}")
    
    # 2. 未定義変数set
    print("\n2. 未定義変数set:")
    try:
        expr = parse_s_expression('(set undefined_var 42)')
        result = evaluator.evaluate_with_context(expr, env)
        print(f"エラーが発生すべきでした: {result}")
    except Exception as e:
        print(f"期待通りエラー: {type(e).__name__}: {e}")
    
    # 3. set引数エラー
    print("\n3. set引数エラー:")
    try:
        expr = parse_s_expression('(set 123 42)')  # 変数名が数値
        result = evaluator.evaluate_with_context(expr, env)
        print(f"エラーが発生すべきでした: {result}")
    except Exception as e:
        print(f"期待通りエラー: {type(e).__name__}: {e}")

async def test_async_while_limits():
    """非同期whileの制限テスト"""
    print("\n=== 非同期while制限テスト ===")
    
    evaluator = AsyncContextualEvaluator()
    env = AsyncEnvironment()
    
    # 非同期での最大反復数制限
    print("\n1. 非同期最大反復数制限:")
    await env.define("async_count", 0)
    expr = parse_s_expression('''
    (while (< async_count 50)
        (seq
            (set async_count (+ async_count 1))
            (notify async_count))
        10)
    ''')
    result = await evaluator.evaluate_with_context(expr, env)
    final_count = await env.lookup("async_count")
    print(f"結果: {result}, 最終async_count: {final_count}")

def test_real_world_scenarios():
    """実世界のユースケーステスト"""
    print("\n=== 実世界シナリオテスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 再試行ロジック（失敗後の再実行）
    print("\n1. 再試行ロジックシミュレーション:")
    env.define("retry_count", 0)
    env.define("success", False)  # 成功フラグ
    
    expr = parse_s_expression('''
    (while (< retry_count 3)
        (seq
            (set retry_count (+ retry_count 1))
            (notify "試行回数: " + retry_count)
            (if (< retry_count 3)
                (notify "失敗")
                (seq
                    (set success True)
                    (notify "成功"))))
        5)
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")
    print(f"最終状態 - retry_count: {env.lookup('retry_count')}, success: {env.lookup('success')}")

def main():
    """メインテスト実行"""
    print("while構文制限・エラーケーステスト開始")
    
    test_max_iterations_limit()
    test_error_cases()
    asyncio.run(test_async_while_limits())
    test_real_world_scenarios()
    
    print("\n✅ while構文制限・エラーケーステスト完了！")
    print("📊 LangSmithで詳細なトレースを確認: https://smith.langchain.com/")

if __name__ == "__main__":
    main()