#!/usr/bin/env python3
"""
MCP統合システムテスト

MCPサーバーの起動、ツール発見、S式統合をテスト
"""

import asyncio
import os
from s_style_agent.mcp.manager import mcp_manager
from s_style_agent.mcp.config import mcp_config_loader
from s_style_agent.tools.base import global_registry


async def test_mcp_config():
    """MCP設定読み込みテスト"""
    print("=== MCP設定読み込みテスト ===")
    
    # 設定を読み込み
    servers = mcp_config_loader.load_config()
    
    print(f"設定済みサーバー数: {len(servers)}")
    for server_id, config in servers.items():
        print(f"- {server_id}: {config.command} {' '.join(config.args)}")
        print(f"  環境変数: {list(config.env.keys())}")
        print(f"  自動起動: {config.autostart}")
    
    # 設定検証
    is_valid = mcp_config_loader.validate_config()
    print(f"設定妥当性: {'✅ 有効' if is_valid else '❌ 無効'}")
    
    return len(servers) > 0


async def test_mcp_system_initialization():
    """MCPシステム初期化テスト"""
    print("\n=== MCPシステム初期化テスト ===")
    
    try:
        # MCPシステムを初期化
        success = await mcp_manager.initialize()
        
        if success:
            print("✅ MCPシステム初期化成功")
            
            # システム状態を確認
            status = mcp_manager.get_system_status()
            print(f"初期化済み: {status['initialized']}")
            print(f"サーバー起動済み: {status['servers_started']}")
            print(f"ツール登録済み: {status['tools_registered']}")
            print(f"アクティブサーバー: {status['active_servers']}")
            
            # ツール統計
            stats = status['tool_statistics']
            print(f"登録ツール数: {stats['total_tools']}")
            if stats['servers']:
                print("サーバー別ツール数:")
                for server, count in stats['servers'].items():
                    print(f"  - {server}: {count}個")
            
            return True
        else:
            print("❌ MCPシステム初期化失敗")
            return False
            
    except Exception as e:
        print(f"❌ 初期化エラー: {e}")
        return False


async def test_mcp_tools():
    """MCPツールテスト"""
    print("\n=== MCPツールテスト ===")
    
    # 利用可能ツール一覧
    tools = mcp_manager.list_available_tools()
    print(f"利用可能MCPツール数: {len(tools)}")
    
    for tool_name in tools:
        info = mcp_manager.get_tool_info(tool_name)
        if info:
            print(f"\n📊 ツール: {tool_name}")
            print(f"   サーバー: {info['server_id']}")
            print(f"   説明: {info['description']}")
            
            if info['input_schema'].get('properties'):
                params = list(info['input_schema']['properties'].keys())
                print(f"   パラメータ: {', '.join(params)}")
    
    return len(tools) > 0


async def test_global_registry_integration():
    """グローバルツールレジストリ統合テスト"""
    print("\n=== グローバルレジストリ統合テスト ===")
    
    # 全ツールスキーマを取得
    all_schemas = global_registry.get_all_schemas()
    
    # MCPツールを特定
    mcp_tools = [
        schema for schema in all_schemas 
        if schema.description.startswith("[MCP:")
    ]
    
    print(f"グローバルレジストリ内総ツール数: {len(all_schemas)}")
    print(f"うちMCPツール数: {len(mcp_tools)}")
    
    if mcp_tools:
        print("\nMCPツール詳細:")
        for schema in mcp_tools:
            params = ", ".join([p.name for p in schema.parameters])
            print(f"- {schema.name}({params}): {schema.description}")
    
    return len(mcp_tools) > 0


async def test_health_check():
    """ヘルスチェックテスト"""
    print("\n=== ヘルスチェックテスト ===")
    
    health_status = await mcp_manager.health_check()
    
    print("サーバーヘルスチェック結果:")
    all_healthy = True
    for server_id, is_healthy in health_status.items():
        status_icon = "✅" if is_healthy else "❌"
        status_text = "正常" if is_healthy else "異常"
        print(f"{status_icon} {server_id}: {status_text}")
        if not is_healthy:
            all_healthy = False
    
    return all_healthy


async def main():
    """メインテスト実行"""
    print("🧪 MCP統合システムテスト開始")
    print("=" * 50)
    
    try:
        # テスト実行
        test_results = {}
        
        test_results["config"] = await test_mcp_config()
        test_results["initialization"] = await test_mcp_system_initialization()
        
        if test_results["initialization"]:
            test_results["tools"] = await test_mcp_tools()
            test_results["registry"] = await test_global_registry_integration()
            test_results["health"] = await test_health_check()
        else:
            print("⚠️ 初期化失敗のため、後続テストをスキップします")
            test_results["tools"] = False
            test_results["registry"] = False
            test_results["health"] = False
        
        # 結果サマリー
        print("\n" + "=" * 50)
        print("📋 テスト結果サマリー")
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            icon = "✅" if result else "❌"
            print(f"{icon} {test_name}: {'成功' if result else '失敗'}")
        
        print(f"\n合計: {passed}/{total} 個のテスト成功")
        
        if passed == total:
            print("🎉 全テスト成功！MCPシステムは正常に動作しています")
        else:
            print("⚠️ 一部テストが失敗しました")
        
        # クリーンアップ
        if test_results["initialization"]:
            print("\nMCPシステムを停止中...")
            await mcp_manager.shutdown()
            print("✅ MCPシステム停止完了")
        
    except Exception as e:
        print(f"❌ テスト実行中にエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())