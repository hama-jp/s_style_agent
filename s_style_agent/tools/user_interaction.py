"""
ユーザーインタラクションツール

Human-in-the-loop処理を提供する包括的なツール群
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from langsmith import traceable

from .base import BaseTool, ToolSchema, ToolParameter, ToolResult


class AskUserTool(BaseTool):
    """ユーザーに質問して回答を取得するツール"""
    
    def __init__(self):
        super().__init__(
            "ask_user",
            "ユーザーに質問して回答を取得（Human-in-the-loop処理）"
        )
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="question",
                    type="string",
                    description="ユーザーへの質問",
                    required=True
                ),
                ToolParameter(
                    name="variable_name",
                    type="string",
                    description="回答を格納する変数名",
                    required=True
                ),
                ToolParameter(
                    name="question_type",
                    type="string",
                    description="質問タイプ: required（必須）, optional（任意）, choice（選択）",
                    required=False
                ),
                ToolParameter(
                    name="choices",
                    type="string",
                    description="選択肢（カンマ区切り、choice タイプの場合）",
                    required=False
                ),
                ToolParameter(
                    name="default_value",
                    type="string",
                    description="デフォルト値",
                    required=False
                )
            ]
        )
    
    @traceable(name="ask_user_execute")
    async def execute(self, **kwargs) -> ToolResult:
        question = kwargs.get("question", "")
        variable_name = kwargs.get("variable_name", "user_input")
        question_type = kwargs.get("question_type", "required")
        choices = kwargs.get("choices", "")
        default_value = kwargs.get("default_value", "")
        
        if not question:
            return ToolResult(
                success=False,
                result=None,
                error="質問が指定されていません",
                metadata={"tool": "ask_user", **kwargs}
            )
        
        try:
            # 質問の表示形式を決定
            if question_type == "choice" and choices:
                choice_list = [c.strip() for c in choices.split(",")]
                choice_text = " / ".join([f"{i+1}. {c}" for i, c in enumerate(choice_list)])
                display_question = f"{question}\n{choice_text}\n選択してください"
            elif default_value:
                display_question = f"{question} (デフォルト: {default_value})"
            else:
                display_question = question
            
            # 必須フラグの表示
            if question_type == "required":
                display_question += " *"
            
            print(f"\n[HUMAN INPUT REQUIRED]")
            print(f"質問: {display_question}")
            
            # ユーザー入力を取得
            loop = asyncio.get_event_loop()
            
            def get_user_input():
                return input("回答: ").strip()
            
            user_response = await loop.run_in_executor(None, get_user_input)
            
            # 入力の検証と処理
            if not user_response and question_type == "required":
                return ToolResult(
                    success=False,
                    result=None,
                    error="必須項目への回答が必要です",
                    metadata={"tool": "ask_user", **kwargs}
                )
            
            # デフォルト値の適用
            if not user_response and default_value:
                user_response = default_value
            
            # 選択肢の処理
            if question_type == "choice" and choices:
                choice_list = [c.strip() for c in choices.split(",")]
                try:
                    if user_response.isdigit():
                        choice_index = int(user_response) - 1
                        if 0 <= choice_index < len(choice_list):
                            user_response = choice_list[choice_index]
                        else:
                            return ToolResult(
                                success=False,
                                result=None,
                                error=f"選択肢は1-{len(choice_list)}の範囲で入力してください",
                                metadata={"tool": "ask_user", **kwargs}
                            )
                    elif user_response not in choice_list:
                        return ToolResult(
                            success=False,
                            result=None,
                            error=f"有効な選択肢を選んでください: {', '.join(choice_list)}",
                            metadata={"tool": "ask_user", **kwargs}
                        )
                except ValueError:
                    pass  # 数字でない場合は文字列として処理
            
            print(f"✓ {variable_name} = '{user_response}'")
            
            return ToolResult(
                success=True,
                result=user_response,
                metadata={
                    "tool": "ask_user",
                    "variable_name": variable_name,
                    "question_type": question_type,
                    **kwargs
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"ユーザー入力エラー: {str(e)}",
                metadata={"tool": "ask_user", **kwargs}
            )


class CollectInfoTool(BaseTool):
    """複数の情報を効率的に収集するツール"""
    
    def __init__(self):
        super().__init__(
            "collect_info",
            "複数の情報を順次収集してコンテキストに保存"
        )
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="questions",
                    type="string",
                    description="質問と変数名のペア（JSON形式）",
                    required=True
                )
            ]
        )
    
    @traceable(name="collect_info_execute")
    async def execute(self, **kwargs) -> ToolResult:
        questions_str = kwargs.get("questions", "")
        
        if not questions_str:
            return ToolResult(
                success=False,
                result=None,
                error="質問が指定されていません",
                metadata={"tool": "collect_info", **kwargs}
            )
        
        try:
            import json
            questions = json.loads(questions_str)
            
            collected_data = {}
            ask_tool = AskUserTool()
            
            print(f"\n[情報収集を開始します - {len(questions)}項目]")
            
            for i, question_data in enumerate(questions, 1):
                question = question_data.get("question", "")
                variable_name = question_data.get("variable", f"item_{i}")
                question_type = question_data.get("type", "required")
                
                print(f"\n({i}/{len(questions)})")
                
                result = await ask_tool.execute(
                    question=question,
                    variable_name=variable_name,
                    question_type=question_type,
                    choices=question_data.get("choices", ""),
                    default_value=question_data.get("default", "")
                )
                
                if result.success:
                    collected_data[variable_name] = result.result
                else:
                    return ToolResult(
                        success=False,
                        result=None,
                        error=f"情報収集中にエラー: {result.error}",
                        metadata={"tool": "collect_info", **kwargs}
                    )
            
            print(f"\n✓ 情報収集完了: {len(collected_data)}項目")
            
            return ToolResult(
                success=True,
                result=collected_data,
                metadata={
                    "tool": "collect_info",
                    "collected_count": len(collected_data),
                    **kwargs
                }
            )
            
        except json.JSONDecodeError:
            return ToolResult(
                success=False,
                result=None,
                error="質問データのJSON形式が正しくありません",
                metadata={"tool": "collect_info", **kwargs}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"情報収集エラー: {str(e)}",
                metadata={"tool": "collect_info", **kwargs}
            )


class ConditionalAskTool(BaseTool):
    """条件に応じてユーザーに質問するツール"""
    
    def __init__(self):
        super().__init__(
            "conditional_ask",
            "条件を満たす場合のみユーザーに質問"
        )
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="condition",
                    type="string",
                    description="質問する条件",
                    required=True
                ),
                ToolParameter(
                    name="question",
                    type="string",
                    description="ユーザーへの質問",
                    required=True
                ),
                ToolParameter(
                    name="variable_name",
                    type="string",
                    description="回答を格納する変数名",
                    required=True
                )
            ]
        )
    
    @traceable(name="conditional_ask_execute")
    async def execute(self, **kwargs) -> ToolResult:
        condition = kwargs.get("condition", "")
        question = kwargs.get("question", "")
        variable_name = kwargs.get("variable_name", "")
        
        try:
            # 簡単な条件評価（実際の実装では、より複雑な条件評価が必要）
            should_ask = True  # 仮実装：常に質問する
            
            if should_ask:
                ask_tool = AskUserTool()
                result = await ask_tool.execute(
                    question=question,
                    variable_name=variable_name,
                    question_type="optional"
                )
                return result
            else:
                return ToolResult(
                    success=True,
                    result=None,
                    metadata={
                        "tool": "conditional_ask",
                        "condition_met": False,
                        **kwargs
                    }
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"条件付き質問エラー: {str(e)}",
                metadata={"tool": "conditional_ask", **kwargs}
            )


class SuggestAndConfirmTool(BaseTool):
    """エージェントの提案をユーザーに確認するツール"""
    
    def __init__(self):
        super().__init__(
            "suggest_and_confirm",
            "エージェントの推測・提案をユーザーに確認"
        )
    
    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="suggestion",
                    type="string",
                    description="エージェントの提案内容",
                    required=True
                ),
                ToolParameter(
                    name="variable_name",
                    type="string",
                    description="回答を格納する変数名",
                    required=True
                ),
                ToolParameter(
                    name="alternatives",
                    type="string",
                    description="代替案（カンマ区切り）",
                    required=False
                )
            ]
        )
    
    @traceable(name="suggest_and_confirm_execute")
    async def execute(self, **kwargs) -> ToolResult:
        suggestion = kwargs.get("suggestion", "")
        variable_name = kwargs.get("variable_name", "suggestion")
        alternatives = kwargs.get("alternatives", "")
        
        if not suggestion:
            return ToolResult(
                success=False,
                result=None,
                error="提案内容が指定されていません",
                metadata={"tool": "suggest_and_confirm", **kwargs}
            )
        
        try:
            print(f"\n[AGENT SUGGESTION]")
            print(f"提案: {suggestion}")
            
            if alternatives:
                alt_list = [a.strip() for a in alternatives.split(",")]
                print(f"他の選択肢: {', '.join(alt_list)}")
                
                confirm_text = "この提案でよろしいですか？ (y/n/番号): "
                for i, alt in enumerate(alt_list, 1):
                    print(f"  {i}. {alt}")
            else:
                confirm_text = "この提案でよろしいですか？ (y/n): "
            
            # ユーザー確認を取得
            loop = asyncio.get_event_loop()
            
            def get_user_input():
                return input(confirm_text).strip().lower()
            
            user_response = await loop.run_in_executor(None, get_user_input)
            
            if user_response == 'y' or user_response == 'yes':
                result = suggestion
                print(f"✓ 採用: {suggestion}")
            elif user_response == 'n' or user_response == 'no':
                new_input = input("代替案を入力してください: ").strip()
                result = new_input if new_input else suggestion
                print(f"✓ 変更: {result}")
            elif alternatives and user_response.isdigit():
                choice_index = int(user_response) - 1
                alt_list = [a.strip() for a in alternatives.split(",")]
                if 0 <= choice_index < len(alt_list):
                    result = alt_list[choice_index]
                    print(f"✓ 選択: {result}")
                else:
                    result = suggestion
                    print(f"✓ 無効な選択、デフォルト使用: {suggestion}")
            else:
                result = suggestion
                print(f"✓ デフォルト使用: {suggestion}")
            
            return ToolResult(
                success=True,
                result=result,
                metadata={
                    "tool": "suggest_and_confirm",
                    "variable_name": variable_name,
                    "original_suggestion": suggestion,
                    **kwargs
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result=None,
                error=f"提案確認エラー: {str(e)}",
                metadata={"tool": "suggest_and_confirm", **kwargs}
            )