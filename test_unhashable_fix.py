#!/usr/bin/env python3
"""
unhashable type: 'dict' エラーの修正テスト
"""

import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.core.trace_logger import TraceLogger
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression


def test_basic_s_expression_evaluation():
    """基本的なS式評価テスト"""
    print("🧪 S式評価の基本テスト開始...")
    
    # TraceLoggerとEvaluatorを初期化
    logger = TraceLogger()
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 簡単なS式をテスト
    test_expressions = [
        "(+ 2 3)",
        "(calc 5 * 6)",
        "(notify 'Hello World')",
        "(seq (+ 1 2) (+ 3 4))"
    ]
    
    for s_expr_str in test_expressions:
        print(f"📝 テスト中: {s_expr_str}")
        
        try:
            # S式をパースして評価
            parsed_expr = parse_s_expression(s_expr_str)
            print(f"  パース結果: {parsed_expr}")
            
            result = evaluator.evaluate_with_context(parsed_expr, env)
            print(f"  ✅ 評価結果: {result}")
            
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("✅ 基本S式評価テスト完了")
    return True


def test_trace_logger_with_dict_input():
    """辞書入力でのTraceLogger動作テスト"""
    print("🧪 TraceLoggerの辞書入力テスト開始...")
    
    logger = TraceLogger()
    
    # 辞書を含む複雑な入力をテスト
    complex_input = {
        "s_expr": "(+ 2 3)",
        "parsed": ["+", 2, 3],
        "metadata": {"depth": 1, "operation": "test"}
    }
    
    try:
        # start_operationの新しいシグネチャをテスト
        entry_id = logger.start_operation(
            operation="evaluate",
            input_data=complex_input,
            explanation="辞書入力テスト"
        )
        
        print(f"  ✅ エントリID {entry_id} で正常に開始")
        
        # 操作完了
        logger.end_operation(entry_id, 5)
        
        # エントリを確認
        entry = logger.entries[entry_id]
        print(f"  📊 エントリ内容:")
        print(f"    操作: {entry.operation}")
        print(f"    入力: {entry.input}")
        print(f"    出力: {entry.output}")
        print(f"    説明: {entry.explanation}")
        
        print("✅ TraceLoggerの辞書入力テスト完了")
        return True
        
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tui_compatibility():
    """TUI互換性テスト"""
    print("🧪 TUI互換性テスト開始...")
    
    # TUIで使用される方法をシミュレート
    logger = TraceLogger()
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # TUIからの典型的なS式入力
    s_expr_text = "(seq (calc 2 + 3) (notify result))"
    
    try:
        print(f"📝 TUI入力シミュレート: {s_expr_text}")
        
        # TUIと同じ処理フロー
        logger.clear()  # ログクリア
        
        parsed_expr = parse_s_expression(s_expr_text)
        print(f"  パース結果: {parsed_expr}")
        
        result = evaluator.evaluate_with_context(parsed_expr, env)
        print(f"  ✅ 評価結果: {result}")
        
        # トレースエントリの確認
        recent_entries = logger.get_recent_entries(10)
        print(f"  📊 生成されたトレースエントリ数: {len(recent_entries)}")
        
        for i, entry in enumerate(recent_entries):
            print(f"    [{i}] {entry.operation}: {entry.explanation}")
        
        print("✅ TUI互換性テスト完了")
        return True
        
    except Exception as e:
        print(f"  ❌ TUI互換性エラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """メインテスト実行"""
    print("🚀 unhashable type: 'dict' エラー修正テスト開始")
    print("=" * 50)
    
    try:
        # 各テストを実行
        success = True
        
        success &= test_trace_logger_with_dict_input()
        print()
        
        success &= test_basic_s_expression_evaluation()
        print()
        
        success &= test_tui_compatibility()
        
        print("=" * 50)
        if success:
            print("🎉 すべてのテストが正常に完了しました！")
            print("✅ unhashable type: 'dict' エラーが修正されました")
            print("✅ TUIでのS式評価が正常に動作するはずです")
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