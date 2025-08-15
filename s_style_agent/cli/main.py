"""
メインCLIインターフェース

ユーザーがS式の生成・編集・実行を制御できるインタラクティブCLI
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from pathlib import Path

from langchain_openai import ChatOpenAI
from langsmith import traceable

from ..core.parser import parse_s_expression, SExpressionParseError
from ..core.evaluator import ContextualEvaluator, Environment
from ..tools.builtin_tools import register_builtin_tools
from ..tools.base import global_registry


class SStyleAgentCLI:
    """S式エージェントCLI"""
    
    def __init__(self, llm_base_url: str = "http://192.168.79.1:1234/v1",
                 model_name: str = "unsloth/gpt-oss-120b"):
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            api_key="dummy",
            model=model_name,
            temperature=0.3
        )
        self.evaluator = ContextualEvaluator(llm_base_url, model_name)
        self.global_env = Environment()
        self.session_history: list = []
        
        # 組み込みツールを登録
        register_builtin_tools()
        
        print("S式エージェントシステムへようこそ！")
        print("利用可能コマンド:")
        print("  /help     - ヘルプを表示")
        print("  /generate - LLMでS式を生成")
        print("  /parse    - S式をパース")
        print("  /execute  - S式を実行")
        print("  /history  - セッション履歴を表示")
        print("  /tools    - 利用可能ツール一覧")
        print("  /exit     - 終了")
        print()
    
    def print_help(self):
        """ヘルプを表示"""
        print("""
S式エージェントシステム ヘルプ

■ 基本的な使い方
1. 自然言語でタスクを入力
2. LLMがS式を生成
3. 生成されたS式を確認・編集
4. S式を実行

■ コマンド一覧
/help      - このヘルプを表示
/generate  - LLMでS式を生成
/parse     - S式の構文をチェック
/execute   - S式を実行
/history   - セッション履歴を表示
/tools     - 利用可能ツール一覧
/exit      - システムを終了

■ S式の構文例
(seq step1 step2)           - 順次実行
(par stepA stepB)           - 並列実行
(if cond then else)         - 条件分岐
(let ((var val)) body)      - 変数束縛
(notify "message")          - 通知
(search "query")            - 検索
(calc "expression")         - 計算
(db-query "query")          - データベースクエリ

■ 使用例
ユーザー: 今日の天気を調べて教えて
システム: (seq (search "今日の天気") (notify "天気情報をお伝えします"))
""")
    
    @traceable(name="generate_s_expression")
    async def generate_s_expression(self, user_input: str) -> str:
        """LLMでS式を生成"""
        tools_info = "\n".join([
            f"- ({schema.name} {' '.join([p.name for p in schema.parameters])}): {schema.description}"
            for schema in global_registry.get_schemas()
        ])
        
        prompt = f"""あなたはS式を生成するエージェントです。ユーザーの要求をS式で表現してください。

利用可能な関数:
- (seq step1 step2 ...): 順次実行
- (par stepA stepB ...): 並列実行
- (if cond then else): 条件分岐
- (let ((var expr) ...) body): 変数束縛

利用可能なツール:
{tools_info}

ユーザーの要求: {user_input}

