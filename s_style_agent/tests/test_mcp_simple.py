#!/usr/bin/env python3
"""
MCP統合の簡単なテスト
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_simple_mcp():
    """シンプルなMCPテスト"""
    print("=== 簡単なMCPテスト開始 ===")
    
    try:
        # Brave Searchサーバーに直接接続
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-brave-search"],
            env={
                "BRAVE_API_KEY": "BSA08ZZ1dpMwC_ZWGkkYng3J-1GbZ1P"
            }
        )
        
        print(f"コマンド: {server_params.command} {' '.join(server_params.args)}")
        print("サーバー接続開始...")
        
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("ストリーム確立成功")
            
            session = ClientSession(read_stream, write_stream)
            print("ClientSession作成成功")
            
            print("初期化開始...")
            try:
                # 初期化にタイムアウトを設定
                init_result = await asyncio.wait_for(session.initialize(), timeout=30.0)
                print(f"初期化成功: {init_result}")
                
                # ツール一覧を取得
                print("ツール一覧取得中...")
                tools_result = await session.list_tools()
                print(f"利用可能ツール: {[tool.name for tool in tools_result.tools]}")
                
                print("✅ テスト成功！")
                
            except asyncio.TimeoutError:
                print("❌ 初期化タイムアウト")
            except Exception as e:
                print(f"❌ 初期化エラー: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_mcp())