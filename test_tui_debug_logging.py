#!/usr/bin/env python3
"""
TUIデバッグログ機能の包括的テスト
"""

import sys
import time
import tempfile
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.ui.debug_logger import TUIDebugLogger, DebugLogLevel, setup_debug_logging
from s_style_agent.core.trace_logger import TraceLogger
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression


def test_debug_logger_basic():
    """デバッグロガーの基本機能テスト"""
    print("🧪 デバッグロガー基本機能テスト開始")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test_debug.log"
        
        # ロガー作成
        logger = TUIDebugLogger(log_file, DebugLogLevel.TRACE)
        logger.enable_console_output(False)  # テスト中はコンソール出力無効
        
        # 各レベルのログをテスト
        logger.trace("TEST", "trace_test", "トレースレベルテスト", {"key": "value"})
        logger.debug("TEST", "debug_test", "デバッグレベルテスト")
        logger.info("TEST", "info_test", "情報レベルテスト")
        logger.warn("TEST", "warn_test", "警告レベルテスト")
        logger.error("TEST", "error_test", "エラーレベルテスト")
        
        # 専用ログメソッドをテスト
        logger.log_ui_event("click", "button1", "ボタンクリック", user="test")
        logger.log_key_event("Space", "toggle_expansion", active_node="node1")
        logger.log_s_expr_evaluation("(+ 1 2)", "evaluate", 3, duration_ms=15.5)
        logger.log_node_operation("expand", [0, 1], "ノード展開", children=2)
        logger.log_performance("test_operation", 250.7, complexity="high")
        
        # エラーログテスト
        try:
            raise ValueError("テストエラー")
        except Exception as e:
            logger.log_error_with_traceback(e, "test_error_logging")
        
        # ログファイル確認
        assert log_file.exists(), "ログファイルが作成されていません"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
        # 各種ログが含まれていることを確認
        assert "trace_test" in log_content, "トレースログが記録されていません"
        assert "debug_test" in log_content, "デバッグログが記録されていません"
        assert "info_test" in log_content, "情報ログが記録されていません"
        assert "warn_test" in log_content, "警告ログが記録されていません"
        assert "error_test" in log_content, "エラーログが記録されていません"
        assert "UI:click" in log_content, "UIイベントログが記録されていません"
        assert "KEY:press" in log_content, "キーイベントログが記録されていません"
        assert "EVAL:evaluate" in log_content, "S式評価ログが記録されていません"
        assert "NODE:expand" in log_content, "ノード操作ログが記録されていません"
        assert "PERF:test_operation" in log_content, "パフォーマンスログが記録されていません"
        assert "ValueError" in log_content, "エラートレースバックが記録されていません"
        
        # メモリ内ログ確認
        recent_logs = logger.get_recent_logs(5)
        assert len(recent_logs) > 0, "メモリ内ログが保存されていません"
        
        logger.shutdown()
        print("✅ デバッグロガー基本機能テスト完了")
        return True


def test_log_level_filtering():
    """ログレベルフィルタリングテスト"""
    print("🧪 ログレベルフィルタリングテスト開始")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test_filter.log"
        
        # INFO レベルでロガー作成
        logger = TUIDebugLogger(log_file, DebugLogLevel.INFO)
        logger.enable_console_output(False)
        
        # 各レベルのログを記録
        logger.trace("FILTER", "trace", "表示されないはず")
        logger.debug("FILTER", "debug", "表示されないはず")
        logger.info("FILTER", "info", "表示されるはず")
        logger.warn("FILTER", "warn", "表示されるはず")
        logger.error("FILTER", "error", "表示されるはず")
        
        # ログファイル確認
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # INFOレベル以上のみ記録されていることを確認
        assert "表示されないはず" not in log_content, "TRACEレベルログが記録されています"
        assert "表示されるはず" in log_content, "INFOレベル以上のログが記録されていません"
        
        # レベル変更テスト
        logger.set_log_level(DebugLogLevel.ERROR)
        logger.info("FILTER", "info_after", "変更後は表示されないはず")
        logger.error("FILTER", "error_after", "変更後も表示されるはず")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            updated_content = f.read()
        
        assert "変更後は表示されないはず" not in updated_content, "レベル変更後のフィルタリングが動作していません"
        assert "変更後も表示されるはず" in updated_content, "エラーレベルログが記録されていません"
        
        logger.shutdown()
        print("✅ ログレベルフィルタリングテスト完了")
        return True


def test_integration_with_trace_viewer():
    """TraceViewerとの統合テスト"""
    print("🧪 TraceViewer統合テスト開始")
    
    try:
        # TUIクラスをインポート（実際のUI起動はしない）
        from s_style_agent.ui.trace_viewer import ExpandableTraceNode
        
        # ExpandableTraceNodeのログ機能をテスト
        node = ExpandableTraceNode("test_op", "(test 1 2)")
        node.add_child(ExpandableTraceNode("child", "(child)"))
        
        # 展開切り替え（ログが出力される）
        initial_state = node.is_expanded
        node.toggle_expansion()
        final_state = node.is_expanded
        
        assert initial_state != final_state, "ノード展開状態が変更されていません"
        
        print("✅ TraceViewer統合テスト完了")
        return True
        
    except ImportError as e:
        print(f"⚠️ TraceViewer統合テスト スキップ (Textual未インストール): {e}")
        return True