適切なS式を生成してください。S式のみを返してください。余計な説明は不要です。"""

        try:
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            s_expression = response.content.strip()
            
            # 前後の ```やコードブロック記号を除去
            if s_expression.startswith("```"):
                lines = s_expression.split("\n")
                s_expression = "\n".join(lines[1:-1])
            
            return s_expression
        except Exception as e:
            return f"(notify \"S式生成エラー: {str(e)}\")"
    
    def parse_s_expression_safe(self, s_expr: str) -> tuple[bool, Any, str]:
        """S式を安全にパース"""
        try:
            parsed = parse_s_expression(s_expr)
            return True, parsed, ""
        except SExpressionParseError as e:
            return False, None, str(e)
    
    async def execute_s_expression(self, s_expr: str, context: str = "") -> Any:
        """S式を実行"""
        try:
            # まず既存の評価エンジンで実行
            self.evaluator.set_task_context(context)
            parsed_expr = parse_s_expression(s_expr)
            result = self.evaluator.evaluate_with_context(parsed_expr, self.global_env)
            
            # セッション履歴に記録
            self.session_history.append({
                "input": s_expr,
                "context": context,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return result
        except Exception as e:
            error_msg = f"実行エラー: {str(e)}"
            self.session_history.append({
                "input": s_expr,
                "context": context,
                "error": error_msg,
                "timestamp": asyncio.get_event_loop().time()
            })
            return error_msg
    
    def show_history(self):
        """セッション履歴を表示"""
        if not self.session_history:
            print("履歴がありません。")
            return
        
        print("\\n=== セッション履歴 ===")
        for i, entry in enumerate(self.session_history[-10:], 1):  # 最新10件
            print(f"\\n{i}. S式: {entry['input']}")
            if 'result' in entry:
                print(f"   結果: {entry['result']}")
            if 'error' in entry:
                print(f"   エラー: {entry['error']}")
    
    def show_tools(self):
        """利用可能ツール一覧を表示"""
        schemas = global_registry.get_schemas()
        if not schemas:
            print("利用可能なツールがありません。")
            return
        
        print("\\n=== 利用可能ツール ===")
        for schema in schemas:
            params = ", ".join([p.name for p in schema.parameters])
            print(f"- {schema.name}({params}): {schema.description}")
    
    async def run(self):
        """メインループ"""
        while True:
            try:
                user_input = input("\\n> ").strip()
                
                if not user_input:
                    continue
                
                # コマンド処理
                if user_input.startswith("/"):
                    command = user_input[1:].lower()
                    
                    if command == "help":
                        self.print_help()
                    elif command == "exit":
                        print("S式エージェントを終了します。")
                        break
                    elif command == "history":
                        self.show_history()
                    elif command == "tools":
                        self.show_tools()
                    elif command == "generate":
                        task = input("タスクを入力してください: ").strip()
                        if task:
                            print("\\nS式を生成中...")
                            s_expr = await self.generate_s_expression(task)
                            print(f"生成されたS式: {s_expr}")
                            
                            # パース確認
                            success, parsed, error = self.parse_s_expression_safe(s_expr)
                            if success:
                                print(f"パース結果: {parsed}")
                                exec_choice = input("\\n実行しますか？ (y/n): ").strip().lower()
                                if exec_choice == 'y':
                                    print("\\n実行中...")
                                    result = await self.execute_s_expression(s_expr, task)
                                    print(f"実行結果: {result}")
                            else:
                                print(f"パースエラー: {error}")
                    elif command == "parse":
                        s_expr = input("S式を入力してください: ").strip()
                        if s_expr:
                            success, parsed, error = self.parse_s_expression_safe(s_expr)
                            if success:
                                print(f"パース成功: {parsed}")
                            else:
                                print(f"パースエラー: {error}")
                    elif command == "execute":
                        s_expr = input("実行するS式を入力してください: ").strip()
                        if s_expr:
                            context = input("文脈（オプション）: ").strip()
                            print("\\n実行中...")
                            result = await self.execute_s_expression(s_expr, context)
                            print(f"実行結果: {result}")
                    else:
                        print(f"不明なコマンド: {command}")
                        print("利用可能コマンド: /help, /generate, /parse, /execute, /history, /tools, /exit")
                
                # 直接S式入力の場合
                elif user_input.startswith("("):
                    print("S式を実行中...")
                    result = await self.execute_s_expression(user_input)
                    print(f"実行結果: {result}")
                
                # 自然言語入力の場合
                else:
                    print("S式を生成中...")
                    s_expr = await self.generate_s_expression(user_input)
                    print(f"生成されたS式: {s_expr}")
                    
                    # パース確認
                    success, parsed, error = self.parse_s_expression_safe(s_expr)
                    if success:
                        print(f"パース結果: {parsed}")
                        
                        # ユーザーに実行前確認
                        exec_choice = input("\\n実行しますか？ (y/n/e=編集): ").strip().lower()
                        
                        if exec_choice == 'y':
                            print("\\n実行中...")
                            result = await self.execute_s_expression(s_expr, user_input)
                            print(f"実行結果: {result}")
                        elif exec_choice == 'e':
                            edited_expr = input(f"S式を編集してください:\\n{s_expr}\\n> ").strip()
                            if edited_expr:
                                print("\\n編集されたS式を実行中...")
                                result = await self.execute_s_expression(edited_expr, user_input)
                                print(f"実行結果: {result}")
                    else:
                        print(f"パースエラー: {error}")
                        
            except KeyboardInterrupt:
                print("\\n\\nS式エージェントを終了します。")
                break
            except Exception as e:
                print(f"エラーが発生しました: {str(e)}")


async def main():
    """メイン関数"""
    cli = SStyleAgentCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())