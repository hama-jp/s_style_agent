"""
統一ツール実行サービス

CLI/TUI両方で使用される共通のツール実行ロジック
CLIの実装を基にMCP統合を含む統一されたツール実行を提供
"""

from typing import Any, Dict, List, Optional, Union
import asyncio
from langsmith import traceable

from ..tools.base import global_registry
from ..mcp.manager import mcp_manager
from ..mcp.robust_client import robust_mcp_client


class ToolExecutionError(Exception):
    """ツール実行エラー"""
    pass


class ToolExecutor:
    """統一ツール実行サービス"""
    
    def __init__(self):
        self.mcp_initialized = False
        
        # トレースロガーを初期化
        from .trace_logger import get_global_logger
        self.trace_logger = get_global_logger()
    
    async def initialize_mcp(self) -> bool:
        """
        MCPシステムを初期化（CLIと同じ実装）
        
        Returns:
            初期化成功フラグ
        """
        try:
            success = await mcp_manager.initialize()
            if success:
                self.mcp_initialized = True
                tools = mcp_manager.list_available_tools()
                print(f"✅ MCPシステム初期化完了 - {len(tools)}個のツールが利用可能")
                if tools:
                    print(f"   利用可能なMCPツール: {', '.join(tools)}")
                return True
            else:
                print("⚠️  MCPシステムの初期化に失敗しました（通常機能は利用可能）")
                return False
        except Exception as e:
            print(f"⚠️  MCP初期化エラー: {e} （通常機能は利用可能）")
            return False
    
    async def shutdown_mcp(self) -> None:
        """MCPシステムを終了（CLIと同じ実装）"""
        if self.mcp_initialized:
            print("MCPシステムを終了中...")
            await mcp_manager.shutdown()
            self.mcp_initialized = False
    
    @traceable(name="unified_tool_execute")
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        統一ツール実行（CLI実装ベース + トレース対応）
        
        Args:
            tool_name: 実行するツール名
            **kwargs: ツールパラメータ
            
        Returns:
            ツール実行結果
            
        Raises:
            ToolExecutionError: ツール実行に失敗した場合
        """
        import time
        from .trace_logger import ExecutionMetadata, ProvenanceType
        
        start_time = time.time()
        
        # トレースログ開始
        entry_id = self.trace_logger.start_operation(
            operation=f"tool:{tool_name}",
            input_data={"tool": tool_name, "params": kwargs}
        )
        
        try:
            # 1. MCPツールを優先チェック（CLI実装と同じ順序）
            if self.mcp_initialized and tool_name in robust_mcp_client.list_tools():
                result = await self._execute_mcp_tool_with_trace(tool_name, kwargs, entry_id)
            
            # 2. 通常のツールレジストリからチェック
            elif global_registry.get_tool(tool_name):
                tool = global_registry.get_tool(tool_name)
                result = await self._execute_builtin_tool_with_trace(tool, kwargs, entry_id)
            
            # 3. ツールが見つからない場合
            else:
                raise ToolExecutionError(f"ツール '{tool_name}' が見つかりません")
            
            # 成功時のトレースログ完了
            duration_ms = (time.time() - start_time) * 1000
            metadata = ExecutionMetadata(
                tool_called=tool_name,
                context={"success": True, "duration_ms": duration_ms}
            )
            self.trace_logger.end_operation(entry_id, result, metadata)
            
            return result
            
        except Exception as e:
            # エラー時のトレースログ完了
            duration_ms = (time.time() - start_time) * 1000
            metadata = ExecutionMetadata(
                tool_called=tool_name,
                error=str(e),
                context={"success": False, "duration_ms": duration_ms}
            )
            self.trace_logger.end_operation(entry_id, f"Error: {e}", metadata)
            
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"ツール実行エラー: {e}")
    
    async def _execute_mcp_tool_with_trace(self, tool_name: str, kwargs: Dict[str, Any], entry_id: str) -> Any:
        """MCP経由でツールを実行（トレース対応）"""
        import time
        from .trace_logger import ExecutionMetadata, ProvenanceType
        
        mcp_start_time = time.time()
        
        try:
            # パラメータを適切に処理
            processed_kwargs = {}
            for key, value in kwargs.items():
                # 第一引数を "query" として扱う（CLI実装と同じ）
                if key == "arg_0" or (key == "query" and len(kwargs) == 1):
                    processed_kwargs["query"] = str(value)
                else:
                    processed_kwargs[key] = str(value)
            
            print(f"[TRACE-MCP] ツール '{tool_name}' をMCP経由で実行: {processed_kwargs}")
            
            # MCPツールを実行
            mcp_result = await robust_mcp_client.call_tool(tool_name, processed_kwargs)
            
            mcp_duration_ms = (time.time() - mcp_start_time) * 1000
            
            if mcp_result.get("success"):
                result = mcp_result.get("result")
                
                # MCPトレース情報を追加
                self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                    provenance=ProvenanceType.MCP,
                    tool_called=tool_name,
                    mcp_server="brave-search",  # TODO: 動的に取得
                    mcp_tool=tool_name,
                    mcp_params=processed_kwargs,
                    mcp_duration_ms=mcp_duration_ms,
                    mcp_success=True,
                    context={"mcp_result": mcp_result}
                ))
                
                print(f"[TRACE-MCP] 実行成功: {mcp_duration_ms:.1f}ms")
                return result
            else:
                error_msg = f"MCPツールエラー: {mcp_result.get('error')}"
                
                # MCPエラートレース情報を追加
                self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                    provenance=ProvenanceType.MCP,
                    tool_called=tool_name,
                    mcp_server="brave-search",
                    mcp_tool=tool_name,
                    mcp_params=processed_kwargs,
                    mcp_duration_ms=mcp_duration_ms,
                    mcp_success=False,
                    error=error_msg,
                    context={"mcp_result": mcp_result}
                ))
                
                print(f"[TRACE-MCP] 実行エラー: {error_msg}")
                raise ToolExecutionError(error_msg)
                
        except Exception as e:
            mcp_duration_ms = (time.time() - mcp_start_time) * 1000
            
            # MCP例外トレース情報を追加
            self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                provenance=ProvenanceType.MCP,
                tool_called=tool_name,
                mcp_server="brave-search",
                mcp_tool=tool_name,
                mcp_params=kwargs,
                mcp_duration_ms=mcp_duration_ms,
                mcp_success=False,
                error=str(e),
                context={"exception": str(e)}
            ))
            
            print(f"[TRACE-MCP] 実行例外: {e}")
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"MCP実行エラー: {e}")
    
    async def _execute_builtin_tool_with_trace(self, tool, kwargs: Dict[str, Any], entry_id: str) -> Any:
        """組み込みツールを実行（トレース対応）"""
        import time
        from .trace_logger import ExecutionMetadata, ProvenanceType
        
        builtin_start_time = time.time()
        
        try:
            # スキーマに基づいてパラメータをマッピング
            schema = tool.schema
            mapped_kwargs = {}
            
            # パラメータを適切にマッピング
            for i, param in enumerate(schema.parameters):
                if param.name in kwargs:
                    mapped_kwargs[param.name] = kwargs[param.name]
                elif f"arg_{i}" in kwargs:
                    mapped_kwargs[param.name] = kwargs[f"arg_{i}"]
                elif i == 0 and "query" in kwargs:
                    # 第一引数をqueryとして扱う
                    mapped_kwargs[param.name] = kwargs["query"]
            
            print(f"[TRACE-BUILTIN] ツール '{tool.name}' を実行: {mapped_kwargs}")
            
            # ツールを実行
            tool_result = await tool.execute(**mapped_kwargs)
            
            builtin_duration_ms = (time.time() - builtin_start_time) * 1000
            
            if tool_result.success:
                result = tool_result.result
                
                # Built-inトレース情報を追加
                self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                    provenance=ProvenanceType.TOOL,
                    tool_called=tool.name,
                    context={
                        "builtin_tool": True,
                        "schema": schema.description,
                        "mapped_params": mapped_kwargs,
                        "duration_ms": builtin_duration_ms
                    }
                ))
                
                print(f"[TRACE-BUILTIN] 実行成功: {builtin_duration_ms:.1f}ms")
                return result
            else:
                error_msg = f"ツールエラー: {tool_result.error}"
                
                # Built-inエラートレース情報を追加
                self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                    provenance=ProvenanceType.TOOL,
                    tool_called=tool.name,
                    error=error_msg,
                    context={
                        "builtin_tool": True,
                        "schema": schema.description,
                        "mapped_params": mapped_kwargs,
                        "duration_ms": builtin_duration_ms
                    }
                ))
                
                print(f"[TRACE-BUILTIN] 実行エラー: {error_msg}")
                raise ToolExecutionError(error_msg)
                
        except Exception as e:
            builtin_duration_ms = (time.time() - builtin_start_time) * 1000
            
            # Built-in例外トレース情報を追加
            self.trace_logger.update_metadata(entry_id, ExecutionMetadata(
                provenance=ProvenanceType.TOOL,
                tool_called=getattr(tool, 'name', 'unknown'),
                error=str(e),
                context={
                    "builtin_tool": True,
                    "exception": str(e),
                    "duration_ms": builtin_duration_ms
                }
            ))
            
            print(f"[TRACE-BUILTIN] 実行例外: {e}")
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"組み込みツール実行エラー: {e}")
    
    async def _execute_mcp_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        """MCP経由でツールを実行（CLI実装ベース）"""
        # 後方互換性のため、トレース無し版も保持
        return await self._execute_mcp_tool_with_trace(tool_name, kwargs, "legacy")
    
    async def _execute_builtin_tool(self, tool, kwargs: Dict[str, Any]) -> Any:
        """組み込みツールを実行"""
        # 後方互換性のため、トレース無し版も保持  
        return await self._execute_builtin_tool_with_trace(tool, kwargs, "legacy")
    
    async def _execute_builtin_tool(self, tool, kwargs: Dict[str, Any]) -> Any:
        """組み込みツールを実行"""
        try:
            # スキーマに基づいてパラメータをマッピング
            schema = tool.schema
            mapped_kwargs = {}
            
            # パラメータを適切にマッピング
            for i, param in enumerate(schema.parameters):
                if param.name in kwargs:
                    mapped_kwargs[param.name] = kwargs[param.name]
                elif f"arg_{i}" in kwargs:
                    mapped_kwargs[param.name] = kwargs[f"arg_{i}"]
                elif i == 0 and "query" in kwargs:
                    # 第一引数をqueryとして扱う
                    mapped_kwargs[param.name] = kwargs["query"]
            
            # ツールを実行
            tool_result = await tool.execute(**mapped_kwargs)
            
            if tool_result.success:
                return tool_result.result
            else:
                raise ToolExecutionError(f"ツールエラー: {tool_result.error}")
                
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise
            raise ToolExecutionError(f"組み込みツール実行エラー: {e}")
    
    def list_available_tools(self) -> List[str]:
        """利用可能なツール一覧を取得（CLI実装ベース）"""
        tools = []
        
        # MCPツール
        if self.mcp_initialized:
            mcp_tools = robust_mcp_client.list_tools()
            tools.extend(mcp_tools)
        
        # 組み込みツール
        builtin_schemas = global_registry.get_schemas()
        builtin_tools = [schema.name for schema in builtin_schemas]
        tools.extend(builtin_tools)
        
        return list(set(tools))  # 重複除去
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """ツール情報を取得"""
        # MCPツール情報
        if self.mcp_initialized and tool_name in robust_mcp_client.list_tools():
            return {
                "name": tool_name,
                "type": "mcp",
                "source": "MCP Server"
            }
        
        # 組み込みツール情報
        tool = global_registry.get_tool(tool_name)
        if tool:
            schema = tool.schema
            return {
                "name": schema.name,
                "type": "builtin", 
                "description": schema.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required
                    } for p in schema.parameters
                ]
            }
        
        return None


# グローバルインスタンス（シングルトン）
_global_tool_executor = None

def get_tool_executor() -> ToolExecutor:
    """グローバルツール実行サービスを取得"""
    global _global_tool_executor
    if _global_tool_executor is None:
        _global_tool_executor = ToolExecutor()
    return _global_tool_executor