#!/usr/bin/env python3
"""
TUIデバッグログ機能の使用例

実際のTUIアプリでデバッグログを活用する方法のデモンストレーション
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 環境変数でデバッグレベルを設定（実際の使用時に設定）
os.environ["TUI_DEBUG_LEVEL"] = "DEBUG"

from s_style_agent.ui.debug_logger import get_debug_logger, DebugLogLevel
from s_style_agent.core.trace_logger import TraceLogger
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression


def simulate_tui_session():
    """TUIセッションをシミュレート"""
    print("🎮 TUIデバッグログ使用例デモ")
    print("=" * 50)
    
    # デバッグロガーを取得
    debug_logger = get_debug_logger()
    debug_logger.info("DEMO", "start", "TUIデバッグログデモ開始")
    
    print(f"📊 現在のログレベル: {debug_logger.min_level.name}")
    print(f"📁 ログファイル: {debug_logger.log_file}")
    print()
    
    # S式実行をシミュレート
    print("🧮 S式実行シミュレーション:")
    
    trace_logger = TraceLogger()
    evaluator = ContextualEvaluator()
    env = Environment()
    
    test_expressions = [
        "(+ 10 20)",
        "(seq (+ 1 2) (+ 3 4))",
        "(calc 5 * 6)",
        "(if (< 5 10) (notify 'true') (notify 'false'))"
    ]
    
    for i, s_expr_text in enumerate(test_expressions, 1):
        print(f"\n🔢 テスト {i}: {s_expr_text}")
        
        # UI操作ログ
        debug_logger.log_ui_event("input", "s_expr_input", f"S式入力: {s_expr_text}")
        debug_logger.log_key_event("Enter", "execute_s_expression")
        
        try:
            # S式実行
            debug_logger.log_s_expr_evaluation(s_expr_text, "parse_start")
            parsed_expr = parse_s_expression(s_expr_text)
            debug_logger.log_s_expr_evaluation(s_expr_text, "parse_complete", parsed_expr)
            
            debug_logger.log_s_expr_evaluation(s_expr_text, "eval_start")
            import time
            start_time = time.time()
            
            result = evaluator.evaluate_with_context(parsed_expr, env)
            
            duration_ms = (time.time() - start_time) * 1000
            debug_logger.log_s_expr_evaluation(s_expr_text, "eval_complete", result)
            debug_logger.log_performance("s_expr_evaluation", duration_ms)
            
            print(f"  ✅ 結果: {result}")
            
        except Exception as e:
            debug_logger.log_error_with_traceback(e, "s_expr_execution", s_expr=s_expr_text)
            print(f"  ❌ エラー: {e}")
    
    # ノード操作シミュレート
    print(f"\n🌳 ノード操作シミュレーション:")
    debug_logger.log_key_event("Space", "toggle_expansion")
    debug_logger.log_node_operation("expand", [0], "ルートノード展開", children=2)
    debug_logger.log_key_event("Down", "navigate")
    debug_logger.log_key_event("Enter", "select_node") 
    debug_logger.log_node_operation("select", [0, 1], "子ノード選択")
    
    # パフォーマンス警告シミュレート
    print(f"\n⚡ パフォーマンス警告シミュレーション:")
    debug_logger.log_performance("heavy_operation", 1200.5)  # 重い処理
    debug_logger.log_performance("normal_operation", 45.2)   # 通常処理
    
    # デバッグレベル変更シミュレート
    print(f"\n🔧 デバッグレベル変更シミュレーション:")
    debug_logger.log_key_event("D", "toggle_debug_level")
    debug_logger.set_log_level(DebugLogLevel.TRACE)
    debug_logger.trace("UI", "level_change", "TRACEレベルに変更されました")
    
    debug_logger.log_key_event("D", "toggle_debug_level")
    debug_logger.set_log_level(DebugLogLevel.ERROR)
    debug_logger.debug("UI", "invisible", "このメッセージは表示されません")
    debug_logger.error("UI", "visible", "ERRORレベルなので表示されます")
    
    # 最近のログ表示シミュレート
    print(f"\n📝 最近のログ表示シミュレーション:")
    debug_logger.log_key_event("L", "show_debug_log")
    recent_logs = debug_logger.get_recent_logs(5)
    
    print("📋 最近のデバッグログ（最新5件）:")
    for log_entry in recent_logs[-5:]:
        formatted = debug_logger._format_message(log_entry)
        print(f"  {formatted}")
    
    debug_logger.info("DEMO", "end", "TUIデバッグログデモ終了")
    print(f"\n✅ デモ完了!")
    print(f"📁 詳細ログは '{debug_logger.log_file}' をご確認ください")


def show_log_file_example():
    """生成されたログファイルの内容例を表示"""
    print("\n📄 ログファイル内容例:")
    print("-" * 50)
    
    debug_logger = get_debug_logger()
    try:
        with open(debug_logger.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 最新の10行を表示
        print("(最新10行)")
        for line in lines[-10:]:
            print(f"  {line.strip()}")
            
    except FileNotFoundError:
        print("  (ログファイルがまだ作成されていません)")
    
    print("-" * 50)


def show_usage_instructions():
    """使用方法の説明"""
    print("\n📚 TUIデバッグログ使用方法:")
    print("=" * 50)
    
    print("🌍 環境変数設定:")
    print("  export TUI_DEBUG_LEVEL=DEBUG    # ログレベル設定")
    print("  export TUI_DEBUG_LEVEL=TRACE    # 最詳細ログ")
    print("  export TUI_DEBUG_LEVEL=INFO     # 標準ログ")
    print("  export TUI_DEBUG_LEVEL=ERROR    # エラーのみ")
    
    print("\n🎮 TUI内操作:")
    print("  D キー: デバッグレベル切り替え")
    print("  L キー: 最近のデバッグログ表示")
    print("  Space: ノード展開/折りたたみ（ログ記録）")
    print("  Enter: ノード選択（ログ記録）")
    print("  ↑↓: ナビゲーション（ログ記録）")
    
    print("\n📁 ログファイル:")
    print("  場所: tui_debug.log (実行ディレクトリ)")
    print("  形式: [時刻] [レベル] [カテゴリ:操作] メッセージ | コンテキスト")
    
    print("\n🔍 ログカテゴリ:")
    print("  UI    : ユーザーインターフェース操作")
    print("  EVAL  : S式評価処理")
    print("  NODE  : ツリーノード操作")
    print("  KEY   : キーボード入力")
    print("  ERROR : エラー・例外")
    print("  PERF  : パフォーマンス測定")
    print("  TRACE : トレース更新")
    
    print("\n💡 デバッグのコツ:")
    print("  1. 問題発生時はDキーでTRACEレベルに設定")
    print("  2. Lキーで最近のログを確認")
    print("  3. ログファイルで詳細な実行履歴を追跡")
    print("  4. パフォーマンス警告（🐌）で重い処理を特定")
    print("  5. エラートレースバックで問題箇所を特定")


def main():
    """メイン実行"""
    try:
        simulate_tui_session()
        show_log_file_example()
        show_usage_instructions()
        
        print("\n🎉 TUIデバッグログ機能が正常に動作しています!")
        return True
        
    except Exception as e:
        print(f"❌ デモ実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)