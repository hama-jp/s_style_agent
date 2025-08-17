"""
S式エージェント 共通サービス

CLI/TUI両方で使用される共通機能を提供
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from langchain_openai import ChatOpenAI

from ..config.settings import settings
from ..tools.builtin_tools import register_builtin_tools
from ..core.evaluator import ContextualEvaluator, Environment
from ..core.async_evaluator import AsyncContextualEvaluator, AsyncEnvironment
from ..core.parser import parse_s_expression
from ..core.trace_logger import configure_trace_logging, TraceLogger


class AgentService:
    """S式エージェントの共通サービス"""
    
    def __init__(self, 
                 llm_base_url: Optional[str] = None,
                 model_name: Optional[str] = None,
                 use_async: bool = True):
        """
        共通サービスを初期化
        
        Args:
            llm_base_url: LLM API ベースURL
            model_name: モデル名
            use_async: 非同期実行モード
        """
        # 設定値を取得（引数が指定されていない場合は設定ファイルから）
        self.llm_base_url = llm_base_url or settings.llm.base_url
        self.model_name = model_name or settings.llm.model_name
        self.use_async = use_async
        
        # LLM初期化
        self.llm = ChatOpenAI(
            base_url=self.llm_base_url,
            api_key=settings.llm.api_key,
            model=self.model_name,
            temperature=settings.llm.temperature
        )
        
        # 統一ツール実行サービスを使用
        from .tool_executor import get_tool_executor
        self.tool_executor = get_tool_executor()
        
        # 評価器初期化
        if use_async:
            self.async_evaluator = AsyncContextualEvaluator(self.llm_base_url, self.model_name)
            self.async_global_env = AsyncEnvironment()
        else:
            self.evaluator = ContextualEvaluator(self.llm_base_url, self.model_name)
            self.global_env = Environment()
        
        # セッション履歴
        self.session_history: List[Dict[str, Any]] = []
        
        # 組み込みツールを登録
        register_builtin_tools()
        
        # MCP初期化フラグ（統一ツール実行サービス経由）
        self.mcp_initialized = False
        
        # トレースログ設定
        self.trace_logger = configure_trace_logging("s_expr_trace.jsonl")
    
    async def evaluate_s_expression(self, s_expr: str, context: Optional[Dict] = None, auto_retry: bool = True) -> Any:
        """
        S式を評価（自動再生成機能付き）
        
        Args:
            s_expr: S式文字列
            context: 評価コンテキスト
            auto_retry: 構文エラー時の自動再生成フラグ
            
        Returns:
            評価結果
        """
        max_retries = 3 if auto_retry else 1
        original_query = context.get("original_query", "") if context else ""
        
        for attempt in range(max_retries):
            # トレース開始
            entry_id = self.trace_logger.start_operation(
                operation="evaluate_s_expression",
                input_data={"s_expr": s_expr, "context": context}
            )
            
            try:
                parsed_expr = parse_s_expression(s_expr)
                
                if self.use_async:
                    result = await self.async_evaluator.evaluate_with_context(
                        parsed_expr, self.async_global_env, context or {}
                    )
                else:
                    result = self.evaluator.evaluate_with_context(
                        parsed_expr, self.global_env, context or {}
                    )
                
                # 成功時はトレースに記録して履歴に追加
                from .trace_logger import ExecutionMetadata, ProvenanceType
                self.trace_logger.end_operation(entry_id, result, ExecutionMetadata(
                    provenance=ProvenanceType.BUILTIN,
                    tool_called="s_expression_evaluator",
                    context={"attempt": attempt + 1, "success": True}
                ))
                
                self.add_to_history("evaluate", s_expr, result, True)
                return result
                
            except Exception as e:
                error_msg = str(e)
                print(f"[S式評価] 試行 {attempt + 1}/{max_retries}: エラー - {error_msg}")
                
                # エラーをトレースに記録
                from .trace_logger import ExecutionMetadata, ProvenanceType
                self.trace_logger.end_operation(entry_id, f"Error: {e}", ExecutionMetadata(
                    provenance=ProvenanceType.BUILTIN,
                    tool_called="s_expression_evaluator",
                    error=error_msg,
                    context={"attempt": attempt + 1, "success": False}
                ))
                
                # 自動再試行が有効で、元のクエリがあり、最後の試行でない場合
                if auto_retry and attempt < max_retries - 1 and original_query:
                    print(f"[S式評価] エラー内容をLLMに送信して再生成を試行します...")
                    
                    try:
                        # エラー全文をLLMに送って再生成
                        regenerated_expr = await self._regenerate_s_expression_with_full_error(
                            original_query, s_expr, error_msg, attempt + 1
                        )
                        
                        print(f"[S式評価] 再生成されたS式: {regenerated_expr}")
                        s_expr = regenerated_expr  # 次の試行で使用
                        continue
                        
                    except Exception as regen_error:
                        print(f"[S式評価] 再生成失敗: {regen_error}")
                        # 再生成に失敗した場合は元のエラーを継続
                
                # 最後の試行またはリトライ無効の場合
                if attempt == max_retries - 1:
                    self.add_to_history("evaluate", s_expr, f"Error: {e}", False)
                    raise
        
        # ここには到達しないはず
        raise RuntimeError("予期しないエラー")
    
    async def generate_s_expression(self, natural_language: str, max_retries: int = 3) -> str:
        """
        自然言語からS式を生成（自動再試行機能付き）
        
        Args:
            natural_language: 自然言語の指示
            max_retries: 最大再試行回数
            
        Returns:
            生成されたS式
        """
        for attempt in range(max_retries):
            try:
                prompt = f"""
