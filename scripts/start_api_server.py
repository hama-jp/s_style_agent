#!/usr/bin/env python3
"""
S式エージェントAPIサーバー起動スクリプト
"""

import uvicorn
import argparse
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from s_style_agent.tools.builtin_tools import register_builtin_tools


def main():
    parser = argparse.ArgumentParser(description="S式エージェントAPIサーバー")
    parser.add_argument("--host", default="127.0.0.1", help="ホストアドレス")
    parser.add_argument("--port", type=int, default=8000, help="ポート番号")
    parser.add_argument("--reload", action="store_true", help="ファイル変更時の自動リロード")
    parser.add_argument("--workers", type=int, default=1, help="ワーカー数")
    parser.add_argument("--log-level", default="info", help="ログレベル")
    
    args = parser.parse_args()
    
    # 組み込みツールを登録
    register_builtin_tools()
    
    print(f"🚀 S式エージェントAPIサーバーを起動中...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   URL: http://{args.host}:{args.port}")
    print(f"   WebSocket: ws://{args.host}:{args.port}/ws/{{session_id}}")
    print(f"   ドキュメント: http://{args.host}:{args.port}/docs")
    
    # サーバー起動
    uvicorn.run(
        "s_style_agent.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,  # reloadモードでは1ワーカーのみ
        log_level=args.log_level
    )


if __name__ == "__main__":
    main()