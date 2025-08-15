"""
FastAPI REST/WebSocket APIサーバー
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, List
import uuid
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from langsmith import traceable

from .models import (
    SExpressionRequest, SExpressionResponse, ParseRequest, ParseResponse,
    GenerateRequest, GenerateResponse, SystemStatus, WebSocketMessage,
    SessionInfo, ExecutionMode
)
from ..core.parser import parse_s_expression, SExpressionParseError
from ..core.evaluator import ContextualEvaluator, Environment
from ..core.async_evaluator import AsyncContextualEvaluator, AsyncEnvironment
from ..tools.base import global_registry
from ..cli.main import SStyleAgentCLI


class ConnectionManager:
    """WebSocket接続管理"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_info: Dict[str, SessionInfo] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, mode: ExecutionMode = ExecutionMode.ASYNC, is_admin: bool = False):
        """新しい接続を追加"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_info[session_id] = SessionInfo(
            session_id=session_id,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            mode=mode,
            is_admin=is_admin
        )
    
    def disconnect(self, session_id: str):
        """接続を削除"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_info:
            del self.session_info[session_id]
    
    async def send_personal_message(self, message: str, session_id: str):
        """特定のセッションにメッセージ送信"""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)
    
    async def broadcast(self, message: str):
        """全接続にブロードキャスト"""
        for connection in self.active_connections.values():
            await connection.send_text(message)
    
    def update_activity(self, session_id: str):
        """セッションの最終活動時刻を更新"""
        if session_id in self.session_info:
            self.session_info[session_id].last_activity = datetime.now().isoformat()


