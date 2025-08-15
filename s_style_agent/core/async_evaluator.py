"""
非同期S式評価エンジン

真の並列実行とキャンセレーション対応を実装
"""

import asyncio
from typing import Any, Dict, List, Optional
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langsmith import traceable

from .parser import parse_s_expression, SExpression
from ..tools.security_sympy import security_validator, safe_sympy_calculator


class SecurityError(Exception):
    """セキュリティ関連のエラー"""
    pass


class AsyncEnvironment:
    """非同期対応の変数束縛管理クラス"""
    
    def __init__(self, parent: Optional['AsyncEnvironment'] = None):
        self.parent = parent
        self.bindings: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def define(self, var: str, val: Any) -> None:
        """変数を定義（スレッドセーフ）"""
        async with self._lock:
            self.bindings[var] = val
    
    async def lookup(self, var: str) -> Any:
        """変数を検索"""
        async with self._lock:
            if var in self.bindings:
                return self.bindings[var]
        
        if self.parent:
            return await self.parent.lookup(var)
        else:
            raise NameError(f"Name '{var}' is not defined")
    
    async def get_all_bindings(self) -> Dict[str, Any]:
        """すべての変数束縛を取得（デバッグ用）"""
        all_bindings = {}
        if self.parent:
            all_bindings.update(await self.parent.get_all_bindings())
        
        async with self._lock:
            all_bindings.update(self.bindings)
        
        return all_bindings


