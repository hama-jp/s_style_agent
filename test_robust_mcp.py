#!/usr/bin/env python3
"""
堅牢なMCPクライアントのテスト
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.robust_client import robust_mcp_client


async def test_robust_mcp():
    """堅牢なMCPクライアントのテスト"""
    print("=== 堅牢なMCPクライアントテスト開始 ===")
    
    try:
        # Brave Searchサーバーを起動
        print("\n1. Brave Searchサーバー起動...")
        success = await robust_mcp_client.start_server(
            server_id="brave-search",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={"BRAVE_API_KEY": "BSA08ZZ1dpMwC_ZWGkkYng3J-1GbZ1P"}
        )
        
        print(f"   起動結果: {success}")
        
        if not success:
            print("   ❌ サーバー起動に失敗")
            return
        
        # 利用可能ツール確認
        print("\n2. 利用可能ツール確認...")
        tools = robust_mcp_client.list_tools()
        print(f"   登録ツール数: {len(tools)}")
        for tool in tools:
            print(f"   - {tool}")
            
            # ツール詳細情報
            info = robust_mcp_client.get_tool_info(tool)
            if info:
                print(f"     説明: {info.description}")
                print(f"     サーバー: {info.server_id}")
        
        # サーバー状態確認
        print("\n3. サーバー状態確認...")
        is_running = robust_mcp_client.is_server_running("brave-search")
        print(f"   Brave Search実行状態: {is_running}")
        
        print("\n✅ 堅牢なMCPクライアントテスト完了")
        
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n4. クリーンアップ...")
        await robust_mcp_client.shutdown_all()


if __name__ == "__main__":
    asyncio.run(test_robust_mcp())