以下の自然言語の指示をS式形式に変換してください。
利用可能な関数: search, calc, notify, math, par, seq, ask_user, collect_info

指示: {natural_language}

S式のみを出力してください（説明不要）。
必ず正しい括弧の対応と構文で記述してください。

例:
- "天気を調べて" → (search "天気")
- "2つの処理を並列実行" → (par (search "A") (search "B"))
- "順番に実行" → (seq (search "情報") (notify "完了"))
"""
                
                # LLMで生成（簡易実装）
                response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                generated_expr = response.content.strip()
                
                # 生成されたS式の構文チェック
                validation_result = self._validate_s_expression(generated_expr)
                
                if validation_result["valid"]:
                    # 正常な場合、履歴に追加して返す
                    self.add_to_history("generate", natural_language, generated_expr, True)
                    return generated_expr
                else:
                    # 構文エラーの場合、再試行
                    error_msg = validation_result["error"]
                    print(f"[S式生成] 試行 {attempt + 1}/{max_retries}: 構文エラー - {error_msg}")
                    
                    if attempt < max_retries - 1:
                        # 再生成プロンプトを改良
                        prompt = f"""
前回生成したS式「{generated_expr}」に構文エラーがありました。
エラー内容: {error_msg}

以下の指示を正しいS式形式で再生成してください:
指示: {natural_language}

重要事項:
1. 括弧の対応を正確に
2. 文字列は必ずダブルクォートで囲む
3. 利用可能関数: search, calc, notify, math, par, seq, ask_user, collect_info
4. S式のみを出力（説明文不要）

正しい例:
- (search "カレーの作り方")
- (seq (search "天気") (notify "検索完了"))
"""
                        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
                        generated_expr = response.content.strip()
                        continue
                    else:
                        # 最大試行回数に達した場合
                        fallback_expr = f'(notify "S式生成に失敗しました: {natural_language}")'
                        self.add_to_history("generate", natural_language, fallback_expr, False)
                        return fallback_expr
                        
            except Exception as e:
                print(f"[S式生成] 試行 {attempt + 1}/{max_retries}: 生成エラー - {e}")
                if attempt == max_retries - 1:
                    # 最後の試行でエラーの場合、フォールバック
                    fallback_expr = f'(notify "S式生成エラー: {str(e)}")'
                    self.add_to_history("generate", natural_language, fallback_expr, False)
                    return fallback_expr
        
        # ここには到達しないはずだが、安全のため
        fallback_expr = f'(notify "予期しないエラーが発生しました")'
        self.add_to_history("generate", natural_language, fallback_expr, False)
        return fallback_expr
    
    def _validate_s_expression(self, s_expr: str) -> Dict[str, Any]:
        """
        S式の構文チェック
        
        Args:
            s_expr: チェックするS式文字列
            
        Returns:
            {"valid": bool, "error": str, "parsed": Any}
        """
        try:
            # 基本的な括弧チェック
            if not s_expr.strip():
                return {"valid": False, "error": "S式が空です", "parsed": None}
            
            if not s_expr.strip().startswith('('):
                return {"valid": False, "error": "S式は '(' で始まる必要があります", "parsed": None}
            
            if not s_expr.strip().endswith(')'):
                return {"valid": False, "error": "S式は ')' で終わる必要があります", "parsed": None}
            
            # 括弧の対応チェック
            open_count = s_expr.count('(')
            close_count = s_expr.count(')')
            if open_count != close_count:
                return {"valid": False, "error": f"括弧の数が一致しません (開: {open_count}, 閉: {close_count})", "parsed": None}
            
            # パーサーでの詳細チェック
            parsed = parse_s_expression(s_expr)
            
            # 基本的な形式チェック
            if isinstance(parsed, list) and len(parsed) > 0:
                op = parsed[0]
                if not isinstance(op, str):
                    return {"valid": False, "error": "操作名は文字列である必要があります", "parsed": None}
                
                # 既知の操作かチェック
                known_ops = {'search', 'calc', 'notify', 'math', 'par', 'seq', 'ask_user', 'collect_info', 'let', 'if'}
                if op not in known_ops:
                    return {"valid": True, "error": f"未知の操作 '{op}' ですが、構文は正しいです", "parsed": parsed}
            
            return {"valid": True, "error": "", "parsed": parsed}
            
        except Exception as e:
            return {"valid": False, "error": f"パース エラー: {str(e)}", "parsed": None}
    
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
    
    async def _regenerate_s_expression_with_full_error(self, original_query: str, failed_expr: str, error_msg: str, attempt: int) -> str:
        """
        エラー全文をLLMに送ってS式を再生成（共通処理）
        
        Args:
            original_query: 元の自然言語クエリ
            failed_expr: 失敗したS式
            error_msg: エラーメッセージ全文
            attempt: 試行回数
            
        Returns:
            再生成されたS式
        """
        prompt = f"""
