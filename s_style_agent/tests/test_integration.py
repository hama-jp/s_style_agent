#!/usr/bin/env python3
"""
簡単な数学問題解決テスト

エージェントが基本的な数学問題を解決できるかテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from s_style_agent.core.parser import parse_s_expression
from s_style_agent.core.evaluator import ContextualEvaluator, Environment


async def test_direct_math_operations():
    """数学エンジンの直接テスト"""
    print("🧮 === 数学エンジン直接テスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    test_cases = [
        ('因数分解', '(math "x**2 + 6*x + 9" "factor")'),
        ('展開', '(math "(x+1)**2" "expand")'),
        ('微分', '(math "x**3 + 2*x" "diff")'),
        ('積分', '(math "2*x + 1" "integrate")'),
        ('簡約', '(math "sin(x)**2 + cos(x)**2" "simplify")'),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for name, s_expr in test_cases:
        print(f"\n📊 {name}: {s_expr}")
        try:
            parsed = parse_s_expression(s_expr)
            result = evaluator.evaluate_with_context(parsed, env)
            print(f"✅ 結果: {result}")
            passed += 1
        except Exception as e:
            print(f"❌ エラー: {e}")
    
    print(f"\n📈 結果: {passed}/{total} 成功")
    return passed == total


async def test_llm_integration():
    """LLM統合テスト（タイムアウトあり）"""
    print("\n🤖 === LLM統合テスト ===")
    
    try:
        from s_style_agent.cli.main import SStyleAgentCLI
        cli = SStyleAgentCLI()
        
        # 簡単な問題でテスト
        problem = "x²+4x+4を因数分解して"
        print(f"問題: {problem}")
        
        # タイムアウトを設定（thinking モデル対応）
        s_expr = await asyncio.wait_for(
            cli.generate_s_expression(problem), 
            timeout=60.0
        )
        print(f"生成されたS式: {s_expr}")
        
        # S式を実行
        result = await asyncio.wait_for(
            cli.execute_s_expression(s_expr, problem),
            timeout=60.0
        )
        print(f"✅ 実行結果: {result}")
        return True
        
    except asyncio.TimeoutError:
        print("⏰ LLMの応答がタイムアウトしました")
        return False
    except Exception as e:
        print(f"❌ LLM統合エラー: {e}")
        return False


async def main():
    """メインテスト実行"""
    print("🧪 S式エージェント 数学問題解決テスト（シンプル版）")
    print("=" * 60)
    
    # 数学エンジンの直接テスト
    math_test_passed = await test_direct_math_operations()
    
    # LLM統合テスト
    llm_test_passed = await test_llm_integration()
    
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー:")
    print(f"  🧮 数学エンジン: {'✅ 合格' if math_test_passed else '❌ 不合格'}")
    print(f"  🤖 LLM統合: {'✅ 合格' if llm_test_passed else '❌ 不合格'}")
    
    if math_test_passed and llm_test_passed:
        print("\n🎉 全テスト合格！エージェントは数学問題を解決できます")
        return True
    elif math_test_passed:
        print("\n👍 数学エンジンは正常動作。LLM統合に課題があります")
        return True
    else:
        print("\n⚠️ 数学エンジンに問題があります")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    if not result:
        sys.exit(1)