"""
組み込みツール実装

基本的な機能を提供する組み込みツール群
"""

import asyncio
import requests
from typing import Any, Dict
from langsmith import traceable

from .base import BaseTool, ToolSchema, ToolParameter, ToolResult
from .math_engine import MathEngine, StepMathEngine
from .user_interaction import AskUserTool, CollectInfoTool, ConditionalAskTool, SuggestAndConfirmTool


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
            # 直接SymPyを使用した計算
            import sympy as sp
            expr = sp.sympify(expression)
            
            if mode == "numeric":
                result = sp.N(expr)
                # 可能であれば数値型に変換
                if result.is_number:
                    if result.is_integer:
                        return ToolResult(
                            success=True, 
                            result=int(result), 
                            metadata={"tool": "calc", "expression": expression, "mode": mode}
                        )
                    else:
                        return ToolResult(
                            success=True, 
                            result=float(result), 
                            metadata={"tool": "calc", "expression": expression, "mode": mode}
                        )
                return ToolResult(
                    success=True, 
                    result=str(result), 
                    metadata={"tool": "calc", "expression": expression, "mode": mode}
                )
            elif mode == "symbolic":
                return ToolResult(
                    success=True, 
                    result=str(expr), 
                    metadata={"tool": "calc", "expression": expression, "mode": mode}
                )
            elif mode == "simplify":
                result = sp.simplify(expr)
                return ToolResult(
                    success=True, 
                    result=str(result), 
                    metadata={"tool": "calc", "expression": expression, "mode": mode}
                )
            else:
                raise ValueError(f"不明なモード: {mode}")
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


def register_builtin_tools():
    """組み込みツールをレジストリに登録"""
    from .base import global_registry
    
    tools = [
        NotifyTool(),
        CalcTool(),
        SearchTool(),
        DbQueryTool(),
        MathEngine(),  # 記号数学処理エンジン
        StepMathEngine(),  # 段階的数学解法エンジン
        AskUserTool(),  # ユーザー質問ツール
        CollectInfoTool(),  # 情報収集ツール
        ConditionalAskTool(),  # 条件付き質問ツール
        SuggestAndConfirmTool()  # 提案確認ツール
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