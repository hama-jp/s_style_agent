"""
堅牢なMCPクライアント実装

MCPサーバーとの接続問題を解決するための代替アプローチ
"""

import asyncio
import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from langsmith import traceable


@dataclass
class MCPToolInfo:
    """MCPツール情報"""
    name: str
    description: str
    server_id: str
    input_schema: Dict[str, Any]


class RobustMCPClient:
    """堅牢なMCPクライアント"""
    
    def __init__(self):
        self.servers: Dict[str, subprocess.Popen] = {}
        self.tools: Dict[str, MCPToolInfo] = {}
        self.server_status: Dict[str, str] = {}
    
    async def start_server(self, server_id: str, command: str, args: List[str], 
                          env: Dict[str, str]) -> bool:
        """MCPサーバーを起動"""
        try:
            print(f"[RobustMCP] サーバー '{server_id}' を起動中...")
            
            # 環境変数を設定
            full_env = dict(os.environ)
            full_env.update(env)
            
            # プロセスを起動
            process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                text=True
            )
            
            self.servers[server_id] = process
            self.server_status[server_id] = "starting"
            
            # 起動確認のため少し待機
            await asyncio.sleep(2.0)
            
            # プロセスがまだ生きているかチェック
            if process.poll() is None:
                self.server_status[server_id] = "running"
                print(f"[RobustMCP] サーバー '{server_id}' が正常に起動しました")
                
                # 基本的なヘルスチェック（ツール一覧取得）
                await self._discover_tools(server_id)
                return True
            else:
                # プロセスが終了している場合
                stderr_output = process.stderr.read() if process.stderr else ""
                print(f"[RobustMCP] サーバー '{server_id}' の起動に失敗: {stderr_output}")
                self.server_status[server_id] = "failed"
                return False
            
        except Exception as e:
            print(f"[RobustMCP] サーバー '{server_id}' の起動でエラー: {e}")
            self.server_status[server_id] = "error"
            return False
    
    async def _discover_tools(self, server_id: str) -> None:
        """サーバーのツール一覧を取得"""
        try:
            # JSONRPCでツール一覧リクエスト
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            result = await self._send_request(server_id, request)
            if result and "result" in result:
                tools_data = result["result"].get("tools", [])
                
                for tool_data in tools_data:
                    tool_name = tool_data.get("name", "")
                    if tool_name:
                        tool_info = MCPToolInfo(
                            name=tool_name,
                            description=tool_data.get("description", ""),
                            server_id=server_id,
                            input_schema=tool_data.get("inputSchema", {})
                        )
                        self.tools[tool_name] = tool_info
                        print(f"[RobustMCP] ツール '{tool_name}' を登録しました")
        
        except Exception as e:
            print(f"[RobustMCP] ツール探索でエラー: {e}")
    
    async def _send_request(self, server_id: str, request: Dict[str, Any], 
                           timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """サーバーにJSONRPCリクエストを送信"""
        if server_id not in self.servers:
            return None
        
        process = self.servers[server_id]
        
        try:
            # リクエストをJSON形式で送信
            request_json = json.dumps(request) + "\n"
            
            # 非同期でプロセスと通信
            loop = asyncio.get_event_loop()
            
            # stdin に書き込み
            await loop.run_in_executor(None, process.stdin.write, request_json)
            await loop.run_in_executor(None, process.stdin.flush)
            
            # stdout から応答を読み取り（タイムアウト付き）
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, process.stdout.readline),
                timeout=timeout
            )
            
            if response_line:
                return json.loads(response_line.strip())
            
        except asyncio.TimeoutError:
            print(f"[RobustMCP] サーバー '{server_id}' への要求がタイムアウトしました")
        except Exception as e:
            print(f"[RobustMCP] サーバー '{server_id}' との通信エラー: {e}")
        
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """ツールを呼び出し"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"ツール '{tool_name}' が見つかりません"
            }
        
        tool_info = self.tools[tool_name]
        server_id = tool_info.server_id
        
        try:
            # JSONRPCでツール実行リクエスト
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            result = await self._send_request(server_id, request, timeout=30.0)
            
            if result and "result" in result:
                return {
                    "success": True,
                    "result": result["result"],
                    "tool_name": tool_name,
                    "server_id": server_id
                }
            elif result and "error" in result:
                return {
                    "success": False,
                    "error": f"サーバーエラー: {result['error']}",
                    "tool_name": tool_name,
                    "server_id": server_id
                }
            else:
                return {
                    "success": False,
                    "error": "応答なし",
                    "tool_name": tool_name,
                    "server_id": server_id
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"ツール実行エラー: {str(e)}",
                "tool_name": tool_name,
                "server_id": server_id
            }
    
    def list_tools(self) -> List[str]:
        """利用可能ツール一覧を取得"""
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        """ツール情報を取得"""
        return self.tools.get(tool_name)
    
    def is_server_running(self, server_id: str) -> bool:
        """サーバーが実行中かチェック"""
        if server_id not in self.servers:
            return False
        
        process = self.servers[server_id]
        return process.poll() is None
    
    async def stop_server(self, server_id: str) -> bool:
        """サーバーを停止"""
        if server_id not in self.servers:
            return True
        
        try:
            process = self.servers[server_id]
            process.terminate()
            
            # 終了を待機（タイムアウト付き）
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process(process)),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # 強制終了
                process.kill()
                await asyncio.sleep(1.0)
            
            del self.servers[server_id]
            self.server_status[server_id] = "stopped"
            
            # 関連ツールも削除
            tools_to_remove = [name for name, info in self.tools.items() 
                             if info.server_id == server_id]
            for tool_name in tools_to_remove:
                del self.tools[tool_name]
            
            print(f"[RobustMCP] サーバー '{server_id}' を停止しました")
            return True
            
        except Exception as e:
            print(f"[RobustMCP] サーバー '{server_id}' の停止でエラー: {e}")
            return False
    
    async def _wait_for_process(self, process):
        """プロセスの終了を非同期で待機"""
        while process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def shutdown_all(self) -> None:
        """全サーバーを停止"""
        print("[RobustMCP] 全サーバーを停止中...")
        
        for server_id in list(self.servers.keys()):
            await self.stop_server(server_id)
        
        print("[RobustMCP] 全サーバーが停止しました")


# グローバルクライアントインスタンス
robust_mcp_client = RobustMCPClient()