"""
MCP サーバープロセス管理

MCPサーバーのライフサイクル管理（起動・停止・監視・再起動）
"""

import asyncio
import json
import signal
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langsmith import traceable
from .config import MCPServerConfig, mcp_config_loader


@dataclass
class MCPServerStatus:
    """MCP サーバーステータス"""
    server_id: str
    status: str  # "starting", "running", "stopped", "error", "restarting"
    process_id: Optional[int] = None
    start_time: Optional[float] = None
    last_error: Optional[str] = None
    restart_count: int = 0


class MCPServerManager:
    """MCP サーバー管理クラス"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self.status: Dict[str, MCPServerStatus] = {}
        self.shutdown_event = asyncio.Event()
        
    @traceable(name="initialize_mcp_servers")
    async def initialize(self, config_path: str = "mcp.json") -> bool:
        """MCP サーバーを初期化"""
        print("[MCP] サーバー管理システムを初期化中...")
        
        # 設定を読み込み
        mcp_config_loader.config_path = Path(config_path)
        self.servers = mcp_config_loader.load_config()
        
        if not self.servers:
            print("[MCP] 設定されたサーバーがありません")
            return True
        
        # 設定の妥当性をチェック
        if not mcp_config_loader.validate_config():
            print("[MCP] 設定に問題があります")
            return False
        
        # 自動起動サーバーを起動
        autostart_servers = mcp_config_loader.get_autostart_servers()
        success_count = 0
        
        for server_config in autostart_servers:
            try:
                success = await self.start_server(server_config)
                if success:
                    success_count += 1
            except Exception as e:
                print(f"[MCP] サーバー '{server_config.id}' の起動でエラー: {e}")
        
        print(f"[MCP] {success_count}/{len(autostart_servers)} 個のサーバーが起動しました")
        return success_count > 0
    
    @traceable(name="start_mcp_server")
    async def start_server(self, config: MCPServerConfig) -> bool:
        """MCP サーバーを起動"""
        server_id = config.id
        print(f"[MCP] サーバー '{server_id}' を起動中...")
        
        # ステータスを更新
        self.status[server_id] = MCPServerStatus(
            server_id=server_id,
            status="starting",
            start_time=time.time()
        )
        
        try:
            if config.transport == "stdio":
                return await self._start_stdio_server(config)
            else:
                print(f"[MCP] 未対応のトランスポート: {config.transport}")
                return False
                
        except Exception as e:
            print(f"[MCP] サーバー '{server_id}' の起動に失敗: {e}")
            self.status[server_id].status = "error"
            self.status[server_id].last_error = str(e)
            return False
    
    async def _start_stdio_server(self, config: MCPServerConfig) -> bool:
        """stdio トランスポートでサーバーを起動"""
        server_id = config.id
        
        try:
            # サーバープロセスを起動
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.get_full_env()
            )
            
            # 新しいタスクで非同期コンテキストマネージャーを実行
            task = asyncio.create_task(self._run_mcp_session(server_id, server_params))
            
            # セッション確立を待つ（最大5秒）
            for i in range(10):
                await asyncio.sleep(0.5)
                if server_id in self.sessions:
                    self.status[server_id].status = "running"
                    print(f"[MCP] サーバー '{server_id}' が正常に起動しました")
                    return True
            
            print(f"[MCP] サーバー '{server_id}' のセッション確立に失敗（タイムアウト）")
            return False
            
        except Exception as e:
            print(f"[MCP] stdio サーバー '{server_id}' の起動に失敗: {e}")
            self.status[server_id].status = "error"
            self.status[server_id].last_error = str(e)
            return False
    
    async def _run_mcp_session(self, server_id: str, server_params: StdioServerParameters):
        """MCPセッションを長時間実行"""
        try:
            print(f"[MCP] サーバー '{server_id}' のセッション開始...")
            print(f"[MCP] コマンド: {server_params.command} {' '.join(server_params.args)}")
            
            async with stdio_client(server_params) as (read_stream, write_stream):
                print(f"[MCP] サーバー '{server_id}' の通信ストリーム確立")
                
                # ClientSessionを作成
                session = ClientSession(read_stream, write_stream)
                print(f"[MCP] サーバー '{server_id}' のClientSession作成")
                
                # 初期化を試行（タイムアウト付き）
                print(f"[MCP] サーバー '{server_id}' の初期化開始...")
                try:
                    init_result = await asyncio.wait_for(session.initialize(), timeout=10.0)
                    print(f"[MCP] サーバー '{server_id}' の初期化結果: {init_result}")
                except asyncio.TimeoutError:
                    print(f"[MCP] サーバー '{server_id}' の初期化がタイムアウトしました")
                    raise
                
                print(f"[MCP] サーバー '{server_id}' の初期化完了")
                
                # セッションを保存
                self.sessions[server_id] = session
                print(f"[MCP] サーバー '{server_id}' のセッション保存完了")
                
                # セッションを維持（shutdown_eventがセットされるまで）
                while not self.shutdown_event.is_set():
                    await asyncio.sleep(1.0)
                
        except Exception as e:
            print(f"[MCP] サーバー '{server_id}' セッションエラー: {e}")
            import traceback
            traceback.print_exc()
            if server_id in self.sessions:
                del self.sessions[server_id]
    
    @traceable(name="stop_mcp_server")
    async def stop_server(self, server_id: str, timeout: float = 5.0) -> bool:
        """MCP サーバーを停止"""
        print(f"[MCP] サーバー '{server_id}' を停止中...")
        
        if server_id not in self.sessions:
            print(f"[MCP] サーバー '{server_id}' は実行されていません")
            return True
        
        try:
            # セッションを辞書から削除（セッションタスクが自動的に終了）
            if server_id in self.sessions:
                del self.sessions[server_id]
            
            # プロセス情報も削除
            if server_id in self.processes:
                del self.processes[server_id]
            
            # ステータスを更新
            if server_id in self.status:
                self.status[server_id].status = "stopped"
            
            print(f"[MCP] サーバー '{server_id}' を停止しました")
            return True
            
        except Exception as e:
            print(f"[MCP] サーバー '{server_id}' の停止でエラー: {e}")
            return False
    
    async def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """サーバーの利用可能ツール一覧を取得"""
        if server_id not in self.sessions:
            print(f"[MCP] サーバー '{server_id}' は実行されていません")
            return []
        
        try:
            session = self.sessions[server_id]
            result = await session.list_tools()
            
            tools = []
            for tool in result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema.model_dump() if tool.inputSchema else {}
                })
            
            return tools
            
        except Exception as e:
            print(f"[MCP] サーバー '{server_id}' のツール一覧取得でエラー: {e}")
            return []
    
    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ツールを呼び出し"""
        if server_id not in self.sessions:
            return {
                "success": False,
                "error": f"サーバー '{server_id}' は実行されていません"
            }
        
        try:
            session = self.sessions[server_id]
            result = await session.call_tool(tool_name, arguments)
            
            return {
                "success": True,
                "result": result.content if hasattr(result, 'content') else result,
                "tool_name": tool_name,
                "server_id": server_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"ツール '{tool_name}' の実行でエラー: {str(e)}",
                "tool_name": tool_name,
                "server_id": server_id
            }
    
    async def health_check(self, server_id: str) -> bool:
        """サーバーのヘルスチェック"""
        if server_id not in self.sessions:
            return False
        
        try:
            # ツール一覧取得でヘルスチェック
            await self.get_server_tools(server_id)
            return True
        except:
            return False
    
    def get_server_status(self, server_id: str) -> Optional[MCPServerStatus]:
        """サーバーステータスを取得"""
        return self.status.get(server_id)
    
    def list_servers(self) -> List[str]:
        """実行中のサーバー一覧を取得"""
        return list(self.sessions.keys())
    
    async def shutdown_all(self) -> None:
        """全サーバーを停止"""
        print("[MCP] 全サーバーを停止中...")
        
        for server_id in list(self.sessions.keys()):
            await self.stop_server(server_id)
        
        self.shutdown_event.set()
        print("[MCP] 全サーバーが停止しました")


# グローバルサーバー管理インスタンス
mcp_server_manager = MCPServerManager()