class AsyncContextualEvaluator:
    """非同期対応の文脈考慮S式評価器"""
    
    def __init__(self, llm_base_url: str = "http://192.168.79.1:1234/v1", 
                 model_name: str = "unsloth/gpt-oss-120b",
                 is_admin: bool = False,
                 max_parallel_tasks: int = 10):
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            api_key="dummy",  # ローカルLLMなのでダミー
            model=model_name,
            temperature=0.3
        )
        self.task_context = ""
        self.execution_history: List[Dict[str, Any]] = []
        self.is_admin = is_admin
        self.max_parallel_tasks = max_parallel_tasks
        self._semaphore = asyncio.Semaphore(max_parallel_tasks)
        self._task_counter = 0
        self._active_tasks: Dict[int, asyncio.Task] = {}
    
    def set_task_context(self, context: str) -> None:
        """タスクの文脈を設定"""
        self.task_context = context
    
    @traceable(name="async_evaluate_with_context")
    async def evaluate_with_context(self, expr: SExpression, env: AsyncEnvironment, 
                                  task_id: Optional[int] = None) -> Any:
        """文脈を考慮してS式を非同期評価"""
        if task_id is None:
            task_id = self._get_next_task_id()
        
        try:
            # セキュリティ検証を最初に実行
            is_valid, error_msg = security_validator.validate_s_expression(expr, self.is_admin)
            if not is_valid:
                raise SecurityError(f"セキュリティ検証失敗: {error_msg}")
            
            # セマフォを使用してリソース制限
            async with self._semaphore:
                # 基本評価
                result = await self._evaluate_basic_async(expr, env, task_id)
                
                # 複雑な評価が必要な場合は LLM を使用
                if self._needs_contextual_evaluation(expr):
                    contextual_result = await self._evaluate_contextually_async(expr, env, result)
                    return contextual_result
                
                return result
        
        finally:
            self._cleanup_task(task_id)
    
    def _get_next_task_id(self) -> int:
        """次のタスクIDを取得"""
        self._task_counter += 1
        return self._task_counter
    
    def _cleanup_task(self, task_id: int) -> None:
        """タスクのクリーンアップ"""
        self._active_tasks.pop(task_id, None)
    
    async def cancel_all_tasks(self) -> None:
        """すべてのアクティブタスクをキャンセル"""
        for task in self._active_tasks.values():
            task.cancel()
        
        # すべてのタスクの完了を待機
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        
        self._active_tasks.clear()
    
    def _needs_contextual_evaluation(self, expr: SExpression) -> bool:
        """文脈評価が必要かどうかを判定"""
        if not isinstance(expr, list) or len(expr) == 0:
            return False
        
        op = expr[0]
        # 条件分岐や複雑な制御構造では文脈評価を行う
        return op in ['if', 'cond', 'when', 'unless']
    
    @traceable(name="async_contextual_llm_evaluation")
    async def _evaluate_contextually_async(self, expr: SExpression, env: AsyncEnvironment, basic_result: Any) -> Any:
        """LLMを使用した非同期文脈考慮評価"""
        bindings = await env.get_all_bindings()
        
        prompt = f"""
タスク文脈: {self.task_context}

現在の変数束縛: {bindings}

実行履歴: {self.execution_history[-3:] if self.execution_history else "なし"}

評価対象のS式: {expr}

基本評価結果: {basic_result}

上記の文脈を考慮して、このS式の評価結果が適切かどうか判断し、
必要であれば修正した結果を提案してください。
結果のみを返してください。
"""
        
        try:
            # LLM呼び出しを非同期で実行
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            # LLMの応答を基本結果と比較して、適切な方を選択
            # 実装簡略化のため、ここでは基本結果を返す
            return basic_result
        except Exception:
            return basic_result
    
    @traceable(name="async_basic_s_expression_evaluation")
    async def _evaluate_basic_async(self, expr: SExpression, env: AsyncEnvironment, task_id: int) -> Any:
        """基本的なS式の非同期評価"""
        # 記録
        bindings = await env.get_all_bindings()
        self.execution_history.append({
            "expression": expr,
            "environment": bindings.copy(),
            "task_id": task_id
        })
        
        if isinstance(expr, str):
            try:
                return await env.lookup(expr)
            except NameError:
                return expr
        elif not isinstance(expr, list):
            return expr
        
        if len(expr) == 0:
            return expr
        
        op = expr[0]
        args = expr[1:]
        
        if op == 'plan':
            return await self._evaluate_basic_async(args[0], env, task_id)
        
        elif op == 'seq':
            # 順次実行
            result = None
            for arg in args:
                result = await self._evaluate_basic_async(arg, env, task_id)
            return result
        
        elif op == 'par':
            # 真の並列実行 - asyncio.gather を使用
            tasks = []
            for i, arg in enumerate(args):
                sub_task_id = self._get_next_task_id()
                task = asyncio.create_task(
                    self._evaluate_basic_async(arg, env, sub_task_id),
                    name=f"par_task_{task_id}_{i}"
                )
                self._active_tasks[sub_task_id] = task
                tasks.append(task)
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=False)
                return results
            except Exception as e:
                # エラーが発生した場合、他のタスクもキャンセル
                for task in tasks:
                    if not task.done():
                        task.cancel()
                raise e
        
        elif op == 'if':
            cond_val = await self._evaluate_basic_async(args[0], env, task_id)
            if cond_val:
                return await self._evaluate_basic_async(args[1], env, task_id)
            else:
                return await self._evaluate_basic_async(args[2], env, task_id) if len(args) > 2 else None
        
        elif op == 'let':
            bindings_list = args[0]
            body = args[1]
            new_env = AsyncEnvironment(parent=env)
            
            # bindings_listがリストでない場合はエラー
            if not isinstance(bindings_list, list):
                raise TypeError(f"let式の束縛リストはリストである必要があります: {type(bindings_list)}")
            
            # 変数束縛を並列で処理
            binding_tasks = []
            for binding in bindings_list:
                if not isinstance(binding, list) or len(binding) != 2:
                    raise TypeError(f"let式の束縛は[変数名, 値]の形式である必要があります: {binding}")
                var = binding[0]
                if not isinstance(var, str):
                    raise TypeError(f"変数名は文字列である必要があります: {var}")
                val_expr = binding[1]
                binding_tasks.append(self._process_binding(var, val_expr, env, new_env, task_id))
            
            await asyncio.gather(*binding_tasks)
            return await self._evaluate_basic_async(body, new_env, task_id)
        
        elif op == 'notify':
            message = await self._evaluate_basic_async(args[0], env, task_id)
            print(f"[NOTIFY] {message}")
            return message
        
        elif op == 'search':
            query = await self._evaluate_basic_async(args[0], env, task_id)
            print(f"[SEARCH] Query: {query}")
            # 検索を非同期で実行（ダミー実装）
            await asyncio.sleep(0.1)  # 非同期処理のシミュレート
            return f"検索結果: {query}"
        
        elif op == 'calc':
            expression = await self._evaluate_basic_async(args[0], env, task_id)
            try:
                # SymPyベースの安全な計算実行
                # CPU集約的な処理なので ThreadPoolExecutor で実行
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    safe_sympy_calculator.calculate, 
                    str(expression)
                )
                return result
            except Exception as e:
                return f"計算エラー: {e}"
        
        elif op == 'db-query':
            query = await self._evaluate_basic_async(args[0], env, task_id)
            print(f"[DB-QUERY] Query: {query}")
            # DB操作を非同期で実行（ダミー実装）
            await asyncio.sleep(0.05)
            return f"DB結果: {query}"
        
        else:
            raise NotImplementedError(f"Unknown operation: {op}")
    
    async def _process_binding(self, var: str, val_expr: SExpression, 
                             parent_env: AsyncEnvironment, 
                             new_env: AsyncEnvironment, 
                             task_id: int) -> None:
        """変数束縛を非同期で処理"""
        val = await self._evaluate_basic_async(val_expr, parent_env, task_id)
        await new_env.define(var, val)


