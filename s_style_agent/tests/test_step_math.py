#!/usr/bin/env python3
"""
段階的数学解法システムのテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.tools.math_engine import StepMathEngine
from s_style_agent.tools.builtin_tools import register_builtin_tools
from s_style_agent.cli.main import SStyleAgentCLI


async def test_step_math_tool():
    """段階的数学ツールの直接テスト"""
    print("=== 段階的数学ツール 直接テスト ===")
    
    tool = StepMathEngine()
    
    # x*sin(x)の部分積分テスト
    print("\n📊 x*sin(x)の部分積分:")
    result = await tool.execute(
        expression="x*sin(x)",
        operation="integrate_by_parts",
        var="x"
    )
    
    if result.success:
        print("✅ 成功:")
        print(result.result)
    else:
        print(f"❌ エラー: {result.error}")
    
    return result.success


async def test_s_expression_generation():
    """S式生成とツール統合テスト"""
    print("\n=== S式生成とツール統合テスト ===")
    
    # ツール登録
    register_builtin_tools()
    
    cli = SStyleAgentCLI()
    
    # テストケース
    test_input = "x * sin(x) の不定積分を詳細な手順付きで示して"
    
    print(f"入力: {test_input}")
    
    try:
        # S式生成
        s_expr = await cli.generate_s_expression(test_input)
        print(f"生成されたS式: {s_expr}")
        
        # パース
        success, parsed, error = cli.parse_s_expression_safe(s_expr)
        if success:
            print(f"パース結果: {parsed}")
            
            # 実行
            result = await cli.execute_s_expression(s_expr, test_input)
            print(f"実行結果: {result}")
            return True
        else:
            print(f"パースエラー: {error}")
            return False
            
    except Exception as e:
        print(f"エラー: {e}")
        return False


async def main():
    """メインテスト"""
    print("🧪 段階的数学解法システム テスト")
    print("=" * 50)
    
    # 直接ツールテスト
    tool_test = await test_step_math_tool()
    
    # S式統合テスト  
    integration_test = await test_s_expression_generation()
    
    print("\n" + "=" * 50)
    print("📊 テスト結果:")
    print(f"  🔧 ツール直接テスト: {'✅ 成功' if tool_test else '❌ 失敗'}")
    print(f"  🔗 S式統合テスト: {'✅ 成功' if integration_test else '❌ 失敗'}")
    
    if tool_test and integration_test:
        print("\n🎉 全テスト成功！段階的数学解法システムが動作しています")
        return True
    else:
        print("\n⚠️ 一部テストが失敗しました")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    if not result:
        sys.exit(1)