# FastAPIアプリケーションを作成
app = FastAPI(
    title="S式エージェントAPI",
    description="S式ベースの説明可能なエージェントシステム",
    version="0.1.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket接続管理
manager = ConnectionManager()

# グローバル評価器
sync_evaluator = ContextualEvaluator()
async_evaluator = AsyncContextualEvaluator()
sync_env = Environment()
async_env = AsyncEnvironment()


@app.get("/", summary="ヘルスチェック")
async def root():
    """APIのヘルスチェック"""
    return {"message": "S式エージェントAPI", "status": "healthy"}


@app.get("/status", response_model=SystemStatus, summary="システムステータス")
async def get_status():
    """システムの現在のステータスを取得"""
    return SystemStatus(
        version="0.1.0",
        available_tools=[schema.name for schema in global_registry.get_schemas()],
        supported_modes=[ExecutionMode.SYNC, ExecutionMode.ASYNC],
        active_sessions=len(manager.active_connections)
    )


@app.post("/parse", response_model=ParseResponse, summary="S式パース")
@traceable(name="api_parse_s_expression")
async def parse_s_expression_endpoint(request: ParseRequest):
    """S式をパースして構造を返す"""
    try:
        parsed = parse_s_expression(request.expression)
        return ParseResponse(success=True, parsed=parsed)
    except SExpressionParseError as e:
        return ParseResponse(success=False, error=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.post("/execute", response_model=SExpressionResponse, summary="S式実行")
@traceable(name="api_execute_s_expression")
async def execute_s_expression_endpoint(request: SExpressionRequest):
    """S式を実行して結果を返す"""
    start_time = time.time()
    
    try:
        # S式をパース
        parsed_expr = parse_s_expression(request.expression)
        
        # 実行モードに応じて評価
        if request.mode == ExecutionMode.ASYNC:
            if request.context:
                async_evaluator.set_task_context(request.context)
            async_evaluator.is_admin = request.is_admin
            result = await async_evaluator.evaluate_with_context(parsed_expr, async_env)
        else:
            if request.context:
                sync_evaluator.set_task_context(request.context)
            sync_evaluator.is_admin = request.is_admin
            result = sync_evaluator.evaluate_with_context(parsed_expr, sync_env)
        
        execution_time = time.time() - start_time
        
        return SExpressionResponse(
            success=True,
            result=result,
            execution_time=execution_time,
            mode=request.mode
        )
    
    except SExpressionParseError as e:
        execution_time = time.time() - start_time
        return SExpressionResponse(
            success=False,
            error=f"Parse error: {str(e)}",
            execution_time=execution_time,
            mode=request.mode
        )
    except Exception as e:
        execution_time = time.time() - start_time
        return SExpressionResponse(
            success=False,
            error=f"Execution error: {str(e)}",
            execution_time=execution_time,
            mode=request.mode
        )


@app.post("/generate", response_model=GenerateResponse, summary="S式生成")
@traceable(name="api_generate_s_expression")
async def generate_s_expression_endpoint(request: GenerateRequest):
    """自然言語からS式を生成"""
    try:
        # CLIのS式生成機能を利用
        cli = SStyleAgentCLI(
            llm_base_url=request.llm_base_url or "http://192.168.79.1:1234/v1",
            model_name=request.model_name or "unsloth/gpt-oss-120b"
        )
        
        expression = await cli.generate_s_expression(request.task)
        
        return GenerateResponse(success=True, expression=expression)
    
    except Exception as e:
        return GenerateResponse(success=False, error=str(e))


@app.get("/sessions", response_model=List[SessionInfo], summary="アクティブセッション一覧")
async def get_active_sessions():
    """現在のアクティブセッション一覧を取得"""
    return list(manager.session_info.values())


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocketエンドポイント"""
    await manager.connect(websocket, session_id)
    
    # 接続確認メッセージ
    welcome_msg = WebSocketMessage(
        type="connection",
        data={"message": f"WebSocket connected: {session_id}", "session_id": session_id}
    )
    await manager.send_personal_message(welcome_msg.model_dump_json(), session_id)
    
    try:
        while True:
            # メッセージ受信
            data = await websocket.receive_text()
            manager.update_activity(session_id)
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "unknown")
                
                if message_type == "execute":
                    # S式実行リクエスト
                    expr_data = message.get("data", {})
                    request = SExpressionRequest(**expr_data)
                    
                    # 実行
                    start_time = time.time()
                    try:
                        parsed_expr = parse_s_expression(request.expression)
                        
                        if request.mode == ExecutionMode.ASYNC:
                            if request.context:
                                async_evaluator.set_task_context(request.context)
                            async_evaluator.is_admin = request.is_admin
                            result = await async_evaluator.evaluate_with_context(parsed_expr, async_env)
                        else:
                            if request.context:
                                sync_evaluator.set_task_context(request.context)
                            sync_evaluator.is_admin = request.is_admin
                            result = sync_evaluator.evaluate_with_context(parsed_expr, sync_env)
                        
                        execution_time = time.time() - start_time
                        
                        response = WebSocketMessage(
                            type="result",
                            data={
                                "success": True,
                                "result": result,
                                "execution_time": execution_time,
                                "mode": request.mode.value
                            },
                            session_id=session_id
                        )
                    
                    except Exception as e:
                        execution_time = time.time() - start_time
                        response = WebSocketMessage(
                            type="result",
                            data={
                                "success": False,
                                "error": str(e),
                                "execution_time": execution_time,
                                "mode": request.mode.value
                            },
                            session_id=session_id
                        )
                    
                    await manager.send_personal_message(response.model_dump_json(), session_id)
                
                elif message_type == "ping":
                    # Pingリクエスト
                    pong = WebSocketMessage(
                        type="pong",
                        data={"timestamp": datetime.now().isoformat()},
                        session_id=session_id
                    )
                    await manager.send_personal_message(pong.model_dump_json(), session_id)
                
                else:
                    # 不明なメッセージタイプ
                    error_msg = WebSocketMessage(
                        type="error",
                        data={"message": f"Unknown message type: {message_type}"},
                        session_id=session_id
                    )
                    await manager.send_personal_message(error_msg.model_dump_json(), session_id)
            
            except json.JSONDecodeError:
                error_msg = WebSocketMessage(
                    type="error",
                    data={"message": "Invalid JSON format"},
                    session_id=session_id
                )
                await manager.send_personal_message(error_msg.model_dump_json(), session_id)
            
            except Exception as e:
                error_msg = WebSocketMessage(
                    type="error",
                    data={"message": f"Processing error: {str(e)}"},
                    session_id=session_id
                )
                await manager.send_personal_message(error_msg.model_dump_json(), session_id)
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket disconnected: {session_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)