#!/usr/bin/env python3
"""
単一検索テスト（レート制限注意）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.manager import mcp_manager
from s_style_agent.core.evaluator import evaluate_s_expression


async def test_single_search():
    """単一検索テスト"""
    print("=== 単一検索テスト（レート制限考慮） ===")
    
    try:
        print("\n1. MCPシステム初期化...")
        success = await mcp_manager.initialize()
        
        if not success:
            print("   ❌ MCP初期化に失敗しました")
            return
        
        print("   ✅ MCP初期化成功")
        tools = mcp_manager.list_available_tools()
        print(f"   利用可能ツール: {tools}")
        
        if 'brave_web_search' in tools:
            print("\n2. 実際の検索実行...")
            
            s_expr = '(search "高松市役所 座標")'
            print(f"   実行S式: {s_expr}")
            print("   検索実行中（レート制限: 1 request/second）...")
            
            try:
                result = evaluate_s_expression(s_expr, "単一検索テスト")
                print(f"\n   ✅ 検索結果:")
                print(f"   {result}")
                
            except Exception as e:
                print(f"   ❌ 検索実行エラー: {e}")
                import traceback
                traceback.print_exc()
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
    asyncio.run(test_single_search())