S式の実行でエラーが発生しました。エラー内容を分析して正しいS式に修正してください。

【元のクエリ】
{original_query}

【失敗したS式】
{failed_expr}

【エラーメッセージ全文】
{error_msg}

【修正指針】
- 括弧の対応を正確に（開いた括弧 "(" の数と閉じた括弧 ")" の数を同じに）
- 文字列は必ずダブルクォート（"）で囲む
- 利用可能関数: search, calc, notify, math, par, seq, ask_user, collect_info, let, if
- エラーメッセージに従って具体的な問題を修正

【正しいS式の例】
- 検索: (search "検索語")
- 順次実行: (seq (search "情報") (notify "完了"))
- 並列実行: (par (search "A") (search "B"))
- 計算: (calc "2+3")
- 通知: (notify "メッセージ")

【試行回数】
{attempt}/3回目の修正です。

修正されたS式のみを出力してください（説明や前置きは不要）。
"""
        
        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            regenerated_expr = response.content.strip()
            
            # 生成された内容から最初のS式を抽出（説明文が含まれている場合に備えて）
            regenerated_expr = self._extract_s_expression_from_response(regenerated_expr)
            
            return regenerated_expr
                
        except Exception as e:
            # LLM呼び出しエラーの場合、シンプルなフォールバックを生成
            print(f"[再生成] LLM呼び出しエラー: {e}")
            fallback_expr = f'(notify "元のクエリ: {original_query}")'
            return fallback_expr
    
    def _extract_s_expression_from_response(self, response: str) -> str:
        """
        LLMレスポンスからS式を抽出
        
        Args:
            response: LLMの回答全文
            
        Returns:
            抽出されたS式
        """
        lines = response.strip().split('\n')
        
        # 括弧で始まる最初の行を探す
        for line in lines:
            line = line.strip()
            if line.startswith('(') and line.endswith(')'):
                return line
        
        # 見つからない場合、括弧で始まる最初の部分を探す
        for line in lines:
            line = line.strip()
            if line.startswith('('):
                # 括弧の対応をチェックして補完
                open_count = line.count('(')
                close_count = line.count(')')
                if open_count > close_count:
                    # 不足分の括弧を追加
                    line += ')' * (open_count - close_count)
                return line
        
        # それでも見つからない場合、元のレスポンスをそのまま返す
        return response.strip()
    
    def parse_s_expression_safe(self, s_expr: str) -> Optional[Any]:
        """
        S式を安全にパース
        
        Args:
            s_expr: S式文字列
            
        Returns:
            パース結果（エラー時はNone）
        """
        try:
            return parse_s_expression(s_expr)
        except Exception:
            return None
    
    def add_to_history(self, operation: str, input_data: Any, output_data: Any, success: bool = True) -> None:
        """
        履歴に項目を追加
        
        Args:
            operation: 操作名
            input_data: 入力データ
            output_data: 出力データ
            success: 成功フラグ
        """
        self.session_history.append({
            "timestamp": datetime.now().timestamp(),
            "operation": operation,
            "input": input_data,
            "output": output_data,
            "success": success
        })
    
    def get_session_history(self) -> List[Dict[str, Any]]:
        """
        セッション履歴を取得
        
        Returns:
            セッション履歴のコピー
        """
        return self.session_history.copy()
    
    def clear_history(self) -> None:
        """履歴をクリア"""
        self.session_history.clear()
    
    def toggle_execution_mode(self) -> str:
        """
        実行モードを切り替え
        
        Returns:
            新しいモード名
        """
        self.use_async = not self.use_async
        
        # 新しいモードに対応する評価器を初期化
        if self.use_async:
            if not hasattr(self, 'async_evaluator'):
                self.async_evaluator = AsyncContextualEvaluator(self.llm_base_url, self.model_name)
                self.async_global_env = AsyncEnvironment()
        else:
            if not hasattr(self, 'evaluator'):
                self.evaluator = ContextualEvaluator(self.llm_base_url, self.model_name)
                self.global_env = Environment()
        
        new_mode = "async" if self.use_async else "sync"
        self.add_to_history("toggle_mode", self.use_async, new_mode, True)
        
        return new_mode
    
    async def run_benchmark(self, test_expressions: List[str] = None) -> Dict[str, Any]:
        """
        ベンチマークを実行
        
        Args:
            test_expressions: テスト用S式リスト
            
        Returns:
            ベンチマーク結果
        """
        if test_expressions is None:
            test_expressions = [
                "(calc \"10*10\")",
                "(calc \"20+20\")",
                "(calc \"30-10\")"
            ]
        
        # 同期実行ベンチマーク
        original_mode = self.use_async
        self.use_async = False
        
        sync_start = datetime.now()
        sync_results = []
        
        for expr in test_expressions:
            try:
                result = await self.evaluate_s_expression(expr)
                sync_results.append(result)
            except Exception as e:
                sync_results.append(f"Error: {e}")
        
        sync_end = datetime.now()
        sync_duration = (sync_end - sync_start).total_seconds() * 1000
        
        # 非同期実行ベンチマーク
        self.use_async = True
        
        async_start = datetime.now()
        
        tasks = [self.evaluate_s_expression(expr) for expr in test_expressions]
        try:
            async_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            async_results = [f"Error: {e}"] * len(test_expressions)
        
        async_end = datetime.now()
        async_duration = (async_end - async_start).total_seconds() * 1000
        
        # 元のモードに戻す
        self.use_async = original_mode
        
        # 結果をまとめる
        improvement = ((sync_duration - async_duration) / sync_duration * 100) if sync_duration > 0 else 0
        
        benchmark_result = {
            "sync_duration_ms": sync_duration,
            "async_duration_ms": async_duration,
            "improvement_percent": improvement,
            "test_count": len(test_expressions),
            "sync_results": sync_results,
            "async_results": async_results
        }
        
        self.add_to_history("benchmark", test_expressions, benchmark_result, True)
        
        return benchmark_result
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """
        利用可能ツール一覧を取得
        
        Returns:
            ツール情報リスト
        """
        builtin_tools = [
            {"name": "calc", "description": "数式計算", "type": "builtin", "status": "available"},
            {"name": "notify", "description": "通知表示", "type": "builtin", "status": "available"},
            {"name": "math", "description": "記号数学計算", "type": "builtin", "status": "available"},
            {"name": "par", "description": "並列実行", "type": "builtin", "status": "available"},
            {"name": "seq", "description": "順次実行", "type": "builtin", "status": "available"},
        ]
        
        mcp_tools = []
        if self.mcp_initialized:
            mcp_tools.append({
                "name": "search", 
                "description": "Brave検索", 
                "type": "mcp", 
                "status": "available"
            })
        
        return builtin_tools + mcp_tools
    
    async def test_tools(self) -> Dict[str, Any]:
        """
        ツールテストを実行
        
        Returns:
            テスト結果
        """
        test_results = {}
        
        # 内蔵ツールテスト
        test_cases = [
            ("calc", "(calc \"2+2\")", 4),
            ("notify", "(notify \"テスト通知\")", None),
            ("math", "(math \"x + 2\" \"x=3\")", 5)
        ]
        
        for tool_name, test_expr, expected in test_cases:
            try:
                result = await self.evaluate_s_expression(test_expr)
                if expected is not None:
                    success = result == expected
                else:
                    success = True  # notify は実行できれば成功
                
                test_results[tool_name] = {
                    "status": "success" if success else "failed",
                    "result": result,
                    "expected": expected
                }
            except Exception as e:
                test_results[tool_name] = {
                    "status": "error",
                    "error": str(e),
                    "expected": expected
                }
        
        self.add_to_history("test_tools", test_cases, test_results, True)
        
        return test_results
    
    async def init_mcp_system(self) -> bool:
        """
        MCPシステムを初期化（統一ツール実行サービス経由）
        
        Returns:
            初期化成功フラグ
        """
        try:
            success = await self.tool_executor.initialize_mcp()
            self.mcp_initialized = success
            
            if success:
                self.add_to_history("init_mcp", None, "MCP initialized successfully", True)
            else:
                self.add_to_history("init_mcp", None, "MCP init failed", False)
                
            return success
            
        except Exception as e:
            self.add_to_history("init_mcp", None, f"MCP init failed: {e}", False)
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        システム状態を取得
        
        Returns:
            システム状態情報
        """
        return {
            "execution_mode": "async" if self.use_async else "sync",
            "mcp_status": "initialized" if self.mcp_initialized else "not_initialized",
            "session_count": len(self.session_history),
            "available_tools": len(self.get_available_tools()),
            "llm_model": self.model_name,
            "llm_base_url": self.llm_base_url
        }