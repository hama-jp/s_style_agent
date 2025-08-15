"""
組み込みツール実装

基本的な機能を提供する組み込みツール群
"""

import asyncio
import requests
from typing import Any, Dict
from langsmith import traceable

from .base import BaseTool, ToolSchema, ToolParameter, ToolResult


class NotifyTool(BaseTool):
    """通知ツール"""
    
    def __init__(self):
        super().__init__("notify", "ユーザーにメッセージを通知")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="通知するメッセージ",
                    required=True
                )
            ]
        )
    
    @traceable(name="notify_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        print(f"[NOTIFY] {message}")
        return ToolResult(
            success=True,
            result=message,
            metadata={"tool": "notify", "timestamp": asyncio.get_event_loop().time()}
        )


class CalcTool(BaseTool):
    """計算ツール"""
    
    def __init__(self):
        super().__init__("calc", "数式を計算")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="計算する数式",
                    required=True
                )
            ]
        )
    
    @traceable(name="calc_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        expression = kwargs.get("expression", "")
        try:
            # 安全な計算実行
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "divmod": divmod,
                "__builtins__": {}
            }
            result = eval(expression, allowed_names, {})
            return ToolResult(
                success=True,
                result=result,
                metadata={"tool": "calc", "expression": expression}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"計算エラー: {str(e)}",
                metadata={"tool": "calc", "expression": expression}
            )


class SearchTool(BaseTool):
    """検索ツール（ダミー実装）"""
    
    def __init__(self):
        super().__init__("search", "情報を検索")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="検索クエリ",
                    required=True
                )
            ]
        )
    
    @traceable(name="search_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        # ダミー実装 - 実際はウェブ検索APIを呼び出し
        await asyncio.sleep(0.1)  # 非同期処理のシミュレート
        
        result = f"'{query}' の検索結果:\n- 検索結果1\n- 検索結果2\n- 検索結果3"
        
        return ToolResult(
            success=True,
            result=result,
            metadata={"tool": "search", "query": query}
        )


class DbQueryTool(BaseTool):
    """データベースクエリツール（ダミー実装）"""
    
    def __init__(self):
        super().__init__("db-query", "データベースクエリを実行")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="SQLクエリ",
                    required=True
                )
            ]
        )
    
    @traceable(name="db_query_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        # ダミー実装 - 実際はデータベースに接続
        await asyncio.sleep(0.05)
        
        result = f"クエリ '{query}' の実行結果:\n[{{'id': 1, 'name': 'sample'}}, {{'id': 2, 'name': 'data'}}]"
        
        return ToolResult(
            success=True,
            result=result,
            metadata={"tool": "db-query", "query": query}
        )


def register_builtin_tools():
    """組み込みツールをレジストリに登録"""
    from .base import global_registry
    
    tools = [
        NotifyTool(),
        CalcTool(),
        SearchTool(),
        DbQueryTool()
    ]
    
    for tool in tools:
        global_registry.register(tool)
    
    return global_registry


if __name__ == "__main__":
    # テスト実行
    async def test_tools():
        registry = register_builtin_tools()
        
        # 通知ツールテスト
        result = await registry.execute_tool("notify", message="テストメッセージ")
        print(f"Notify result: {result}")
        
        # 計算ツールテスト
        result = await registry.execute_tool("calc", expression="2 + 3 * 4")
        print(f"Calc result: {result}")
        
        # 検索ツールテスト
        result = await registry.execute_tool("search", query="langchain")
        print(f"Search result: {result}")
    
    asyncio.run(test_tools())