"""
SymPyベースのセキュリティ機能

安全な数式処理とツール許可リスト管理
"""

import re
from typing import Any, Dict, List, Set, Union

# 型エイリアス (parser.pyから)
SExpression = Union[str, int, float, List['SExpression']]
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
from sympy import sympify, N, symbols, simplify, expand, factor, solve, diff, integrate
from langsmith import traceable


class SafeSymPyCalculator:
    """SymPyベースの安全な計算実行クラス"""
    
    def __init__(self) -> None:
        # 許可される関数と定数
        self.allowed_functions = {
            # 基本演算
            'abs', 'round', 'min', 'max', 'sum', 'pow',
            # 三角関数
            'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
            'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
            # 指数・対数
            'exp', 'log', 'ln', 'log10', 'log2', 'sqrt',
            # その他の数学関数
            'factorial', 'gamma', 'floor', 'ceiling', 'gcd', 'lcm',
            # SymPy特有
            'simplify', 'expand', 'factor', 'solve', 'diff', 'integrate',
            'limit', 'series', 'Matrix', 'symbols', 'Symbol'
        }
        
        # 許可される定数
        self.allowed_constants = {
            'pi', 'e', 'I', 'oo', 'zoo', 'nan', 'E', 'Pi'
        }
        
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
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'delattr\s*\(',
            r'hasattr\s*\(',
        ]
    
    @traceable(name="safe_sympy_validate")
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
        if len(expression) > 2000:
            return False, "式が長すぎます（最大2000文字）"
        
        return True, ""
    
    @traceable(name="safe_sympy_calculate")
    def calculate(self, expression: str, mode: str = "numeric") -> Union[float, int, str, sp.Basic]:
        """SymPyで安全に計算を実行
        
        Args:
            expression: 計算式
            mode: "numeric" (数値計算), "symbolic" (記号計算), "simplify" (簡約)
        """
        # まず検証
        is_valid, error_msg = self.validate_expression(expression)
        if not is_valid:
            raise ValueError(f"計算式が無効です: {error_msg}")
        
        try:
            # SymPyで式を解析
            # sympifyは文字列を安全にSymPy表現に変換
            expr = sympify(expression, evaluate=False)
            
            if mode == "numeric":
                # 数値計算
                result = N(expr)
                # 可能であれば Python の数値型に変換
                if result.is_number:
                    if result.is_integer:
                        return int(result)
                    else:
                        return float(result)
                return str(result)
            
            elif mode == "symbolic":
                # 記号計算（そのまま返す）
                return str(expr)
            
            elif mode == "simplify":
                # 簡約
                simplified = simplify(expr)
                return str(simplified)
            
            else:
                raise ValueError(f"不明なモード: {mode}")
                
        except Exception as e:
            raise ValueError(f"SymPy計算エラー: {str(e)}")
    
    @traceable(name="safe_sympy_advanced")
    def advanced_calculate(self, expression: str, operation: str, **kwargs: Any) -> str:
        """高度な数式処理
        
        Args:
            expression: 対象式
            operation: 操作 ("diff", "integrate", "solve", "expand", "factor")
            **kwargs: 追加パラメータ
        """
        is_valid, error_msg = self.validate_expression(expression)
        if not is_valid:
            raise ValueError(f"計算式が無効です: {error_msg}")
        
        try:
            expr = sympify(expression)
            
            if operation == "diff":
                # 微分
                var = symbols(kwargs.get("var", "x"))
                result = diff(expr, var)
                return str(result)
            
            elif operation == "integrate":
                # 積分
                var = symbols(kwargs.get("var", "x"))
                result = integrate(expr, var)
                return str(result)
            
            elif operation == "solve":
                # 方程式を解く
                var = symbols(kwargs.get("var", "x"))
                result = solve(expr, var)
                return str(result)
            
            elif operation == "expand":
                # 展開
                result = expand(expr)
                return str(result)
            
            elif operation == "factor":
                # 因数分解
                result = factor(expr)
                return str(result)
            
            else:
                raise ValueError(f"不明な操作: {operation}")
                
        except Exception as e:
            raise ValueError(f"高度計算エラー: {str(e)}")


