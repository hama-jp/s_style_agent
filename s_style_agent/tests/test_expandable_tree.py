#!/usr/bin/env python3
"""
サブツリー折りたたみ・展開機能のテスト
"""

# import pytest  # Not required for basic testing
import sys
from pathlib import Path
import tempfile
import time

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from s_style_agent.core.trace_logger import TraceLogger, TraceEntry, ExecutionMetadata, ProvenanceType
from s_style_agent.ui.trace_viewer import ExpandableTraceNode


class TestExpandableTraceNode:
    """ExpandableTraceNodeのテスト"""
    
    def test_node_creation(self):
        """基本的なノード作成テスト"""
        node = ExpandableTraceNode(
            operation="test_op",
            s_expr="(test arg1 arg2)"
        )
        
        assert node.operation == "test_op"
        assert node.s_expr == "(test arg1 arg2)"
        assert node.is_expanded == True  # デフォルトは展開
        assert node.execution_status == "pending"
        assert node.children == []
    
    def test_child_management(self):
        """子ノード管理テスト"""
        parent = ExpandableTraceNode("parent", "(parent)")
        child1 = ExpandableTraceNode("child1", "(child1)")
        child2 = ExpandableTraceNode("child2", "(child2)")
        
        parent.add_child(child1)
        parent.add_child(child2)
        
        assert len(parent.children) == 2
        assert child1.parent_node == parent
        assert child2.parent_node == parent
        assert child1.depth == 1
        assert child2.depth == 1
        assert child1.path == [0]
        assert child2.path == [1]
    
    def test_expansion_toggle(self):
        """展開/折りたたみ切り替えテスト"""
        node = ExpandableTraceNode("test", "(test)")
        child = ExpandableTraceNode("child", "(child)")
        node.add_child(child)
        
        # 初期状態は展開
        assert node.is_expanded == True
        assert len(node.get_visible_children()) == 1
        
        # 折りたたみ
        result = node.toggle_expansion()
        assert result == False
        assert node.is_expanded == False
        assert len(node.get_visible_children()) == 0
        
        # 再展開
        result = node.toggle_expansion()
        assert result == True
        assert node.is_expanded == True
        assert len(node.get_visible_children()) == 1
    
    def test_status_emojis(self):
        """ステータス絵文字テスト"""
        node = ExpandableTraceNode("test", "(test)")
        
        # 初期状態
        assert node.status_emoji == "⚪"
        
        # 実行中
        node.set_execution_status("running")
        assert node.status_emoji == "🟡"
        
        # 完了
        node.set_execution_status("completed", 150.5, "result")
        assert node.status_emoji == "🟢"
        assert node.duration_ms == 150.5
        assert node.result == "result"
        
        # エラー
        node.set_execution_status("error")
        assert node.status_emoji == "🔴"
    
    def test_expansion_emojis(self):
        """展開絵文字テスト"""
        node = ExpandableTraceNode("test", "(test)")
        
        # 子ノードなし
        assert node.expansion_emoji == "  "
        
        # 子ノードあり・展開
        child = ExpandableTraceNode("child", "(child)")
        node.add_child(child)
        assert node.expansion_emoji == "▼"
        
        # 子ノードあり・折りたたみ
        node.toggle_expansion()
        assert node.expansion_emoji == "▶"
    
    def test_display_label(self):
        """表示ラベルテスト"""
        node = ExpandableTraceNode("calc", "(calc 2 + 3)")
        node.set_execution_status("completed", 25.7, 5)
        
        label = node.display_label
        assert "calc" in label
        assert "(calc 2 + 3)" in label
        assert "25.7ms" in label
        assert "🟢" in label
    
    def test_path_search(self):
        """パス検索テスト"""
        root = ExpandableTraceNode("root", "(root)")
        child1 = ExpandableTraceNode("child1", "(child1)")
        child2 = ExpandableTraceNode("child2", "(child2)")
        grandchild = ExpandableTraceNode("grandchild", "(grandchild)")
        
        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)
        
        # パス検索テスト
        assert root.find_node_by_path([]) == root
        assert root.find_node_by_path([0]) == child1
        assert root.find_node_by_path([1]) == child2
        assert root.find_node_by_path([0, 0]) == grandchild
        assert root.find_node_by_path([2]) is None  # 存在しないパス
    
    def test_serialization(self):
        """シリアライゼーションテスト"""
        parent = ExpandableTraceNode("parent", "(parent)")
        child = ExpandableTraceNode("child", "(child)")
        parent.add_child(child)
        parent.set_execution_status("completed", 100.0, "success")
        
        # 辞書変換
        data = parent.to_dict()
        assert data["operation"] == "parent"
        assert data["s_expr"] == "(parent)"
        assert data["execution_status"] == "completed"
        assert data["duration_ms"] == 100.0
        assert len(data["children"]) == 1
        
        # 復元
        restored = ExpandableTraceNode.from_dict(data)
        assert restored.operation == parent.operation
        assert restored.s_expr == parent.s_expr
        assert restored.execution_status == parent.execution_status
        assert restored.duration_ms == parent.duration_ms
        assert len(restored.children) == 1
        assert restored.children[0].operation == "child"


