"""
MCP サーバー設定管理

mcp.json ファイルの読み込みと設定管理を担当
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from langsmith import traceable


@dataclass
class MCPServerConfig:
    """MCP サーバー設定"""
    id: str
    command: str
    args: List[str]
    env: Dict[str, str]
    transport: str = "stdio"
    autostart: bool = True
    cwd: Optional[str] = None
    restart_policy: str = "on_failure"
    eager_tool_prefetch: bool = True
    
    def get_full_env(self) -> Dict[str, str]:
        """環境変数を取得（システム環境変数とマージ）"""
        full_env = os.environ.copy()
        full_env.update(self.env)
        return full_env


class MCPConfigLoader:
    """MCP 設定ローダー"""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = Path(config_path)
        self.servers: Dict[str, MCPServerConfig] = {}
        
    @traceable(name="load_mcp_config")
    def load_config(self) -> Dict[str, MCPServerConfig]:
        """mcp.json から設定を読み込み"""
        if not self.config_path.exists():
            print(f"[MCP] 設定ファイルが見つかりません: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            mcp_servers = config_data.get("mcpServers", {})
            
            for server_id, server_config in mcp_servers.items():
                self.servers[server_id] = MCPServerConfig(
                    id=server_id,
                    command=server_config["command"],
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    transport=server_config.get("transport", "stdio"),
                    autostart=server_config.get("autostart", True),
                    cwd=server_config.get("cwd"),
                    restart_policy=server_config.get("restart_policy", "on_failure"),
                    eager_tool_prefetch=server_config.get("eager_tool_prefetch", True)
                )
            
            print(f"[MCP] {len(self.servers)}個のサーバー設定を読み込みました")
            return self.servers
            
        except json.JSONDecodeError as e:
            print(f"[MCP] 設定ファイルの解析エラー: {e}")
            return {}
        except Exception as e:
            print(f"[MCP] 設定読み込みエラー: {e}")
            return {}
    
    def get_server_config(self, server_id: str) -> Optional[MCPServerConfig]:
        """指定されたサーバーの設定を取得"""
        return self.servers.get(server_id)
    
    def get_autostart_servers(self) -> List[MCPServerConfig]:
        """自動起動対象のサーバー設定を取得"""
        return [config for config in self.servers.values() if config.autostart]
    
    def validate_config(self) -> bool:
        """設定の妥当性をチェック"""
        for server_id, config in self.servers.items():
            # 必須フィールドのチェック
            if not config.command:
                print(f"[MCP] サーバー '{server_id}': command が指定されていません")
                return False
            
            # 環境変数のプレースホルダーチェック
            for env_key, env_value in config.env.items():
                if env_value.startswith("YOUR_") and env_value.endswith("_HERE"):
                    print(f"[MCP] サーバー '{server_id}': 環境変数 {env_key} がプレースホルダーのままです")
                    return False
        
        return True


# グローバル設定インスタンス
mcp_config_loader = MCPConfigLoader()