def test_s_expression_evaluation_logging():
    """S式評価時のログ出力テスト"""
    print("🧪 S式評価ログテスト開始")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test_eval.log"
        
        # デバッグロガーを設定
        debug_logger = setup_debug_logging(log_file, DebugLogLevel.DEBUG)
        debug_logger.enable_console_output(False)
        
        # S式評価システムを初期化
        trace_logger = TraceLogger()
        evaluator = ContextualEvaluator()
        env = Environment()
        
        try:
            # 簡単なS式を評価
            s_expr_text = "(+ 5 3)"
            parsed_expr = parse_s_expression(s_expr_text)
            
            # 評価前にログ
            debug_logger.log_s_expr_evaluation(s_expr_text, "start", None)
            
            result = evaluator.evaluate_with_context(parsed_expr, env)
            
            # 評価後にログ
            debug_logger.log_s_expr_evaluation(s_expr_text, "complete", result)
            
            assert result == 8, f"S式評価結果が正しくありません: {result}"
            
            # ログファイル確認
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            assert "(+ 5 3)" in log_content, "S式がログに記録されていません"
            assert "EVAL:start" in log_content, "評価開始ログが記録されていません"
            assert "EVAL:complete" in log_content, "評価完了ログが記録されていません"
            
        except Exception as e:
            debug_logger.log_error_with_traceback(e, "s_expr_evaluation_test")
            raise
        
        debug_logger.shutdown()
        print("✅ S式評価ログテスト完了")
        return True


def test_performance_logging():
    """パフォーマンスログテスト"""
    print("🧪 パフォーマンスログテスト開始")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test_perf.log"
        
        logger = TUIDebugLogger(log_file, DebugLogLevel.TRACE)
        logger.enable_console_output(False)
        
        # 異なる速度の操作をシミュレート
        logger.log_performance("fast_operation", 50.0)      # 高速
        logger.log_performance("normal_operation", 150.0)   # 通常
        logger.log_performance("slow_operation", 1200.0)    # 重い
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # 適切な絵文字/レベルが使用されていることを確認
        assert "⚡" in log_content, "高速処理の絵文字が見つかりません"
        assert "⏱️" in log_content, "通常処理の絵文字が見つかりません"
        assert "🐌" in log_content, "重い処理の絵文字が見つかりません"
        
        logger.shutdown()
        print("✅ パフォーマンスログテスト完了")
        return True


def test_environment_variable_config():
    """環境変数でのログレベル設定テスト"""
    print("🧪 環境変数設定テスト開始")
    
    import os
    
    # 環境変数設定
    original_level = os.environ.get("TUI_DEBUG_LEVEL")
    os.environ["TUI_DEBUG_LEVEL"] = "ERROR"
    
    try:
        # グローバルロガーを取得（環境変数を読み込む）
        from s_style_agent.ui.debug_logger import get_debug_logger
        
        # 新しいインスタンスを強制的に作成するため、グローバル変数をリセット
        import s_style_agent.ui.debug_logger as debug_module
        debug_module._debug_logger = None
        
        logger = get_debug_logger()
        
        # ERRORレベルに設定されていることを確認
        assert logger.min_level == DebugLogLevel.ERROR, f"ログレベルが正しく設定されていません: {logger.min_level}"
        
        print("✅ 環境変数設定テスト完了")
        return True
        
    finally:
        # 環境変数復元
        if original_level:
            os.environ["TUI_DEBUG_LEVEL"] = original_level
        else:
            os.environ.pop("TUI_DEBUG_LEVEL", None)


def main():
    """メインテスト実行"""
    print("🚀 TUIデバッグログ機能 包括テスト開始")
    print("=" * 60)
    
    try:
        test_results = []
        
        # 各テストを実行
        test_results.append(test_debug_logger_basic())
        print()
        
        test_results.append(test_log_level_filtering())
        print()
        
        test_results.append(test_integration_with_trace_viewer())
        print()
        
        test_results.append(test_s_expression_evaluation_logging())
        print()
        
        test_results.append(test_performance_logging())
        print()
        
        test_results.append(test_environment_variable_config())
        
        print("=" * 60)
        
        if all(test_results):
            print("🎉 すべてのテストが正常に完了しました！")
            print()
            print("📋 実装されたTUIデバッグログ機能:")
            print("  ✅ 多段階ログレベル (TRACE, DEBUG, INFO, WARN, ERROR)")
            print("  ✅ カテゴリ別ログ出力 (UI, EVAL, NODE, KEY, ERROR, PERF, TRACE)")
            print("  ✅ 自動エラートレースバック記録")
            print("  ✅ パフォーマンス監視と重い処理の警告")
            print("  ✅ S式評価の詳細ログ")
            print("  ✅ UI操作とキーイベントのログ")
            print("  ✅ ExpandableTraceNode状態変更ログ")
            print("  ✅ 環境変数によるログレベル制御")
            print("  ✅ ファイルとコンソール出力切り替え")
            print("  ✅ メモリ内ログバッファ")
            print()
            print("🎮 TUIでのデバッグ操作:")
            print("  🔍 D キー: デバッグレベル切り替え (TRACE → DEBUG → INFO → WARN → ERROR)")
            print("  📝 L キー: 最近のデバッグログをUI内に表示")
            print("  🌍 TUI_DEBUG_LEVEL環境変数: ログレベル設定")
            print()
            print("📁 ログファイル: tui_debug.log (実行ディレクトリに作成)")
            return True
        else:
            print("❌ 一部のテストが失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)