#!/usr/bin/env python3
"""
統合テスト

S式エージェントシステムの主要機能をテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.core.parser import parse_s_expression, SExpressionParseError
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.tools.builtin_tools import register_builtin_tools
from s_style_agent.cli.main import SStyleAgentCLI


async def test_parser():
    """パーサーのテスト"""
    print("=== パーサーテスト ===")
    
    test_cases = [
        "(notify \"Hello World\")",
        "(seq (calc \"2+3\") (notify \"結果表示\"))",
        "(if (calc \"1 < 2\") (notify \"真\") (notify \"偽\"))",
        "(let ((x 10) (y 20)) (calc \"10+20\"))",
        "(par (search \"天気\") (search \"ニュース\"))"
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nテスト {i}: {case}")
        try:
            result = parse_s_expression(case)
            print(f"✓ パース成功: {result}")
        except SExpressionParseError as e:
            print(f"✗ パースエラー: {e}")


async def test_evaluator():
    """評価エンジンのテスト"""
    print("\n\n=== 評価エンジンテスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    test_expressions = [
        "(notify \"テスト開始\")",
        "(calc \"2 + 3 * 4\")",
        "(seq (notify \"ステップ1\") (calc \"10 / 2\") (notify \"ステップ2\"))",
        "(if (calc \"5 > 3\") (notify \"5は3より大きい\") (notify \"5は3以下\"))",
        "(let ((a 5) (b 10)) (calc \"5 + 10\"))"
    ]
    
    for i, expr in enumerate(test_expressions, 1):
        print(f"\nテスト {i}: {expr}")
        try:
            parsed = parse_s_expression(expr)
            result = evaluator.evaluate_with_context(parsed, env)
            print(f"✓ 評価成功: {result}")
        except Exception as e:
            print(f"✗ 評価エラー: {e}")


async def test_tools():
    """ツールシステムのテスト"""
    print("\n\n=== ツールシステムテスト ===")
    
    registry = register_builtin_tools()
    
    # 利用可能ツール確認
    print("利用可能ツール:")
    for tool_name in registry.list_tools():
        print(f"  - {tool_name}")
    
    # 各ツールのテスト
    tool_tests = [
        ("notify", {"message": "テスト通知"}),
        ("calc", {"expression": "2 ** 8"}),
        ("search", {"query": "Python langchain"}),
        ("db-query", {"query": "SELECT * FROM test_table"}),
    ]
    
    for tool_name, params in tool_tests:
        print(f"\n{tool_name}ツールテスト:")
        try:
            result = await registry.execute_tool(tool_name, **params)
            if result.success:
                print(f"✓ 成功: {result.result}")
            else:
                print(f"✗ 失敗: {result.error}")
        except Exception as e:
            print(f"✗ エラー: {e}")


async def test_llm_integration():
    """LLM統合テスト"""
    print("\n\n=== LLM統合テスト ===")
    
    cli = SStyleAgentCLI()
    
    test_inputs = [
        "2足す3を計算して",
        "Hello Worldと表示して",
        "今日の天気を調べて教えて"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\nテスト {i}: {user_input}")
        try:
            s_expr = await cli.generate_s_expression(user_input)
            print(f"生成されたS式: {s_expr}")
            
            # パース確認
            success, parsed, error = cli.parse_s_expression_safe(s_expr)
            if success:
                print(f"✓ パース成功: {parsed}")
                
                # 実行テスト
                result = await cli.execute_s_expression(s_expr, user_input)
                print(f"✓ 実行結果: {result}")
            else:
                print(f"✗ パースエラー: {error}")
                
        except Exception as e:
            print(f"✗ エラー: {e}")


async def main():
    """メインテスト実行"""
    print("S式エージェントシステム 統合テスト開始")
    print("=" * 50)
    
    try:
        await test_parser()
        await test_evaluator()
        await test_tools()
        await test_llm_integration()
        
        print("\n\n" + "=" * 50)
        print("統合テスト完了")
        
    except Exception as e:
        print(f"\n\n統合テストでエラーが発生: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())