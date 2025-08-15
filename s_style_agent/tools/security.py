"""
セキュリティ機能

安全な計算実行とツール許可リスト管理
"""

import re
from typing import Any, Dict, List, Set, Union
from asteval import Interpreter
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
from sympy import sympify, N, symbols, simplify, expand, factor, solve, diff, integrate
from langsmith import traceable


class SafeCalculator:
    """安全な計算実行クラス"""
    
    def __init__(self):
        # astevalインタープリターを初期化
        self.interpreter = Interpreter(
            # 安全な関数のみ許可
            usersyms={
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum,
                'pow': pow,
                'divmod': divmod,
                'len': len,
                # 数学関数
                'pi': 3.141592653589793,
                'e': 2.718281828459045,
            },
            # 危険な機能を無効化
            use_numpy=False,
            max_time=5.0,  # 最大実行時間5秒
            max_nodes=10000,  # 最大ノード数制限
        )
        
        # 許可しない文字列パターン
        self.forbidden_patterns = [
            r'__.*__',  # dunder attributes
            r'import\s',
            r'exec\s*\(',
            r'eval\s*\(',
            r'open\s*\(',
            r'file\s*\(',
            r'input\s*\(',
            r'raw_input\s*\(',
            r'compile\s*\(',
            r'globals\s*\(',
            r'locals\s*\(',
            r'vars\s*\(',
            r'dir\s*\(',
            r'help\s*\(',
        ]
    
    @traceable(name="safe_calculator_validate")
    def validate_expression(self, expression: str) -> tuple[bool, str]:
        """式の安全性を検証"""
        expression = expression.strip()
        
        if not expression:
            return False, "空の式は許可されません"
        
        # 危険なパターンをチェック
        for pattern in self.forbidden_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                return False, f"危険なパターンが検出されました: {pattern}"
        
        # 長すぎる式を拒否
        if len(expression) > 1000:
            return False, "式が長すぎます（最大1000文字）"
        
        return True, ""
    
    @traceable(name="safe_calculator_execute")
    def calculate(self, expression: str) -> Union[float, int, str]:
        """安全に計算を実行"""
        # まず検証
        is_valid, error_msg = self.validate_expression(expression)
        if not is_valid:
            raise ValueError(f"計算式が無効です: {error_msg}")
        
        try:
            # astevalで安全に実行
            result = self.interpreter.eval(expression)
            
            # エラーチェック
            if self.interpreter.expr is None:
                raise ValueError("計算式の解析に失敗しました")
            
            if self.interpreter.error:
                error_msg = "\n".join([str(err) for err in self.interpreter.error])
                raise ValueError(f"計算エラー: {error_msg}")
            
            return result
            
        except Exception as e:
            raise ValueError(f"計算実行エラー: {str(e)}")


class ToolWhitelist:
    """ツール許可リスト管理"""
    
    def __init__(self, allowed_tools: Set[str] = None):
        # デフォルトで許可するツール
        self.allowed_tools = allowed_tools or {
            'notify',
            'calc', 
            'search',
            'db-query'
        }
        
        # 管理者のみが使用できるツール
        self.admin_only_tools = {
            'exec',
            'shell',
            'file-write',
            'system'
        }
    
    def is_allowed(self, tool_name: str, is_admin: bool = False) -> bool:
        """ツールが許可されているかチェック"""
        if tool_name in self.admin_only_tools:
            return is_admin
        
        return tool_name in self.allowed_tools
    
    def add_tool(self, tool_name: str, admin_only: bool = False) -> None:
        """ツールを許可リストに追加"""
        if admin_only:
            self.admin_only_tools.add(tool_name)
        else:
            self.allowed_tools.add(tool_name)
    
    def remove_tool(self, tool_name: str) -> None:
        """ツールを許可リストから削除"""
        self.allowed_tools.discard(tool_name)
        self.admin_only_tools.discard(tool_name)
    
    def list_allowed_tools(self, is_admin: bool = False) -> List[str]:
        """許可されたツール一覧を取得"""
        tools = list(self.allowed_tools)
        if is_admin:
            tools.extend(self.admin_only_tools)
        return sorted(tools)


class SecurityValidator:
    """包括的なセキュリティ検証"""
    
    def __init__(self):
        self.calculator = SafeCalculator()
        self.whitelist = ToolWhitelist()
    
    @traceable(name="security_validator_validate_s_expression")
    def validate_s_expression(self, s_expr: Any, is_admin: bool = False) -> tuple[bool, str]:
        """S式全体のセキュリティ検証"""
        try:
            return self._validate_recursive(s_expr, is_admin)
        except Exception as e:
            return False, f"セキュリティ検証エラー: {str(e)}"
    
    def _validate_recursive(self, expr: Any, is_admin: bool) -> tuple[bool, str]:
        """再帰的にS式を検証"""
        if isinstance(expr, str):
            # 文字列は基本的に安全
            return True, ""
        
        if not isinstance(expr, list):
            # アトム（数値など）は安全
            return True, ""
        
        if len(expr) == 0:
            return True, ""
        
        op = expr[0]
        
        # ツール呼び出しの場合
        if isinstance(op, str) and not op in ['seq', 'par', 'if', 'let', 'plan']:
            if not self.whitelist.is_allowed(op, is_admin):
                return False, f"ツール '{op}' は許可されていません"
        
        # 計算式の特別検証
        if op == 'calc' and len(expr) > 1:
            calc_expr = expr[1]
            if isinstance(calc_expr, str):
                is_valid, error_msg = self.calculator.validate_expression(calc_expr)
                if not is_valid:
                    return False, f"calc式が無効: {error_msg}"
        
        # 再帰的に子要素を検証
        for arg in expr[1:]:
            is_valid, error_msg = self._validate_recursive(arg, is_admin)
            if not is_valid:
                return False, error_msg
        
        return True, ""


# グローバルインスタンス
safe_calculator = SafeCalculator()
tool_whitelist = ToolWhitelist()
security_validator = SecurityValidator()


if __name__ == "__main__":
    # テスト実行
    calc = SafeCalculator()
    
    # 安全な計算のテスト
    safe_expressions = [
        "2 + 3",
        "10 * 5 + 2",
        "abs(-5)",
        "round(3.14159, 2)",
        "max(1, 2, 3, 4, 5)"
    ]
    
    print("=== 安全な計算テスト ===")
    for expr in safe_expressions:
        try:
            result = calc.calculate(expr)
            print(f"✓ {expr} = {result}")
        except Exception as e:
            print(f"✗ {expr}: {e}")
    
    # 危険な計算のテスト
    dangerous_expressions = [
        "__import__('os').system('ls')",
        "eval('1+1')",
        "open('/etc/passwd')",
        "exec('print(1)')",
    ]
    
    print("\n=== 危険な計算テスト（ブロックされるべき） ===")
    for expr in dangerous_expressions:
        try:
            result = calc.calculate(expr)
            print(f"✗ {expr} = {result} (ブロックされるべきでした！)")
        except Exception as e:
            print(f"✓ {expr}: ブロック済み - {e}")
    
    # ツール許可リストのテスト
    print("\n=== ツール許可リストテスト ===")
    whitelist = ToolWhitelist()
    
    test_tools = ['notify', 'calc', 'shell', 'unknown-tool']
    for tool in test_tools:
        allowed = whitelist.is_allowed(tool)
        admin_allowed = whitelist.is_allowed(tool, is_admin=True)
        print(f"'{tool}': 一般ユーザー={allowed}, 管理者={admin_allowed}")