#!/usr/bin/env python3
"""
MCP自動初期化機能のテスト
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.cli.main import SStyleAgentCLI


async def test_auto_init():
    """MCP自動初期化テスト"""
    print("=== MCP自動初期化テスト ===")
    
    try:
        # CLIインスタンスを作成（この時点ではMCP未初期化）
        cli = SStyleAgentCLI()
        print(f"CLI作成時のMCP状態: {cli.mcp_initialized}")
        
        # run()メソッドの初期化部分のみテスト
        print("\nMCP自動初期化を実行...")
        
        if not cli.mcp_initialized:
            from s_style_agent.mcp.manager import mcp_manager
            
            try:
                success = await mcp_manager.initialize()
                if success:
                    cli.mcp_initialized = True
                    tools = mcp_manager.list_available_tools()
                    print(f"✅ MCPシステム初期化完了 - {len(tools)}個のツールが利用可能")
                    if tools:
                        print(f"   利用可能なMCPツール: {', '.join(tools)}")
                        
                        # 簡単な検索テスト
                        print("\n動作確認: 簡単な検索テスト...")
                        s_expr = '(search "テスト検索")'
                        result = await cli.execute_s_expression(s_expr, "自動初期化テスト")
                        print(f"検索テスト結果: {result}")
                        
                else:
                    print("⚠️  MCPシステムの初期化に失敗しました（通常機能は利用可能）")
            except Exception as e:
                print(f"⚠️  MCP初期化エラー: {e} （通常機能は利用可能）")
        
        print(f"\n最終MCP状態: {cli.mcp_initialized}")
        print("✅ MCP自動初期化テスト完了")
        
        # クリーンアップ
        if cli.mcp_initialized:
            print("MCPシステムを終了中...")
            await mcp_manager.shutdown()
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_auto_init())