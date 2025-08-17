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
from .trace_logger import get_global_logger, ExecutionMetadata, ProvenanceType
from ..config.settings import settings
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
    
    def __init__(self, llm_base_url: str = None, 
                 model_name: str = None,
                 is_admin: bool = False):
        # 設定値を使用（引数が指定されていない場合）
        llm_base_url = llm_base_url or settings.llm.base_url
        model_name = model_name or settings.llm.model_name
        
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            api_key=settings.llm.api_key,
            model=model_name,
            temperature=settings.llm.temperature
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
        logger = get_global_logger()
        
        # トレースログ開始（S式文字列表現も含める）
        s_expr_str = self._format_s_expression_for_trace(expr)
        entry_id = logger.start_operation(
            operation="evaluate",
            input_data={"s_expr": s_expr_str, "parsed": expr},
            explanation=f"S式評価: {s_expr_str}"
        )
        
        try:
            # 記録
            self.execution_history.append({
                "expression": expr,
                "environment": env.get_all_bindings().copy()
            })
        
            if isinstance(expr, str):
                try:
                    result = env.lookup(expr)
                    # トレースログ完了
                    metadata = ExecutionMetadata(provenance=ProvenanceType.BUILTIN)
                    logger.end_operation(entry_id, result, metadata)
                    return result
                except NameError:
                    result = expr
                    metadata = ExecutionMetadata(provenance=ProvenanceType.BUILTIN)
                    logger.end_operation(entry_id, result, metadata)
                    return result
            elif not isinstance(expr, list):
                metadata = ExecutionMetadata(provenance=ProvenanceType.BUILTIN)
                logger.end_operation(entry_id, expr, metadata)
                return expr
            
            if len(expr) == 0:
                metadata = ExecutionMetadata(provenance=ProvenanceType.BUILTIN)
                logger.end_operation(entry_id, expr, metadata)
                return expr
            
            op = expr[0]
            args = expr[1:]
            
            # パスをプッシュ（子ノードに入る）
            logger.push_path(0)  # 操作自体のインデックス
            
            result = None
            
            if op == 'plan':
                result = self._evaluate_basic(args[0], env)
            elif op == 'seq':
                result = None
                for i, arg in enumerate(args):
                    logger.push_path(i + 1)  # 各引数のインデックス
                    result = self._evaluate_basic(arg, env)
                    logger.pop_path()
            elif op == 'par':
                with ThreadPoolExecutor() as executor:
                    futures = []
                    for i, arg in enumerate(args):
                        logger.push_path(i + 1)
                        futures.append(executor.submit(self._evaluate_basic, arg, env))
                        logger.pop_path()
                    result = [future.result() for future in futures]
            elif op == 'if':
                logger.push_path(1)
                cond_val = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                if cond_val:
                    logger.push_path(2)
                    result = self._evaluate_basic(args[1], env)
                    logger.pop_path()
                else:
                    if len(args) > 2:
                        logger.push_path(3)
                        result = self._evaluate_basic(args[2], env)
                        logger.pop_path()
                    else:
                        result = None
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
                    logger.push_path(2)
                    result = self._evaluate_basic(form, env)
                    logger.pop_path()
                except Exception as e:
                    # エラー発生時: エラー情報を環境に設定してフォールバック実行
                    error_env = Environment(parent=env)
                    error_info = {
                        "type": type(e).__name__,
                        "message": str(e),
                        "original_expression": form
                    }
                    error_env.define(error_var, error_info)
                    logger.push_path(3)
                    result = self._evaluate_basic(fallback_form, error_env)
                    logger.pop_path()
            elif op == 'set':
                # 変数代入: (set var_name value)
                if len(args) != 2:
                    raise TypeError(f"set式は2つの引数が必要です: (set var_name value), 受信: {len(args)}個")
                
                var_name = args[0]
                value_expr = args[1]
                
                if not isinstance(var_name, str):
                    raise TypeError(f"変数名は文字列である必要があります: {var_name}")
                
                logger.push_path(2)
                value = self._evaluate_basic(value_expr, env)
                logger.pop_path()
                
                env.set(var_name, value)
                result = value
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
                    logger.push_path(1)
                    condition_result = self._evaluate_basic(condition_expr, env)
                    logger.pop_path()
                    
                    # 条件が偽なら終了
                    if not condition_result:
                        break
                    
                    # ボディ実行
                    logger.push_path(2)
                    result = self._evaluate_basic(body_expr, env)
                    logger.pop_path()
                    iteration_count += 1
            elif op == '+':
                # 加算: (+ a b ...)
                if len(args) < 2:
                    raise TypeError("加算には少なくとも2つの引数が必要です")
                
                logger.push_path(1)
                result = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                for i, arg in enumerate(args[1:], 2):
                    logger.push_path(i)
                    val = self._evaluate_basic(arg, env)
                    logger.pop_path()
                    result = result + val
            elif op == '<':
                # 比較: (< a b)
                if len(args) != 2:
                    raise TypeError("比較には2つの引数が必要です")
                
                logger.push_path(1)
                a = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                logger.push_path(2)
                b = self._evaluate_basic(args[1], env)
                logger.pop_path()
                
                result = a < b
            elif op == 'let':
                bindings_list = args[0]
                body = args[1]
                new_env = Environment(parent=env)
                
                # bindings_listがリストでない場合はエラー
                if not isinstance(bindings_list, list):
                    raise TypeError(f"let式の束縛リストはリストである必要があります: {type(bindings_list)}")
                
                for i, binding in enumerate(bindings_list):
                    if not isinstance(binding, list) or len(binding) != 2:
                        raise TypeError(f"let式の束縛は[変数名, 値]の形式である必要があります: {binding}")
                    var = binding[0]
                    if not isinstance(var, str):
                        raise TypeError(f"変数名は文字列である必要があります: {var}")
                    val_expr = binding[1]
                    
                    logger.push_path(1 + i)
                    value = self._evaluate_basic(val_expr, env)
                    logger.pop_path()
                    
                    new_env.define(var, value)
                
                logger.push_path(len(bindings_list) + 1)
                result = self._evaluate_basic(body, new_env)
                logger.pop_path()
            elif op == 'notify':
                logger.push_path(1)
                message = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                print(f"[NOTIFY] {message}")
                result = message
            elif op == 'search':
                logger.push_path(1)
                query = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
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
                                search_result = future.result(timeout=30)
                            
                            if search_result.get("success"):
                                # 検索結果をLLMで抽出・要約
                                raw_result = search_result.get("result")
                                try:
                                    from ..tools.search_result_extractor import search_extractor
                                    extracted_info = search_extractor.extract_information(str(query), raw_result)
                                    print(f"[SEARCH] 抽出された情報: {extracted_info}")
                                    result = extracted_info
                                except Exception as e:
                                    print(f"[SEARCH] 情報抽出エラー: {e}")
                                    result = raw_result
                            else:
                                print(f"[SEARCH] MCPツールエラー: {search_result.get('error')}")
                                result = f"検索エラー: {search_result.get('error')}"
                        except Exception as e:
                            print(f"[SEARCH] MCP検索実行エラー: {e}")
                            result = f"検索実行エラー: {e}"
                    else:
                        print("[SEARCH] MCPツールは初期化されているが検索ツールが見つかりません")
                        result = f"ダミー検索結果: {query}"
                else:
                    print("[SEARCH] MCPツールが初期化されていません。ダミー結果を返します")
                    result = f"ダミー検索結果: {query}"
            elif op == 'calc':
                logger.push_path(1)
                expression = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                try:
                    # 記号数学エンジンによる計算
                    calc_result = sp.N(sp.sympify(str(expression)))
                    result = float(calc_result) if calc_result.is_number else str(calc_result)
                except Exception as e:
                    result = f"計算エラー: {e}"
            elif op == 'db-query':
                logger.push_path(1)
                query = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                print(f"[DB-QUERY] Query: {query}")
                result = f"DB結果: {query}"
            elif op == 'math':
                # 記号数学処理エンジン
                logger.push_path(1)
                expression = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                logger.push_path(2)
                operation = self._evaluate_basic(args[1], env)
                logger.pop_path()
                
                var_name = args[2] if len(args) > 2 else "x"
                
                try:
                    expr = sp.sympify(str(expression))
                    var = sp.symbols(str(var_name))
                    
                    if operation == "diff":
                        math_result = sp.diff(expr, var)
                    elif operation == "integrate":
                        math_result = sp.integrate(expr, var)
                    elif operation == "factor":
                        math_result = sp.factor(expr)
                    elif operation == "expand":
                        math_result = sp.expand(expr)
                    elif operation == "simplify":
                        math_result = sp.simplify(expr)
                    elif operation == "solve":
                        math_result = sp.solve(expr, var)
                    else:
                        result = f"不明な操作: {operation}"
                        math_result = None
                    
                    if math_result is not None:
                        result = str(math_result)
                except Exception as e:
                    result = f"数学処理エラー: {e}"
            elif op == 'step_math':
                # 段階的数学解法エンジン
                logger.push_path(1)
                expression = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
                logger.push_path(2)
                operation = self._evaluate_basic(args[1], env)
                logger.pop_path()
                
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
                                step_result = future.result()
                        except RuntimeError:
                            # イベントループが実行中でない場合
                            step_result = asyncio.run(tool.execute(
                                expression=str(expression),
                                operation=str(operation),
                                var=str(var_name)
                            ))
                        
                        if step_result.success:
                            result = step_result.result
                        else:
                            result = f"段階的数学処理エラー: {step_result.error}"
                            
                    except Exception as e:
                        result = f"段階的数学処理実行エラー: {e}"
                        
                except Exception as e:
                    result = f"段階的数学処理エラー: {e}"
            elif op == 'ask_user':
                # ユーザー質問ツール
                logger.push_path(1)
                question = self._evaluate_basic(args[0], env)
                logger.pop_path()
                
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
                        user_result = future.result()
                    
                    if user_result.success:
                        # 環境に変数を設定
                        env.define(str(variable_name), user_result.result)
                        result = user_result.result
                    else:
                        result = f"ユーザー質問エラー: {user_result.error}"
                        
                except Exception as e:
                    result = f"ユーザー質問処理エラー: {e}"
            else:
                # 統一ツール実行サービスを使用
                from .tool_executor import get_tool_executor
                tool_executor = get_tool_executor()
                
                try:
                    # パラメータを準備
                    kwargs = {}
                    for i, arg in enumerate(args):
                        param_name = f"arg_{i}" if i > 0 else "query"
                        logger.push_path(i + 1)
                        kwargs[param_name] = self._evaluate_basic(arg, env)
                        logger.pop_path()
                    
                    # 統一ツール実行サービス経由で実行（同期版）
                    import asyncio
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(tool_executor.execute_tool(str(op), **kwargs))
                        loop.close()
                    except Exception as e:
                        result = f"ツール実行エラー: {e}"
                        
                except Exception as e:
                    result = f"ツール処理エラー: {e}"
            
            # パスをポップ（親ノードに戻る）
            logger.pop_path()
            
            # トレースログ完了
            metadata = ExecutionMetadata(
                provenance=ProvenanceType.BUILTIN,
                context={"operation": op, "args_count": len(args)}
            )
            logger.end_operation(entry_id, result, metadata)
            return result
            
        except Exception as e:
            # エラーログ
            logger.log_error("evaluate", expr, e, f"S式評価中にエラー: {op if 'op' in locals() else 'unknown'}")
            # パスをクリア（エラー時の安全処理）
            logger.current_path.clear()
            raise


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
    
    def _format_s_expression_for_trace(self, expr: Any) -> str:
        """S式をトレース表示用に文字列フォーマット"""
        if isinstance(expr, str):
            return f'"{expr}"' if ' ' in expr else expr
        elif isinstance(expr, list):
            if not expr:
                return "()"
            
            formatted_items = []
            for item in expr:
                formatted_items.append(self._format_s_expression_for_trace(item))
            
            return f"({' '.join(formatted_items)})"
        else:
            return str(expr)