class TestTraceLoggerHierarchy:
    """TraceLogger階層構造機能のテスト"""
    
    def test_hierarchy_metadata(self):
        """階層メタデータ機能テスト"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_file = Path(f.name)
        
        try:
            logger = TraceLogger(temp_file)
            
            # ルート操作
            root_id = logger.start_operation("root", "(seq (calc 1 + 2) (notify result))")
            logger.end_operation(root_id, "root_result")
            
            # 子操作1
            logger.push_path(0)
            child1_id = logger.start_operation("calc", "(calc 1 + 2)")
            logger.end_operation(child1_id, 3)
            logger.pop_path()
            
            # 子操作2
            logger.push_path(1)
            child2_id = logger.start_operation("notify", "(notify result)")
            logger.end_operation(child2_id, "notified")
            logger.pop_path()
            
            # 階層構造を分析
            logger.analyze_tree_structure()
            
            # 検証
            root_entry = logger.entries[0]
            child1_entry = logger.entries[1]
            child2_entry = logger.entries[2]
            
            # ルートエントリ
            assert root_entry.metadata.depth == 0
            assert root_entry.metadata.parent_path is None
            assert root_entry.metadata.has_children == True
            assert root_entry.metadata.child_count == 2
            
            # 子エントリ1
            assert child1_entry.metadata.depth == 1
            assert child1_entry.metadata.parent_path == []
            assert child1_entry.metadata.has_children == False
            assert child1_entry.metadata.child_count == 0
            
            # 子エントリ2
            assert child2_entry.metadata.depth == 1
            assert child2_entry.metadata.parent_path == []
            assert child2_entry.metadata.has_children == False
            
        finally:
            temp_file.unlink(missing_ok=True)
    
    def test_tree_summary(self):
        """ツリーサマリー機能テスト"""
        logger = TraceLogger()
        
        # 複雑な階層構造を作成
        logger.start_operation("root", "root")
        logger.push_path(0)
        logger.start_operation("level1_1", "level1_1")
        logger.push_path(0)
        logger.start_operation("level2_1", "level2_1")
        logger.pop_path()
        logger.push_path(1)
        logger.start_operation("level2_2", "level2_2")
        logger.pop_path()
        logger.pop_path()
        logger.push_path(1)
        logger.start_operation("level1_2", "level1_2")
        logger.pop_path()
        
        summary = logger.get_tree_summary()
        
        assert summary["total_operations"] == 5
        assert summary["max_depth"] == 2
        assert 0 in summary["depth_statistics"]  # 深度0
        assert 1 in summary["depth_statistics"]  # 深度1
        assert 2 in summary["depth_statistics"]  # 深度2
        
        complexity = summary["tree_complexity"]
        assert complexity["total_nodes"] == 5
        assert complexity["leaf_nodes"] > 0
        assert complexity["branch_nodes"] > 0


def test_integration():
    """統合テスト: TraceLoggerとExpandableTraceNodeの連携"""
    logger = TraceLogger()
    
    # トレースデータを作成
    root_id = logger.start_operation("seq", "(seq (calc 5 * 6) (notify result))")
    logger.end_operation(root_id, "completed")
    
    logger.push_path(0)
    calc_id = logger.start_operation("calc", "(calc 5 * 6)")
    logger.end_operation(calc_id, 30)
    logger.pop_path()
    
    logger.push_path(1)
    notify_id = logger.start_operation("notify", "(notify result)")
    logger.end_operation(notify_id, "notification sent")
    logger.pop_path()
    
    # 階層構造を分析
    logger.analyze_tree_structure()
    
    # ExpandableTraceNodeツリーを構築（簡易版）
    entries = logger.get_recent_entries(10)
    root_node = ExpandableTraceNode("root", "S式実行ルート")
    
    # エントリからノードを作成
    for entry in entries:
        if not entry.path:  # ルートレベル
            node = ExpandableTraceNode(entry.operation, str(entry.input))
            node.set_execution_status("completed", entry.duration_ms, entry.output)
            root_node.add_child(node)
    
    assert len(root_node.children) == 1
    seq_node = root_node.children[0]
    assert seq_node.operation == "seq"
    assert seq_node.execution_status == "completed"


if __name__ == "__main__":
    # 基本テストを実行
    test_node = TestExpandableTraceNode()
    test_node.test_node_creation()
    test_node.test_child_management()
    test_node.test_expansion_toggle()
    test_node.test_status_emojis()
    test_node.test_expansion_emojis()
    test_node.test_display_label()
    test_node.test_path_search()
    test_node.test_serialization()
    
    test_logger = TestTraceLoggerHierarchy()
    test_logger.test_hierarchy_metadata()
    test_logger.test_tree_summary()
    
    test_integration()
    
    print("✅ すべてのテストが正常に完了しました！")
    print("サブツリー折りたたみ・展開機能の実装が完了しました。")