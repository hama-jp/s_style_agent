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
import sympy as sp


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
    
    def set(self, var: str, val: Any) -> None:
        """既存変数に値を設定（スコープチェーン対応）"""
        if var in self.bindings:
            self.bindings[var] = val
        elif self.parent:
            self.parent.set(var, val)
        else:
            raise NameError(f"Name '{var}' is not defined")
    
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
                 model_name: str = "openai/gpt-oss-20b",
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
            # 基本的な安全性チェック（セキュリティレイヤーを簡素化）
            if isinstance(expr, list) and len(expr) > 0 and expr[0] == "__import__":
                raise SecurityError("危険な操作は許可されていません")
            
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
        elif op == 'handle':
            # try/catch構文: (handle error_var form fallback_form)
            if len(args) != 3:
                raise TypeError(f"handle式は3つの引数が必要です: (handle error_var form fallback_form), 受信: {len(args)}個")
            
            error_var = args[0]
            form = args[1]
            fallback_form = args[2]
            
            if not isinstance(error_var, str):
                raise TypeError(f"エラー変数名は文字列である必要があります: {error_var}")
            
            try:
                # メイン処理を実行
                return self._evaluate_basic(form, env)
            except Exception as e:
                # エラー発生時: エラー情報を環境に設定してフォールバック実行
                error_env = Environment(parent=env)
                error_info = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "original_expression": form
                }
                error_env.define(error_var, error_info)
                return self._evaluate_basic(fallback_form, error_env)
        elif op == 'set':
            # 変数代入: (set var_name value)
            if len(args) != 2:
                raise TypeError(f"set式は2つの引数が必要です: (set var_name value), 受信: {len(args)}個")
            
            var_name = args[0]
            value_expr = args[1]
            
            if not isinstance(var_name, str):
                raise TypeError(f"変数名は文字列である必要があります: {var_name}")
            
            value = self._evaluate_basic(value_expr, env)
            env.set(var_name, value)
            return value
        elif op == 'while':
            # while構文: (while condition body max_iterations)
            if len(args) < 2 or len(args) > 3:
                raise TypeError(f"while式は2-3個の引数が必要です: (while condition body [max_iterations]), 受信: {len(args)}個")
            
            condition_expr = args[0]
            body_expr = args[1]
            max_iterations = args[2] if len(args) > 2 else 1000  # デフォルト上限
            
            # 最大反復数の評価と安全性チェック
            if not isinstance(max_iterations, int):
                max_iterations = self._evaluate_basic(max_iterations, env)
            
            if not isinstance(max_iterations, (int, float)) or max_iterations <= 0:
                raise TypeError(f"最大反復数は正の数値である必要があります: {max_iterations}")
            
            max_iterations = int(max_iterations)
            if max_iterations > 10000:  # 安全上限
                raise ValueError(f"最大反復数が制限を超えています: {max_iterations} > 10000")
            
            # while ループ実行
            result = None
            iteration_count = 0
            
            while iteration_count < max_iterations:
                # 条件評価
                condition_result = self._evaluate_basic(condition_expr, env)
                
                # 条件が偽なら終了
                if not condition_result:
                    break
                
                # ボディ実行
                result = self._evaluate_basic(body_expr, env)
                iteration_count += 1
            
            return result
        elif op == '+':
            # 加算: (+ a b ...)
            if len(args) < 2:
                raise TypeError("加算には少なくとも2つの引数が必要です")
            result = self._evaluate_basic(args[0], env)
            for arg in args[1:]:
                val = self._evaluate_basic(arg, env)
                result = result + val
            return result
        elif op == '<':
            # 比較: (< a b)
            if len(args) != 2:
                raise TypeError("比較には2つの引数が必要です")
            a = self._evaluate_basic(args[0], env)
            b = self._evaluate_basic(args[1], env)
            return a < b
        elif op == 'let':
            bindings_list = args[0]
            body = args[1]
            new_env = Environment(parent=env)
            
            # bindings_listがリストでない場合はエラー
            if not isinstance(bindings_list, list):
                raise TypeError(f"let式の束縛リストはリストである必要があります: {type(bindings_list)}")
            
            for binding in bindings_list:
                if not isinstance(binding, list) or len(binding) != 2:
                    raise TypeError(f"let式の束縛は[変数名, 値]の形式である必要があります: {binding}")
                var = binding[0]
                if not isinstance(var, str):
                    raise TypeError(f"変数名は文字列である必要があります: {var}")
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
            
            # MCPツールが利用可能な場合はそれを使用
            from ..mcp.manager import mcp_manager
            from ..mcp.robust_client import robust_mcp_client
            
            if mcp_manager.initialized:
                available_tools = robust_mcp_client.list_tools()
                
                # 検索ツールを優先順位で選択
                search_tools = []
                if 'brave_web_search' in available_tools:
                    search_tools.append('brave_web_search')
                if 'brave_local_search' in available_tools:
                    search_tools.append('brave_local_search')
                
                if search_tools:
                    # Web検索を優先的に使用
                    selected_tool = search_tools[0]
                    print(f"[SEARCH] MCPツール '{selected_tool}' を使用して検索中...")
                    
                    try:
                        import asyncio
                        import concurrent.futures
                        
                        # 新しいスレッドで非同期処理を実行
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                robust_mcp_client.call_tool(selected_tool, {"query": str(query)})
                            )
                            result = future.result(timeout=30)
                        
                        if result.get("success"):
                            # 検索結果をLLMで抽出・要約
                            raw_result = result.get("result")
                            try:
                                from ..tools.search_result_extractor import search_extractor
                                extracted_info = search_extractor.extract_information(str(query), raw_result)
                                print(f"[SEARCH] 抽出された情報: {extracted_info}")
                                return extracted_info
                            except Exception as e:
                                print(f"[SEARCH] 情報抽出エラー: {e}")
                                return raw_result
                        else:
                            print(f"[SEARCH] MCPツールエラー: {result.get('error')}")
                            return f"検索エラー: {result.get('error')}"
                    except Exception as e:
                        print(f"[SEARCH] MCP検索実行エラー: {e}")
                        return f"検索実行エラー: {e}"
                else:
                    print("[SEARCH] MCPツールは初期化されているが検索ツールが見つかりません")
                    return f"ダミー検索結果: {query}"
            else:
                print("[SEARCH] MCPツールが初期化されていません。ダミー結果を返します")
                return f"ダミー検索結果: {query}"
        elif op == 'calc':
            expression = self._evaluate_basic(args[0], env)
            try:
                # 記号数学エンジンによる計算
                result = sp.N(sp.sympify(str(expression)))
                return float(result) if result.is_number else str(result)
            except Exception as e:
                return f"計算エラー: {e}"
        elif op == 'db-query':
            query = self._evaluate_basic(args[0], env)
            print(f"[DB-QUERY] Query: {query}")
            return f"DB結果: {query}"
        elif op == 'math':
            # 記号数学処理エンジン
            expression = self._evaluate_basic(args[0], env)
            operation = self._evaluate_basic(args[1], env)
            var_name = args[2] if len(args) > 2 else "x"
            
            try:
                expr = sp.sympify(str(expression))
                var = sp.symbols(str(var_name))
                
                if operation == "diff":
                    result = sp.diff(expr, var)
                elif operation == "integrate":
                    result = sp.integrate(expr, var)
                elif operation == "factor":
                    result = sp.factor(expr)
                elif operation == "expand":
                    result = sp.expand(expr)
                elif operation == "simplify":
                    result = sp.simplify(expr)
                elif operation == "solve":
                    result = sp.solve(expr, var)
                else:
                    return f"不明な操作: {operation}"
                
                return str(result)
            except Exception as e:
                return f"数学処理エラー: {e}"
        elif op == 'step_math':
            # 段階的数学解法エンジン
            expression = self._evaluate_basic(args[0], env)
            operation = self._evaluate_basic(args[1], env)
            var_name = args[2] if len(args) > 2 else "x"
            
            try:
                from ..tools.math_engine import StepMathEngine
                tool = StepMathEngine()
                
                # 同期的に実行するためにasyncioを使用
                import asyncio
                try:
                    # 現在のイベントループを取得、なければ新規作成
                    try:
                        loop = asyncio.get_running_loop()
                        # 新しいスレッドで実行
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                tool.execute(
                                    expression=str(expression),
                                    operation=str(operation),
                                    var=str(var_name)
                                )
                            )
                            result = future.result()
                    except RuntimeError:
                        # イベントループが実行中でない場合
                        result = asyncio.run(tool.execute(
                            expression=str(expression),
                            operation=str(operation),
                            var=str(var_name)
                        ))
                    
                    if result.success:
                        return result.result
                    else:
                        return f"段階的数学処理エラー: {result.error}"
                        
                except Exception as e:
                    return f"段階的数学処理実行エラー: {e}"
                    
            except Exception as e:
                return f"段階的数学処理エラー: {e}"
        elif op == 'ask_user':
            # ユーザー質問ツール
            question = self._evaluate_basic(args[0], env)
            variable_name = args[1] if len(args) > 1 else "user_input"
            question_type = args[2] if len(args) > 2 else "required"
            
            try:
                from ..tools.user_interaction import AskUserTool
                tool = AskUserTool()
                
                import asyncio
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        tool.execute(
                            question=str(question),
                            variable_name=str(variable_name),
                            question_type=str(question_type)
                        )
                    )
                    result = future.result()
                
                if result.success:
                    # 環境に変数を設定
                    env.define(str(variable_name), result.result)
                    return result.result
                else:
                    return f"ユーザー質問エラー: {result.error}"
                    
            except Exception as e:
                return f"ユーザー質問処理エラー: {e}"
        else:
            # MCPツールもチェック
            from ..mcp.manager import mcp_manager
            from ..mcp.robust_client import robust_mcp_client
            
            # MCPツールから検索
            if mcp_manager.initialized and str(op) in robust_mcp_client.list_tools():
                try:
                    # パラメータを準備（簡単な方法）
                    kwargs = {}
                    for i, arg in enumerate(args):
                        param_name = f"arg_{i}" if i > 0 else "query"  # 一般的なパラメータ名
                        kwargs[param_name] = self._evaluate_basic(arg, env)
                    
                    # MCPツールを実行（同期的に）
                    import asyncio
                    try:
                        # 非同期メソッドを同期的に実行
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(robust_mcp_client.call_tool(str(op), kwargs))
                        loop.close()
                        
                        if result.get("success"):
                            return result.get("result")
                        else:
                            return f"MCPツールエラー: {result.get('error')}"
                    except Exception as e:
                        return f"MCPツール実行エラー: {e}"
                except Exception as e:
                    return f"MCPツール処理エラー: {e}"
            
            # 通常のツールレジストリから検索
            from ..tools.base import global_registry
            try:
                tool = global_registry.get_tool(str(op))
                if tool:
                    # パラメータを準備
                    kwargs = {}
                    schema = tool.schema
                    for i, param in enumerate(schema.parameters):
                        if i < len(args):
                            kwargs[param.name] = self._evaluate_basic(args[i], env)
                    
                    # ツールを実行（同期版）
                    import asyncio
                    try:
                        # 非同期メソッドを同期的に実行
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(tool.execute(**kwargs))
                        loop.close()
                        
                        if result.success:
                            return result.result
                        else:
                            return f"ツールエラー: {result.error}"
                    except Exception as e:
                        return f"ツール実行エラー: {e}"
                else:
                    raise NotImplementedError(f"Unknown operation: {op}")
            except Exception:
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