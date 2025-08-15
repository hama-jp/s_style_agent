"""
組み込みツール実装

基本的な機能を提供する組み込みツール群
"""

import asyncio
import requests
from typing import Any, Dict
from langsmith import traceable

from .base import BaseTool, ToolSchema, ToolParameter, ToolResult
from .security_sympy import safe_sympy_calculator


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
        mode = kwargs.get("mode", "numeric")  # numeric, symbolic, simplify
        try:
            # SymPyベースの安全な計算実行
            result = safe_sympy_calculator.calculate(expression, mode=mode)
            return ToolResult(
                success=True,
                result=result,
                metadata={"tool": "calc", "expression": expression, "mode": mode}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"計算エラー: {str(e)}",
                metadata={"tool": "calc", "expression": expression, "mode": mode}
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


class MathTool(BaseTool):
    """高度な数学処理ツール（微分・積分・因数分解など）"""
    
    def __init__(self):
        super().__init__("math", "高度な数学処理（微分・積分・因数分解など）")
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="数学式",
                    required=True
                ),
                ToolParameter(
                    name="operation",
                    type="string", 
                    description="操作 (diff, integrate, solve, expand, factor)",
                    required=True
                ),
                ToolParameter(
                    name="var",
                    type="string",
                    description="変数名（デフォルト: x）",
                    required=False
                )
            ]
        )
    
    @traceable(name="math_tool_execute")
    async def execute(self, **kwargs) -> ToolResult:
        expression = kwargs.get("expression", "")
        operation = kwargs.get("operation", "")
        var = kwargs.get("var", "x")
        
        try:
            result = safe_sympy_calculator.advanced_calculate(
                expression, operation, var=var
            )
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "tool": "math", 
                    "expression": expression, 
                    "operation": operation,
                    "var": var
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"数学処理エラー: {str(e)}",
                metadata={
                    "tool": "math", 
                    "expression": expression, 
                    "operation": operation,
                    "var": var
                }
            )


def register_builtin_tools():
    """組み込みツールをレジストリに登録"""
    from .base import global_registry
    
    tools = [
        NotifyTool(),
        CalcTool(),
        SearchTool(),
        DbQueryTool(),
        MathTool()
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