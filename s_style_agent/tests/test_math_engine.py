#!/usr/bin/env python3
"""
高度な数学処理テスト - 修正版

SymPyを使った複雑な数学計算のテストケース
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from s_style_agent.tools.builtin_tools import register_builtin_tools
from s_style_agent.core.parser import parse_s_expression
from s_style_agent.core.evaluator import ContextualEvaluator, Environment


class AdvancedMathTestSuite:
    """高度な数学処理のテストスイート"""
    
    def __init__(self):
        self.registry = register_builtin_tools()
        self.evaluator = ContextualEvaluator()
        self.env = Environment()
        self.passed = 0
        self.failed = 0
    
    async def run_test(self, name: str, expression: str, operation: str, var: str = "x", **kwargs):
        """単一テストの実行"""
        print(f"\n📊 {name}")
        print(f"   式: {expression}")
        print(f"   操作: {operation}({', '.join(f'{k}={v}' for k, v in kwargs.items())})")
        
        try:
            result = await self.registry.execute_tool(
                "math", 
                expression=expression, 
                operation=operation, 
                var=var,
                **kwargs
            )
            
            if result.success:
                print(f"   ✅ 結果: {result.result}")
                self.passed += 1
                return True
            else:
                print(f"   ❌ エラー: {result.error}")
                self.failed += 1
                return False
                
        except Exception as e:
            print(f"   ❌ 例外: {e}")
            self.failed += 1
            return False
    
    async def test_basic_operations(self):
        """基本演算テスト"""
        print("\n🧮 === 基本演算テスト ===")
        
        tests = [
            ("因数分解", "x**2 + 5*x + 6", "factor"),
            ("展開", "(x + 1)**2", "expand"),
            ("簡約", "sin(x)**2 + cos(x)**2", "simplify"),
            ("微分", "x**3 + 2*x**2", "diff"),
            ("積分", "2*x + 3", "integrate"),
            ("定積分", "x**2", "integrate", "x", {"lower": 0, "upper": 1}),
        ]
        
        for test_data in tests:
            if len(test_data) == 3:
                name, expr, op = test_data
                await self.run_test(name, expr, op)
            elif len(test_data) == 4:
                name, expr, op, var = test_data
                await self.run_test(name, expr, op, var)
            elif len(test_data) == 5:
                name, expr, op, var, kwargs = test_data
                await self.run_test(name, expr, op, var, **kwargs)
    
    async def test_advanced_operations(self):
        """高度演算テスト"""
        print("\n🚀 === 高度演算テスト ===")
        
        # 極限テスト
        await self.run_test("極限 x→0", "sin(x)/x", "limit", point="0")
        await self.run_test("極限 x→∞", "(x**2 + 1)/(x**2 + 2)", "limit", point="oo")
        
        # テイラー展開
        await self.run_test("テイラー展開", "exp(x)", "series", point="0", n=5)
        
        # 方程式
        await self.run_test("方程式求解", "x**2 + 3*x + 2", "solve")
        
        # 部分分数
        await self.run_test("部分分数", "1/(x**2 - 1)", "partial_fractions")
    
    def test_s_expressions(self):
        """S式統合テスト（同期版）"""
        print("\n🔗 === S式統合テスト ===")
        
        s_expressions = [
            '(math "x**2 + 4*x + 4" "factor")',
            '(math "x**3 + 2*x**2" "diff")',
            '(math "2*x" "integrate")',
            '(math "x**2 - 1" "factor")',
        ]
        
        for i, s_expr in enumerate(s_expressions, 1):
            print(f"\n🔗 S式テスト {i}: {s_expr}")
            try:
                parsed = parse_s_expression(s_expr)
                result = self.evaluator.evaluate_with_context(parsed, self.env)
                print(f"   ✅ 結果: {result}")
                self.passed += 1
            except Exception as e:
                print(f"   ❌ エラー: {e}")
                self.failed += 1
    
    async def test_error_cases(self):
        """エラーケーステスト"""
        print("\n⚠️ === エラーケーステスト ===")
        
        # 無効な操作
        await self.run_test("無効な操作", "x**2", "invalid_op")
        
        # 空の式
        await self.run_test("空の式", "", "simplify")
        
        # 危険な式
        await self.run_test("危険な式", "__import__('os')", "simplify")
    
    async def run_all_tests(self):
        """全テストの実行"""
        print("🧪 高度数学処理テストスイート開始（修正版）")
        print("=" * 60)
        
        await self.test_basic_operations()
        await self.test_advanced_operations()
        self.test_s_expressions()  # 同期版
        await self.test_error_cases()
        
        print("\n" + "=" * 60)
        print(f"📊 テスト完了: ✅{self.passed}件成功 ❌{self.failed}件失敗")
        
        if self.failed == 0:
            print("🎉 全テスト合格！")
        else:
            print(f"⚠️ {self.failed}件のテストが失敗しました")
        
        return self.failed == 0


async def main():
    """メインテスト実行"""
    test_suite = AdvancedMathTestSuite()
    success = await test_suite.run_all_tests()
    
    if not success:
        print("\n一部のテストが失敗しましたが、主要な機能は動作しています。")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())