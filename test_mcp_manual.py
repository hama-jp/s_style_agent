#!/usr/bin/env python3
"""
MCP統合の手動テスト
"""
import asyncio
import sys
import os

# プロジェクトパスを追加
sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.manager import mcp_manager


async def test_mcp_integration():
    """MCP統合テスト"""
    print("=== MCP統合テスト開始 ===")
    
    try:
        # 1. MCPシステム初期化
        print("\n1. MCPシステム初期化中...")
        success = await mcp_manager.initialize()
        print(f"   初期化結果: {success}")
        
        if not success:
            print("   ❌ MCP初期化に失敗しました")
            return
        
        # 2. システム状態確認
        print("\n2. システム状態確認...")
        status = mcp_manager.get_system_status()
        print(f"   初期化済み: {status['initialized']}")
        print(f"   サーバー起動済み: {status['servers_started']}")
        print(f"   ツール登録済み: {status['tools_registered']}")
        print(f"   アクティブサーバー: {status['active_servers']}")
        
        # 3. 利用可能ツール確認
        print("\n3. 利用可能ツール確認...")
        tools = mcp_manager.list_available_tools()
        print(f"   登録ツール数: {len(tools)}")
        for tool in tools:
            print(f"   - {tool}")
        
        # 4. ヘルスチェック
        print("\n4. ヘルスチェック実行...")
        health = await mcp_manager.health_check()
        print(f"   ヘルス状態: {health}")
        
        # 5. ツール実行テスト（可能であれば）
        if tools:
            print("\n5. ツール実行テスト...")
            # brave_searchツールがあれば簡単なテストを実行
            if any('brave' in tool.lower() or 'search' in tool.lower() for tool in tools):
                print("   brave-search ツールでテスト実行...")
                try:
                    # 簡単な検索テストを実行
                    search_tools = [tool for tool in tools if 'search' in tool.lower()]
                    if search_tools:
                        tool_name = search_tools[0]
                        print(f"   ツール '{tool_name}' のテスト実行中...")
                        
                        # ツール情報を取得
                        tool_info = mcp_manager.get_tool_info(tool_name)
                        if tool_info:
                            print(f"   ツール情報: {tool_info['description']}")
                            
                            # 実際の検索実行は制限があるのでスキップ
                            print("   実際の検索実行はスキップ（レート制限のため）")
                        
                except Exception as e:
                    print(f"   ツールテストでエラー: {e}")
            else:
                print("   検索ツールが見つかりませんでした")
        
        print("\n✅ MCP統合テスト完了")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n6. クリーンアップ...")
        await mcp_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(test_mcp_integration())