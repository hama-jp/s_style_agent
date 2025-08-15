#!/usr/bin/env python3
"""
非同期評価器のテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.core.async_evaluator import evaluate_s_expression_async


async def test_async_evaluator():
    print("=== 非同期評価エンジンテスト ===")
    
    test_expressions = [
        "(notify \"非同期テスト開始\")",
        "(calc \"2 + 3 * 4\")",
        "(seq (notify \"ステップ1\") (calc \"10 / 2\") (notify \"ステップ2\"))",
        "(par (notify \"タスクA\") (notify \"タスクB\") (notify \"タスクC\"))",
        "(if (calc \"5 > 3\") (notify \"5は3より大きい\") (notify \"5は3以下\"))",
        "(let ((a 5) (b 10)) (calc \"5 + 10\"))",
        "(par (calc \"2**8\") (calc \"3**5\") (calc \"4**4\"))"
    ]
    
    for i, expr in enumerate(test_expressions, 1):
        print(f"\n--- テスト {i}: {expr} ---")
        try:
            start_time = asyncio.get_event_loop().time()
            result = await evaluate_s_expression_async(expr, "非同期テスト実行中")
            end_time = asyncio.get_event_loop().time()
            print(f"✓ 成功: {result} (実行時間: {end_time - start_time:.3f}秒)")
        except Exception as e:
            print(f"✗ エラー: {e}")
    
    # 並列実行パフォーマンステスト
    print("\n=== 並列実行パフォーマンステスト ===")
    
    # 順次実行
    print("\n順次実行:")
    seq_expr = "(seq (calc \"2**12\") (calc \"3**10\") (calc \"5**8\") (calc \"7**6\"))"
    start_time = asyncio.get_event_loop().time()
    seq_result = await evaluate_s_expression_async(seq_expr)
    seq_time = asyncio.get_event_loop().time() - start_time
    print(f"結果: {seq_result} (時間: {seq_time:.3f}秒)")
    
    # 並列実行
    print("\n並列実行:")
    par_expr = "(par (calc \"2**12\") (calc \"3**10\") (calc \"5**8\") (calc \"7**6\"))"
    start_time = asyncio.get_event_loop().time()
    par_result = await evaluate_s_expression_async(par_expr)
    par_time = asyncio.get_event_loop().time() - start_time
    print(f"結果: {par_result} (時間: {par_time:.3f}秒)")
    
    if seq_time > 0 and par_time > 0:
        speedup = seq_time / par_time
        print(f"\n並列実行による速度向上: {speedup:.2f}x")


if __name__ == "__main__":
    asyncio.run(test_async_evaluator())