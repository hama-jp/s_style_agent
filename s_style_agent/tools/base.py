"""
ツールベースクラス - MCP対応設計

将来的なMCP統合を念頭に置いたツールアーキテクチャ
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from langsmith import traceable
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """ツールパラメータの定義"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolSchema(BaseModel):
    """ツールスキーマ - MCP準拠"""
    name: str
    description: str
    parameters: List[ToolParameter]


class ToolResult(BaseModel):
    """ツール実行結果"""
    success: bool
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """ベースツールクラス - MCP互換設計"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """ツールスキーマを返す"""
        pass
    
    @traceable
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """ツールを実行"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """パラメータの妥当性をチェック"""
        schema = self.schema
        for param in schema.parameters:
            if param.required and param.name not in parameters:
                return False
        return True


class ToolRegistry:
    """ツールレジストリ - MCP統合時の管理クラス"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """ツールを登録"""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """ツールを取得"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """登録済みツール一覧"""
        return list(self._tools.keys())
    
    def get_schemas(self) -> List[ToolSchema]:
        """全ツールのスキーマを取得"""
        return [tool.schema for tool in self._tools.values()]
    
    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """ツールを実行"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                result=None,
                error=f"Tool '{name}' not found"
            )
        
        if not tool.validate_parameters(kwargs):
            return ToolResult(
                success=False,
                result=None,
                error=f"Invalid parameters for tool '{name}'"
            )
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=str(e)
            )


# グローバルツールレジストリ
global_registry = ToolRegistry()