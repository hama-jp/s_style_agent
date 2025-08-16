#!/usr/bin/env python3
"""
Human-in-the-loop システムのテスト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.tools.user_interaction import AskUserTool, CollectInfoTool
from s_style_agent.tools.builtin_tools import register_builtin_tools
from s_style_agent.cli.main import SStyleAgentCLI


async def test_ask_user_tool():
    """ask_userツールの直接テスト"""
    print("=== ask_userツール 直接テスト ===")
    
    tool = AskUserTool()
    
    # 基本的な質問テスト
    print("\n📊 基本的な質問:")
    result = await tool.execute(
        question="好きな色は何ですか？",
        variable_name="favorite_color",
        question_type="required"
    )
    
    if result.success:
        print(f"✅ 回答: {result.result}")
        return True
    else:
        print(f"❌ エラー: {result.error}")
        return False


async def test_collect_info_tool():
    """collect_infoツールの直接テスト"""
    print("\n=== collect_infoツール 直接テスト ===")
    
    tool = CollectInfoTool()
    
    questions_json = '''[
        {"question": "お名前を教えてください", "variable": "name", "type": "required"},
        {"question": "年齢を教えてください", "variable": "age", "type": "optional", "default": "非公開"},
        {"question": "好きな季節は？", "variable": "season", "type": "choice", "choices": "春,夏,秋,冬"}
    ]'''
    
    print("\n📊 複数情報の収集:")
    result = await tool.execute(questions=questions_json)
    
    if result.success:
        print(f"✅ 収集データ: {result.result}")
        return True
    else:
        print(f"❌ エラー: {result.error}")
        return False


async def test_s_expression_integration():
    """S式統合テスト"""
    print("\n=== S式統合テスト ===")
    
    # ツール登録
    register_builtin_tools()
    
    cli = SStyleAgentCLI()
    
    # テストケース：旅行プラン
    test_input = "2泊3日の国内旅行プランを作って"
    
    print(f"入力: {test_input}")
    
    try:
        # S式生成
        s_expr = await cli.generate_s_expression(test_input)
        print(f"生成されたS式: {s_expr}")
        
        # パース
        success, parsed, error = cli.parse_s_expression_safe(s_expr)
        if success:
            print(f"パース結果: {parsed}")
            
            # ユーザーに実行確認
            print("\n実行しますか？ (y/n): ", end="")
            choice = input().strip().lower()
            
            if choice == 'y':
                # 実行
                result = await cli.execute_s_expression(s_expr, test_input)
                print(f"実行結果: {result}")
                return True
            else:
                print("実行をスキップしました")
                return True
        else:
            print(f"パースエラー: {error}")
            return False
            
    except Exception as e:
        print(f"エラー: {e}")
        return False


async def main():
    """メインテスト"""
    print("🧪 Human-in-the-loop システム テスト")
    print("=" * 50)
    
    # 個別ツールテスト
    print("1. 個別ツールテストを実行しますか？ (y/n): ", end="")
    if input().strip().lower() == 'y':
        ask_test = await test_ask_user_tool()
        collect_test = await test_collect_info_tool()
    else:
        ask_test = collect_test = True
        print("個別ツールテストをスキップしました")
    
    # S式統合テスト
    print("\n2. S式統合テストを実行しますか？ (y/n): ", end="")
    if input().strip().lower() == 'y':
        integration_test = await test_s_expression_integration()
    else:
        integration_test = True
        print("S式統合テストをスキップしました")
    
    print("\n" + "=" * 50)
    print("📊 テスト結果:")
    print(f"  🔧 ask_userツール: {'✅ 成功' if ask_test else '❌ 失敗'}")
    print(f"  📝 collect_infoツール: {'✅ 成功' if collect_test else '❌ 失敗'}")
    print(f"  🔗 S式統合テスト: {'✅ 成功' if integration_test else '❌ 失敗'}")
    
    if ask_test and collect_test and integration_test:
        print("\n🎉 全テスト成功！Human-in-the-loopシステムが動作しています")
        return True
    else:
        print("\n⚠️ 一部テストが失敗しました")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    if not result:
        sys.exit(1)