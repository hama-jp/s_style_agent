#!/usr/bin/env python3
"""
実際の検索テスト（レート制限注意）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.manager import mcp_manager
from s_style_agent.core.evaluator import evaluate_s_expression


async def test_actual_search():
    """実際の検索テスト（1回のみ、レート制限考慮）"""
    print("=== 実際の検索テスト（レート制限注意） ===")
    
    try:
        print("\n1. MCPシステム初期化...")
        success = await mcp_manager.initialize()
        print(f"   初期化結果: {success}")
        
        if not success:
            print("   ❌ MCP初期化に失敗しました")
            return
        
        # システム状態確認
        status = mcp_manager.get_system_status()
        print(f"   アクティブサーバー: {status['active_servers']}")
        tools = mcp_manager.list_available_tools()
        print(f"   利用可能ツール: {tools}")
        
        if 'brave_web_search' in tools:
            print("\n2. 実際の検索実行（1回のみ）...")
            
            # ユーザーに確認
            confirm = input("   実際にBrave Search APIを使用しますか？ (y/n): ").strip().lower()
            
            if confirm == 'y':
                s_expr = '(search "高松市役所 座標")'
                print(f"   実行S式: {s_expr}")
                print("   検索実行中...")
                
                try:
                    result = evaluate_s_expression(s_expr, "実際の検索テスト")
                    print(f"   検索結果:")
                    print(f"   {result}")
                    print("   ✅ 実際の検索が正常に完了しました")
                    
                except Exception as e:
                    print(f"   ❌ 検索実行エラー: {e}")
            else:
                print("   検索をスキップしました")
        else:
            print("   ❌ brave_web_search ツールが利用できません")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n3. クリーンアップ...")
        if mcp_manager.initialized:
            await mcp_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(test_actual_search())