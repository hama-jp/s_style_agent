"""
設定管理

システム設定とLLM接続設定

環境変数による設定例:
# ローカルLLM (デフォルト)
export LLM_BASE_URL="http://localhost:1234/v1"
export LLM_MODEL_NAME="local-model"
export LLM_API_KEY="dummy"

# OpenAI GPT-4
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL_NAME="gpt-4"
export LLM_API_KEY="your-openai-api-key-here"

# OpenAI GPT-3.5 Turbo
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL_NAME="gpt-3.5-turbo"
export LLM_API_KEY="your-openai-api-key-here"

# Anthropic Claude
export LLM_BASE_URL="https://api.anthropic.com"
export LLM_MODEL_NAME="claude-3-sonnet-20240229"
export LLM_API_KEY="your-anthropic-api-key-here"
"""

import os
from typing import Optional
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """LLM設定
    
    デフォルトはローカルLLMサーバー用の設定です。
    OpenAIやその他のクラウドAPIを使用する場合は環境変数で設定してください。
    
    例:
    - ローカルLLM: base_url="http://localhost:1234/v1", api_key="dummy"
    - OpenAI: base_url="https://api.openai.com/v1", api_key="sk-..."
    - Anthropic: base_url="https://api.anthropic.com", api_key="sk-ant-..."
    """
    base_url: str = "http://localhost:1234/v1"  # デフォルトをlocalhostに変更
    model_name: str = "local-model"  # 一般的な名前に変更
    api_key: str = "dummy"  # ローカルLLM用ダミーキー
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