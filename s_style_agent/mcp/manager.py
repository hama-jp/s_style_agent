"""
MCP 統合管理クラス

MCPサーバー管理、ツール登録、S式評価器統合の全体統制
"""

from typing import Dict, List, Any, Optional
from langsmith import traceable

from .config import mcp_config_loader
from .server_manager import mcp_server_manager
from .tool_registry import mcp_tool_registry
from .robust_client import robust_mcp_client


class MCPManager:
    """MCP システム全体管理"""
    
    def __init__(self):
        self.initialized = False
        self.servers_started = False
        self.tools_registered = False
    
    @traceable(name="initialize_mcp_system")
    async def initialize(self, config_path: str = "mcp.json") -> bool:
        """MCP システム全体を初期化"""
        print("[MCP] システムを初期化中...")
        
        try:
            # 設定を読み込み
            from pathlib import Path
            
            mcp_config_loader.config_path = Path(config_path)
            servers = mcp_config_loader.load_config()
            
            if not servers:
                print("[MCP] 設定されたサーバーがありません")
                return True
            
            # 自動起動サーバーを堅牢なクライアントで起動
            autostart_servers = mcp_config_loader.get_autostart_servers()
            success_count = 0
            
            for server_config in autostart_servers:
                try:
                    success = await robust_mcp_client.start_server(
                        server_id=server_config.id,
                        command=server_config.command,
                        args=server_config.args,
                        env=server_config.env
                    )
                    if success:
                        success_count += 1
                        print(f"[MCP] サーバー '{server_config.id}' を堅牢クライアントで起動しました")
                except Exception as e:
                    print(f"[MCP] サーバー '{server_config.id}' の起動でエラー: {e}")
            
            if success_count > 0:
                self.initialized = True
                self.servers_started = True
                self.tools_registered = True
                print(f"[MCP] {success_count}/{len(autostart_servers)} 個のサーバーが起動しました")
                print("[MCP] システム初期化完了")
                return True
            else:
                print("[MCP] サーバーが起動していません")
                return False
            
        except Exception as e:
            print(f"[MCP] システム初期化でエラー: {e}")
            return False
    
    async def shutdown(self) -> None:
        """MCP システムを終了"""
        print("[MCP] システムを終了中...")
        
        try:
            # 全サーバーを停止
            await robust_mcp_client.shutdown_all()
            
            self.initialized = False
            self.servers_started = False
            self.tools_registered = False
            
            print("[MCP] システム終了完了")
            
        except Exception as e:
            print(f"[MCP] システム終了でエラー: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """MCP システムの全体ステータス"""
        tools = robust_mcp_client.list_tools()
        return {
            "initialized": self.initialized,
            "servers_started": self.servers_started,
            "tools_registered": self.tools_registered,
            "active_servers": list(robust_mcp_client.servers.keys()),
            "tool_statistics": {
                "total_tools": len(tools),
                "servers": {
                    server_id: len([t for t in tools if robust_mcp_client.get_tool_info(t) and robust_mcp_client.get_tool_info(t).server_id == server_id])
                    for server_id in robust_mcp_client.servers.keys()
                }
            }
        }
    
    def list_available_tools(self) -> List[str]:
        """利用可能なMCPツール一覧"""
        return robust_mcp_client.list_tools()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """ツール詳細情報"""
        tool_info = robust_mcp_client.get_tool_info(tool_name)
        if not tool_info:
            return None
        
        return {
            "name": tool_info.name,
            "s_expression_name": tool_name,
            "description": tool_info.description,
            "server_id": tool_info.server_id,
            "input_schema": tool_info.input_schema
        }
    
    async def health_check(self) -> Dict[str, bool]:
        """全サーバーのヘルスチェック"""
        health_status = {}
        
        for server_id in robust_mcp_client.servers.keys():
            health_status[server_id] = robust_mcp_client.is_server_running(server_id)
        
        return health_status
    
    async def restart_server(self, server_id: str) -> bool:
        """特定サーバーを再起動"""
        print(f"[MCP] サーバー '{server_id}' を再起動中...")
        
        try:
            # サーバーを停止
            await robust_mcp_client.stop_server(server_id)
            
            # サーバー設定を取得
            config = mcp_config_loader.get_server_config(server_id)
            if not config:
                print(f"[MCP] サーバー '{server_id}' の設定が見つかりません")
                return False
            
            # サーバーを再起動
            success = await robust_mcp_client.start_server(
                server_id=server_id,
                command=config.command,
                args=config.args,
                env=config.env
            )
            
            if success:
                print(f"[MCP] サーバー '{server_id}' の再起動完了")
                return True
            else:
                print(f"[MCP] サーバー '{server_id}' の再起動に失敗")
                return False
            
        except Exception as e:
            print(f"[MCP] サーバー '{server_id}' の再起動でエラー: {e}")
            return False


# グローバルMCP管理インスタンス
mcp_manager = MCPManager()