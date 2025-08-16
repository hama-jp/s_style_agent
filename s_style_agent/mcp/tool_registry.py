"""
MCP ツール動的登録システム

MCPサーバーから取得したツールを既存のツールレジストリに動的登録
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from langsmith import traceable
from ..tools.base import BaseTool, ToolResult, ToolParameter, ToolSchema, global_registry
from .server_manager import mcp_server_manager


@dataclass
class MCPToolInfo:
    """MCP ツール情報"""
    name: str
    description: str
    server_id: str
    input_schema: Dict[str, Any]
    
    def to_s_expression_name(self) -> str:
        """S式での操作名を生成"""
        # サーバーIDをプレフィックスとして使用
        # brave-search の brave_web_search → brave-web-search
        return f"{self.server_id}-{self.name.replace('_', '-')}"


class MCPTool(BaseTool):
    """MCP ツールラッパー"""
    
    # Brave Search API レート制限（1 request/second）
    _last_brave_call = 0
    
    def __init__(self, mcp_info: MCPToolInfo):
        self.mcp_info = mcp_info
        
        # ツールスキーマを構築
        parameters = []
        if mcp_info.input_schema:
            properties = mcp_info.input_schema.get("properties", {})
            required = mcp_info.input_schema.get("required", [])
            
            for param_name, param_def in properties.items():
                param_type = param_def.get("type", "string")
                param_desc = param_def.get("description", "")
                param_required = param_name in required
                
                parameters.append(ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    required=param_required
                ))
        
        self.schema = ToolSchema(
            name=mcp_info.to_s_expression_name(),
            description=f"[MCP:{mcp_info.server_id}] {mcp_info.description}",
            parameters=parameters
        )
    
    @traceable(name="mcp_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        """MCP ツールを実行"""
        try:
            # Brave Search APIのレート制限対応
            if self.mcp_info.server_id == "brave-search":
                current_time = time.time()
                elapsed = current_time - MCPTool._last_brave_call
                
                if elapsed < 1.0:  # 1秒未満の場合は待機
                    wait_time = 1.0 - elapsed
                    print(f"[MCP] Brave Search レート制限: {wait_time:.2f}秒待機中...")
                    await asyncio.sleep(wait_time)
                
                MCPTool._last_brave_call = time.time()
            
            # MCPサーバーのツールを呼び出し
            result = await mcp_server_manager.call_tool(
                server_id=self.mcp_info.server_id,
                tool_name=self.mcp_info.name,
                arguments=kwargs
            )
            
            if result["success"]:
                return ToolResult(
                    success=True,
                    result=result["result"]
                )
            else:
                return ToolResult(
                    success=False,
                    error=result["error"]
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"MCP ツール実行エラー: {str(e)}"
            )


class MCPToolRegistry:
    """MCP ツール動的登録管理"""
    
    def __init__(self):
        self.mcp_tools: Dict[str, MCPToolInfo] = {}
        self.registered_tools: Dict[str, MCPTool] = {}
    
    @traceable(name="discover_mcp_tools") 
    async def discover_and_register_tools(self) -> int:
        """全MCPサーバーからツールを発見・登録"""
        print("[MCP] ツールを発見・登録中...")
        
        total_registered = 0
        servers = mcp_server_manager.list_servers()
        
        for server_id in servers:
            try:
                tools = await mcp_server_manager.get_server_tools(server_id)
                registered_count = await self._register_server_tools(server_id, tools)
                total_registered += registered_count
                
                print(f"[MCP] サーバー '{server_id}': {registered_count}個のツールを登録")
                
            except Exception as e:
                print(f"[MCP] サーバー '{server_id}' のツール登録でエラー: {e}")
        
        print(f"[MCP] 合計 {total_registered} 個のツールを登録しました")
        return total_registered
    
    async def _register_server_tools(self, server_id: str, tools: List[Dict[str, Any]]) -> int:
        """特定サーバーのツールを登録"""
        registered_count = 0
        
        for tool_def in tools:
            try:
                mcp_info = MCPToolInfo(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    server_id=server_id,
                    input_schema=tool_def["input_schema"]
                )
                
                # MCPツールラッパーを作成
                mcp_tool = MCPTool(mcp_info)
                
                # グローバルツールレジストリに登録
                global_registry.register_tool(mcp_tool)
                
                # 内部管理にも追加
                s_expr_name = mcp_info.to_s_expression_name()
                self.mcp_tools[s_expr_name] = mcp_info
                self.registered_tools[s_expr_name] = mcp_tool
                
                print(f"[MCP]   ツール登録: {s_expr_name} ({mcp_info.name})")
                registered_count += 1
                
            except Exception as e:
                print(f"[MCP] ツール '{tool_def.get('name', 'unknown')}' の登録でエラー: {e}")
        
        return registered_count
    
    def get_mcp_tool_info(self, s_expr_name: str) -> Optional[MCPToolInfo]:
        """S式名からMCPツール情報を取得"""
        return self.mcp_tools.get(s_expr_name)
    
    def list_mcp_tools(self) -> List[str]:
        """登録されているMCPツールのS式名一覧を取得"""
        return list(self.mcp_tools.keys())
    
    def unregister_server_tools(self, server_id: str) -> int:
        """特定サーバーのツールを登録解除"""
        unregistered_count = 0
        
        # サーバーのツールを特定
        tools_to_remove = [
            name for name, info in self.mcp_tools.items() 
            if info.server_id == server_id
        ]
        
        for tool_name in tools_to_remove:
            try:
                # グローバルレジストリから削除
                global_registry.unregister_tool(tool_name)
                
                # 内部管理からも削除
                del self.mcp_tools[tool_name]
                del self.registered_tools[tool_name]
                
                unregistered_count += 1
                
            except Exception as e:
                print(f"[MCP] ツール '{tool_name}' の登録解除でエラー: {e}")
        
        print(f"[MCP] サーバー '{server_id}': {unregistered_count}個のツールを登録解除しました")
        return unregistered_count
    
    def get_statistics(self) -> Dict[str, Any]:
        """MCP ツール統計情報を取得"""
        server_counts = {}
        for info in self.mcp_tools.values():
            server_counts[info.server_id] = server_counts.get(info.server_id, 0) + 1
        
        return {
            "total_tools": len(self.mcp_tools),
            "servers": server_counts,
            "tool_names": list(self.mcp_tools.keys())
        }


# グローバルMCPツールレジストリ
mcp_tool_registry = MCPToolRegistry()