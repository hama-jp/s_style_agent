"""
S式評価エンジン - langchain/langgraphベース実装

文脈を考慮したS式評価システム
"""

from typing import Any, Dict, List, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langsmith import traceable
# from langgraph.graph import Graph
# from langgraph.graph.state import CompiledGraph

from .parser import parse_s_expression, SExpression
from ..tools.security_sympy import security_validator, safe_sympy_calculator


class SecurityError(Exception):
    """セキュリティ関連のエラー"""
    pass


class Environment:
    """変数束縛を管理する環境クラス"""
    
    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.bindings: Dict[str, Any] = {}
    
    def define(self, var: str, val: Any) -> None:
        """変数を定義"""
        self.bindings[var] = val
    
    def lookup(self, var: str) -> Any:
        """変数を検索"""
        if var in self.bindings:
            return self.bindings[var]
        elif self.parent:
            return self.parent.lookup(var)
        else:
            raise NameError(f"Name '{var}' is not defined")
    
    def get_all_bindings(self) -> Dict[str, Any]:
        """すべての変数束縛を取得（デバッグ用）"""
        all_bindings = {}
        if self.parent:
            all_bindings.update(self.parent.get_all_bindings())
        all_bindings.update(self.bindings)
        return all_bindings


class ContextualEvaluator:
    """文脈を考慮したS式評価器"""
    
    def __init__(self, llm_base_url: str = "http://192.168.79.1:1234/v1", 
                 model_name: str = "unsloth/gpt-oss-120b",
                 is_admin: bool = False):
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            api_key="dummy",  # ローカルLLMなのでダミー
            model=model_name,
            temperature=0.3
        )
        self.task_context = ""
        self.execution_history: List[Dict[str, Any]] = []
        self.is_admin = is_admin
    
    def set_task_context(self, context: str) -> None:
        """タスクの文脈を設定"""
        self.task_context = context
    
    @traceable(name="evaluate_with_context")
    def evaluate_with_context(self, expr: SExpression, env: Environment) -> Any:
        """文脈を考慮してS式を評価"""
        try:
            # セキュリティ検証を最初に実行
            is_valid, error_msg = security_validator.validate_s_expression(expr, self.is_admin)
            if not is_valid:
                raise SecurityError(f"セキュリティ検証失敗: {error_msg}")
            
            # 基本評価
            result = self._evaluate_basic(expr, env)
            
            # 複雑な評価が必要な場合は LLM を使用
            if self._needs_contextual_evaluation(expr):
                contextual_result = self._evaluate_contextually(expr, env, result)
                return contextual_result
            
            return result
        except Exception:
            raise

    def _needs_contextual_evaluation(self, expr: SExpression) -> bool:
        """文脈評価が必要かどうかを判定"""
        if not isinstance(expr, list) or len(expr) == 0:
            return False
        
        op = expr[0]
        # 条件分岐や複雑な制御構造では文脈評価を行う
        return op in ['if', 'cond', 'when', 'unless']
    
    @traceable(name="contextual_llm_evaluation")
    def _evaluate_contextually(self, expr: SExpression, env: Environment, basic_result: Any) -> Any:
        """LLMを使用した文脈考慮評価"""
        prompt = f"""
タスク文脈: {self.task_context}

現在の変数束縛: {env.get_all_bindings()}

実行履歴: {self.execution_history[-3:] if self.execution_history else "なし"}

評価対象のS式: {expr}

基本評価結果: {basic_result}

上記の文脈を考慮して、このS式の評価結果が適切かどうか判断し、
必要であれば修正した結果を提案してください。
結果のみを返してください。
"""
        
        try:
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            # LLMの応答を基本結果と比較して、適切な方を選択
            # 実装簡略化のため、ここでは基本結果を返す
            return basic_result
        except Exception:
            return basic_result
    
    @traceable(name="basic_s_expression_evaluation")
    def _evaluate_basic(self, expr: SExpression, env: Environment) -> Any:
        """基本的なS式評価"""
        # 記録
        self.execution_history.append({
            "expression": expr,
            "environment": env.get_all_bindings().copy()
        })
        
        if isinstance(expr, str):
            try:
                return env.lookup(expr)
            except NameError:
                return expr
        elif not isinstance(expr, list):
            return expr
        
        if len(expr) == 0:
            return expr
        
        op = expr[0]
        args = expr[1:]
        
        if op == 'plan':
            return self._evaluate_basic(args[0], env)
        elif op == 'seq':
            result = None
            for arg in args:
                result = self._evaluate_basic(arg, env)
            return result
        elif op == 'par':
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._evaluate_basic, arg, env) for arg in args]
                results = [future.result() for future in futures]
            return results
        elif op == 'if':
            cond_val = self._evaluate_basic(args[0], env)
            if cond_val:
                return self._evaluate_basic(args[1], env)
            else:
                return self._evaluate_basic(args[2], env) if len(args) > 2 else None
        elif op == 'let':
            bindings_list = args[0]
            body = args[1]
            new_env = Environment(parent=env)
            for binding in bindings_list:
                var = binding[0]
                val_expr = binding[1]
                new_env.define(var, self._evaluate_basic(val_expr, env))
            return self._evaluate_basic(body, new_env)
        elif op == 'notify':
            message = self._evaluate_basic(args[0], env)
            print(f"[NOTIFY] {message}")
            return message
        elif op == 'search':
            query = self._evaluate_basic(args[0], env)
            print(f"[SEARCH] Query: {query}")
            return f"検索結果: {query}"
        elif op == 'calc':
            expression = self._evaluate_basic(args[0], env)
            try:
                # SymPyベースの安全な計算実行
                result = safe_sympy_calculator.calculate(str(expression))
                return result
            except Exception as e:
                return f"計算エラー: {e}"
        elif op == 'db-query':
            query = self._evaluate_basic(args[0], env)
            print(f"[DB-QUERY] Query: {query}")
            return f"DB結果: {query}"
        else:
            raise NotImplementedError(f"Unknown operation: {op}")


@traceable(name="evaluate_s_expression")
def evaluate_s_expression(s_expr_str: str, context: str = "") -> Any:
    """S式文字列を評価"""
    evaluator = ContextualEvaluator()
    if context:
        evaluator.set_task_context(context)
    
    parsed_expr = parse_s_expression(s_expr_str)
    global_env = Environment()
    
    return evaluator.evaluate_with_context(parsed_expr, global_env)


# Langchain Runnable として公開
evaluator_runnable = RunnableLambda(
    lambda x: evaluate_s_expression(x.get("expression", ""), x.get("context", ""))
)


if __name__ == "__main__":
    # テスト実行
    test_expressions = [
        "(seq (notify \"開始\") (calc \"2+3\") (notify \"終了\"))",
        "(if (calc \"1 < 2\") (notify \"真\") (notify \"偽\"))",
        "(let ((x 10) (y 20)) (calc \"10+20\"))",
    ]
    
    for expr in test_expressions:
        print(f"\n--- 評価: {expr} ---")
        try:
            result = evaluate_s_expression(expr, "テスト実行中")
            print(f"結果: {result}")
        except Exception as e:
            print(f"エラー: {e}")