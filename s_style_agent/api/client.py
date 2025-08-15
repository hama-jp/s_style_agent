"""
APIクライアントのサンプル実装
"""

import asyncio
import json
import websockets
from typing import Dict, Any
import requests
from .models import SExpressionRequest, ExecutionMode


class SStyleAgentClient:
    """S式エージェントAPIクライアント"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
    
    def get_status(self) -> Dict[str, Any]:
        """システムステータスを取得"""
        response = requests.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()
    
    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """S式をパース"""
        data = {"expression": expression}
        response = requests.post(f"{self.base_url}/parse", json=data)
        response.raise_for_status()
        return response.json()
    
    def execute_expression(self, expression: str, context: str = "", 
                         mode: ExecutionMode = ExecutionMode.ASYNC,
                         is_admin: bool = False) -> Dict[str, Any]:
        """S式を実行"""
        data = {
            "expression": expression,
            "context": context,
            "mode": mode.value,
            "is_admin": is_admin
        }
        response = requests.post(f"{self.base_url}/execute", json=data)
        response.raise_for_status()
        return response.json()
    
    def generate_expression(self, task: str, 
                          llm_base_url: str = None,
                          model_name: str = None) -> Dict[str, Any]:
        """自然言語からS式を生成"""
        data = {"task": task}
        if llm_base_url:
            data["llm_base_url"] = llm_base_url
        if model_name:
            data["model_name"] = model_name
            
        response = requests.post(f"{self.base_url}/generate", json=data)
        response.raise_for_status()
        return response.json()
    
    async def websocket_client(self, session_id: str = "test-session"):
        """WebSocketクライアントのサンプル"""
        uri = f"{self.ws_url}/ws/{session_id}"
        
        async with websockets.connect(uri) as websocket:
            print(f"WebSocket connected: {session_id}")
            
            # 接続確認メッセージを受信
            welcome = await websocket.recv()
            print(f"Received: {welcome}")
            
            # Pingテスト
            ping_msg = {
                "type": "ping",
                "data": {"message": "ping test"}
            }
            await websocket.send(json.dumps(ping_msg))
            pong = await websocket.recv()
            print(f"Ping response: {pong}")
            
            # S式実行テスト
            execute_msg = {
                "type": "execute",
                "data": {
                    "expression": "(calc \"2 + 3 * 4\")",
                    "context": "WebSocket test",
                    "mode": "async",
                    "is_admin": False
                }
            }
            await websocket.send(json.dumps(execute_msg))
            result = await websocket.recv()
            print(f"Execution result: {result}")


async def main():
    """クライアントテストのメイン関数"""
    client = SStyleAgentClient()
    
    print("=== REST API テスト ===")
    
    try:
        # ステータス確認
        status = client.get_status()
        print(f"Status: {status}")
        
        # パーステスト
        parse_result = client.parse_expression("(calc \"2 + 3\")")
        print(f"Parse result: {parse_result}")
        
        # 実行テスト
        exec_result = client.execute_expression("(notify \"Hello API!\")", "Test context")
        print(f"Execute result: {exec_result}")
        
        # 計算テスト
        calc_result = client.execute_expression("(calc \"sqrt(16) + sin(pi/2)\")")
        print(f"Calc result: {calc_result}")
        
    except Exception as e:
        print(f"REST API error: {e}")
    
    print("\n=== WebSocket テスト ===")
    
    try:
        await client.websocket_client("test-client-001")
    except Exception as e:
        print(f"WebSocket error: {e}")


if __name__ == "__main__":
    asyncio.run(main())