class ToolWhitelist:
    """ツール許可リスト管理"""
    
    def __init__(self, allowed_tools: Optional[Set[str]] = None) -> None:
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
    
    def __init__(self) -> None:
        self.calculator = SafeSymPyCalculator()
        self.whitelist = ToolWhitelist()
    
    @traceable(name="security_validator_validate_s_expression")
    def validate_s_expression(self, s_expr: SExpression, is_admin: bool = False) -> tuple[bool, str]:
        """S式全体のセキュリティ検証"""
        try:
            return self._validate_recursive(s_expr, is_admin)
        except Exception as e:
            return False, f"セキュリティ検証エラー: {str(e)}"
    
    def _validate_recursive(self, expr: SExpression, is_admin: bool) -> tuple[bool, str]:
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
        
        # ツール呼び出しの場合（制御構造は除く）
        control_structures = ['seq', 'par', 'if', 'let', 'plan']
        if isinstance(op, str) and op not in control_structures:
            if not self.whitelist.is_allowed(op, is_admin):
                return False, f"ツール '{op}' は許可されていません"
        
        # 計算式の特別検証
        if op == 'calc' and len(expr) > 1:
            calc_expr = expr[1]
            if isinstance(calc_expr, str):
                is_valid, error_msg = self.calculator.validate_expression(calc_expr)
                if not is_valid:
                    return False, f"calc式が無効: {error_msg}"
        
        # let式の特別処理
        if op == 'let' and len(expr) >= 3:
            # let式の変数束縛部分はスキップし、本体のみ検証
            bindings = expr[1]
            body = expr[2]
            
            # 束縛の値部分のみ検証
            if isinstance(bindings, list):
                for binding in bindings:
                    if isinstance(binding, list) and len(binding) >= 2:
                        # 変数名（binding[0]）はスキップ、値（binding[1]）のみ検証
                        is_valid, error_msg = self._validate_recursive(binding[1], is_admin)
                        if not is_valid:
                            return False, error_msg
            
            # 本体を検証
            return self._validate_recursive(body, is_admin)
        
        # その他の場合は通常の再帰的検証
        for arg in expr[1:]:
            is_valid, error_msg = self._validate_recursive(arg, is_admin)
            if not is_valid:
                return False, error_msg
        
        return True, ""


# グローバルインスタンス
safe_sympy_calculator = SafeSymPyCalculator()
tool_whitelist = ToolWhitelist()
security_validator = SecurityValidator()


if __name__ == "__main__":
    # テスト実行
    calc = SafeSymPyCalculator()
    
    # 基本計算のテスト
    basic_expressions = [
        "2 + 3",
        "10 * 5 + 2",
        "sqrt(16)",
        "sin(pi/2)",
        "exp(1)",
        "log(e)",
        "2**10",
        "factorial(5)"
    ]
    
    print("=== 基本計算テスト ===")
    for expr in basic_expressions:
        try:
            result = calc.calculate(expr, mode="numeric")
            print(f"✓ {expr} = {result}")
        except Exception as e:
            print(f"✗ {expr}: {e}")
    
    # 記号計算のテスト
    symbolic_expressions = [
        "x + y",
        "x**2 + 2*x + 1",
        "sin(x)**2 + cos(x)**2"
    ]
    
    print("\n=== 記号計算テスト ===")
    for expr in symbolic_expressions:
        try:
            result = calc.calculate(expr, mode="symbolic")
            simplified = calc.calculate(expr, mode="simplify")
            print(f"✓ {expr} → {result} → simplified: {simplified}")
        except Exception as e:
            print(f"✗ {expr}: {e}")
    
    # 高度な操作のテスト
    print("\n=== 高度な操作テスト ===")
    try:
        # 微分
        result = calc.advanced_calculate("x**2 + 3*x + 2", "diff", var="x")
        print(f"✓ d/dx(x²+3x+2) = {result}")
        
        # 積分
        result = calc.advanced_calculate("2*x + 3", "integrate", var="x")
        print(f"✓ ∫(2x+3)dx = {result}")
        
        # 展開
        result = calc.advanced_calculate("(x+1)**2", "expand")
        print(f"✓ expand((x+1)²) = {result}")
        
        # 因数分解
        result = calc.advanced_calculate("x**2 - 1", "factor")
        print(f"✓ factor(x²-1) = {result}")
        
    except Exception as e:
        print(f"✗ 高度な操作エラー: {e}")
    
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