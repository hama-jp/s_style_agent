"""
API用のPydanticモデル定義
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ExecutionMode(str, Enum):
    """実行モード"""
    SYNC = "sync"
    ASYNC = "async"


class SExpressionRequest(BaseModel):
    """S式実行リクエスト"""
    expression: str = Field(..., description="実行するS式")
    context: Optional[str] = Field(None, description="実行コンテキスト")
    mode: ExecutionMode = Field(ExecutionMode.ASYNC, description="実行モード")
    is_admin: bool = Field(False, description="管理者権限フラグ")


class SExpressionResponse(BaseModel):
    """S式実行レスポンス"""
    success: bool = Field(..., description="実行成功フラグ")
    result: Any = Field(None, description="実行結果")
    error: Optional[str] = Field(None, description="エラーメッセージ")
    execution_time: float = Field(..., description="実行時間（秒）")
    mode: ExecutionMode = Field(..., description="使用された実行モード")


class ParseRequest(BaseModel):
    """S式パースリクエスト"""
    expression: str = Field(..., description="パースするS式")


class ParseResponse(BaseModel):
    """S式パースレスポンス"""
    success: bool = Field(..., description="パース成功フラグ")
    parsed: Any = Field(None, description="パース結果")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class GenerateRequest(BaseModel):
    """S式生成リクエスト"""
    task: str = Field(..., description="実行したいタスクの自然言語記述")
    llm_base_url: Optional[str] = Field(None, description="LLMのベースURL")
    model_name: Optional[str] = Field(None, description="使用するモデル名")


class GenerateResponse(BaseModel):
    """S式生成レスポンス"""
    success: bool = Field(..., description="生成成功フラグ")
    expression: Optional[str] = Field(None, description="生成されたS式")
    error: Optional[str] = Field(None, description="エラーメッセージ")


class SystemStatus(BaseModel):
    """システムステータス"""
    version: str = Field(..., description="システムバージョン")
    available_tools: List[str] = Field(..., description="利用可能ツール一覧")
    supported_modes: List[ExecutionMode] = Field(..., description="サポートされた実行モード")
    active_sessions: int = Field(..., description="アクティブセッション数")


class WebSocketMessage(BaseModel):
    """WebSocketメッセージ"""
    type: str = Field(..., description="メッセージタイプ")
    data: Dict[str, Any] = Field(..., description="メッセージデータ")
    session_id: Optional[str] = Field(None, description="セッションID")


class SessionInfo(BaseModel):
    """セッション情報"""
    session_id: str = Field(..., description="セッションID")
    created_at: str = Field(..., description="作成日時")
    last_activity: str = Field(..., description="最終活動日時")
    mode: ExecutionMode = Field(..., description="実行モード")
    is_admin: bool = Field(..., description="管理者権限フラグ")