@traceable(name="async_evaluate_s_expression")
async def evaluate_s_expression_async(s_expr_str: str, context: str = "", 
                                    is_admin: bool = False) -> Any:
    """S式文字列を非同期評価"""
    evaluator = AsyncContextualEvaluator(is_admin=is_admin)
    if context:
        evaluator.set_task_context(context)
    
    parsed_expr = parse_s_expression(s_expr_str)
    global_env = AsyncEnvironment()
    
    return await evaluator.evaluate_with_context(parsed_expr, global_env)


# Langchain Runnable として公開（非同期版）
async_evaluator_runnable = RunnableLambda(
    lambda x: asyncio.run(evaluate_s_expression_async(
        x.get("expression", ""), 
        x.get("context", ""),
        x.get("is_admin", False)
    ))
)


if __name__ == "__main__":
    # 非同期テスト実行
    async def test_async_evaluator():
        print("=== 非同期評価エンジンテスト ===")
        
        test_expressions = [
            "(notify \"非同期テスト開始\")",
            "(calc \"2 + 3 * 4\")",
            "(seq (notify \"ステップ1\") (calc \"10 / 2\") (notify \"ステップ2\"))",
            "(par (notify \"タスクA\") (notify \"タスクB\") (notify \"タスクC\"))",
            "(if (calc \"5 > 3\") (notify \"5は3より大きい\") (notify \"5は3以下\"))",
            "(let ((a 5) (b 10)) (calc \"5 + 10\"))",
            "(par (calc \"2**8\") (calc \"3**5\") (calc \"4**4\"))"
        ]
        
        for i, expr in enumerate(test_expressions, 1):
            print(f"\n--- テスト {i}: {expr} ---")
            try:
                start_time = asyncio.get_event_loop().time()
                result = await evaluate_s_expression_async(expr, "非同期テスト実行中")
                end_time = asyncio.get_event_loop().time()
                print(f"✓ 成功: {result} (実行時間: {end_time - start_time:.3f}秒)")
            except Exception as e:
                print(f"✗ エラー: {e}")
    
    # イベントループで実行
    asyncio.run(test_async_evaluator())