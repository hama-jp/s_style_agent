#!/usr/bin/env python3
"""
S式エージェントシステム - メインエントリーポイント

起動オプション:
  --ui=tui (default): 新しいTUIモード
  --ui=cli          : 従来のCLIモード  
  --cli             : 従来のCLIモード（短縮形）
  --trace-only      : トレースビューア単独起動
  --help            : ヘルプ表示
"""

import argparse
import asyncio
import sys
from pathlib import Path

# パッケージルートを追加
sys.path.insert(0, str(Path(__file__).parent))

def parse_arguments():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(
        description='S式エージェントシステム',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py               # TUIモードで起動（デフォルト）
  python main.py --ui=cli      # CLIモードで起動
  python main.py --cli         # CLIモードで起動（短縮形）
  python main.py --trace-only  # トレースビューア単独起動
        """
    )
    
    parser.add_argument(
        '--ui',
        choices=['tui', 'cli'],
        default='tui',
        help='ユーザーインターフェース選択 (default: tui)'
    )
    
    parser.add_argument(
        '--dev',
        action='store_true',
        help='開発モード（従来のCLI）で起動'
    )
    
    parser.add_argument(
        '--cli',
        action='store_true',
        help='開発モード（従来のCLI）で起動（--dev の別名）'
    )
    
    parser.add_argument(
        '--trace-only',
        action='store_true',
        help='トレースビューア単独起動'
    )
    
    return parser.parse_args()

async def main():
    """メイン関数"""
    args = parse_arguments()
    
    # 起動モード決定
    if args.cli or args.ui == 'cli':
        mode = 'cli'
    elif args.trace_only:
        mode = 'trace'
    else:
        mode = 'tui'
    
    print(f"🚀 S式エージェントシステム起動中...")
    print(f"📱 モード: {mode.upper()}")
    
    try:
        if mode == 'cli':
            # 従来のCLIモード
            print("📟 従来のCLIモードで起動します")
            from s_style_agent.cli.main import SStyleAgentCLI
            cli = SStyleAgentCLI()
            await cli.run()
            
        elif mode == 'trace':
            # トレースビューア単独起動
            print("📊 トレースビューア単独モードで起動します")
            from s_style_agent.ui.trace_viewer import launch_trace_viewer
            from s_style_agent.core.trace_logger import configure_trace_logging
            
            # トレースログを設定
            logger = configure_trace_logging("s_expr_trace.jsonl")
            await launch_trace_viewer(logger)
            
        else:  # mode == 'tui'
            # 新しいTUIモード
            print("🎨 TUIモードで起動します")
            from s_style_agent.ui.main_app import launch_main_tui
            await launch_main_tui()
            
    except KeyboardInterrupt:
        print("\n👋 システムを終了します")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())