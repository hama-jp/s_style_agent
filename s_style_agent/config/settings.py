"""
設定管理

システム設定とLLM接続設定
"""

import os
from typing import Optional
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM設定"""
    base_url: str = "http://192.168.79.1:1234/v1"
    model_name: str = "unsloth/gpt-oss-120b"
    api_key: str = "dummy"
    temperature: float = 0.3
    max_tokens: Optional[int] = None


class SystemConfig(BaseModel):
    """システム設定"""
    debug: bool = False
    trace_enabled: bool = True
    langsmith_project: str = "s-style-agent"
    session_history_limit: int = 100


class Settings:
    """設定管理クラス"""
    
    def __init__(self):
        self.llm = LLMConfig()
        self.system = SystemConfig()
        
        # 環境変数から設定を読み込み
        self._load_from_env()
    
    def _load_from_env(self):
        """環境変数から設定を読み込み"""
        # LLM設定
        if os.getenv("LLM_BASE_URL"):
            self.llm.base_url = os.getenv("LLM_BASE_URL")
        if os.getenv("LLM_MODEL_NAME"):
            self.llm.model_name = os.getenv("LLM_MODEL_NAME")
        if os.getenv("LLM_API_KEY"):
            self.llm.api_key = os.getenv("LLM_API_KEY")
        if os.getenv("LLM_TEMPERATURE"):
            self.llm.temperature = float(os.getenv("LLM_TEMPERATURE"))
        
        # システム設定
        if os.getenv("DEBUG"):
            self.system.debug = os.getenv("DEBUG").lower() in ("true", "1", "yes")
        if os.getenv("LANGSMITH_PROJECT"):
            self.system.langsmith_project = os.getenv("LANGSMITH_PROJECT")


# グローバル設定インスタンス
settings = Settings()