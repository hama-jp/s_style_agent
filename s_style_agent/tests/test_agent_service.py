"""
AgentService 自動テストスイート

CLI/TUI共通機能の包括的テスト
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from ..core.agent_service import AgentService
from ..core.parser import SExpressionParseError


class TestAgentService:
    """AgentService のテストクラス"""
    
    @pytest.fixture
    def agent_service(self):
        """テスト用 AgentService インスタンス"""
        return AgentService(
            llm_base_url="http://test:1234/v1",
            model_name="test-model",
            use_async=True
        )
    
    @pytest.fixture
    def sync_agent_service(self):
        """同期モード用 AgentService インスタンス"""
        return AgentService(
            llm_base_url="http://test:1234/v1", 
            model_name="test-model",
            use_async=False
        )

    def test_initialization(self, agent_service):
        """初期化テスト"""
        assert agent_service.use_async is True
        assert agent_service.llm_base_url == "http://test:1234/v1"
        assert agent_service.model_name == "test-model"
        assert agent_service.session_history == []
        assert agent_service.mcp_initialized is False
        assert hasattr(agent_service, 'llm')
        assert hasattr(agent_service, 'async_evaluator')
        assert hasattr(agent_service, 'async_global_env')
    
    def test_sync_initialization(self, sync_agent_service):
        """同期モード初期化テスト"""
        assert sync_agent_service.use_async is False
        assert hasattr(sync_agent_service, 'evaluator')
        assert hasattr(sync_agent_service, 'global_env')

    @pytest.mark.asyncio
    async def test_evaluate_s_expression_success(self, agent_service):
        """S式評価成功テスト"""
        # Mock async evaluator
        mock_result = 42
        agent_service.async_evaluator.evaluate_with_context = AsyncMock(return_value=mock_result)
        
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.return_value = ["calc", "2+2"]
            
            result = await agent_service.evaluate_s_expression("(calc \"2+2\")")
            
            assert result == mock_result
            assert len(agent_service.session_history) == 1
            
            history_entry = agent_service.session_history[0]
            assert history_entry["operation"] == "evaluate"
            assert history_entry["input"] == "(calc \"2+2\")"
            assert history_entry["output"] == mock_result
            assert history_entry["success"] is True

    @pytest.mark.asyncio
    async def test_evaluate_s_expression_error(self, agent_service):
        """S式評価エラーテスト"""
        agent_service.async_evaluator.evaluate_with_context = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.return_value = ["calc", "invalid"]
            
            with pytest.raises(Exception, match="Test error"):
                await agent_service.evaluate_s_expression("(calc \"invalid\")")
            
            assert len(agent_service.session_history) == 1
            history_entry = agent_service.session_history[0]
            assert history_entry["success"] is False
            assert "Test error" in history_entry["output"]

    @pytest.mark.asyncio
    async def test_generate_s_expression(self, agent_service):
        """S式生成テスト"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "(calc \"2+3\")"
        agent_service.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        result = await agent_service.generate_s_expression("calculate 2 plus 3")
        
        assert result == "(calc \"2+3\")"
        assert len(agent_service.session_history) == 1
        
        history_entry = agent_service.session_history[0]
        assert history_entry["operation"] == "generate"
        assert history_entry["input"] == "calculate 2 plus 3"
        assert history_entry["output"] == "(calc \"2+3\")"

    def test_parse_s_expression_safe_success(self, agent_service):
        """安全パース成功テスト"""
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.return_value = ["calc", "2+2"]
            
            result = agent_service.parse_s_expression_safe("(calc \"2+2\")")
            assert result == ["calc", "2+2"]

    def test_parse_s_expression_safe_error(self, agent_service):
        """安全パースエラーテスト"""
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.side_effect = SExpressionParseError("Invalid syntax")
            
            result = agent_service.parse_s_expression_safe("invalid")
            assert result is None

    def test_add_to_history(self, agent_service):
        """履歴追加テスト"""
        agent_service.add_to_history("test_op", "input_data", "output_data", True)
        
        assert len(agent_service.session_history) == 1
        entry = agent_service.session_history[0]
        
        assert entry["operation"] == "test_op"
        assert entry["input"] == "input_data"
        assert entry["output"] == "output_data"
        assert entry["success"] is True
        assert "timestamp" in entry

    def test_get_session_history(self, agent_service):
        """履歴取得テスト"""
        agent_service.add_to_history("op1", "input1", "output1")
        agent_service.add_to_history("op2", "input2", "output2")
        
        history = agent_service.get_session_history()
        
        assert len(history) == 2
        assert history[0]["operation"] == "op1"
        assert history[1]["operation"] == "op2"
        
        # コピーが返されることを確認
        history.append({"test": "added"})
        assert len(agent_service.session_history) == 2

    def test_clear_history(self, agent_service):
        """履歴クリアテスト"""
        agent_service.add_to_history("test", "input", "output")
        assert len(agent_service.session_history) == 1
        
        agent_service.clear_history()
        assert len(agent_service.session_history) == 0

    def test_toggle_execution_mode(self, agent_service):
        """実行モード切り替えテスト"""
        original_mode = agent_service.use_async
        
        new_mode = agent_service.toggle_execution_mode()
        
        assert agent_service.use_async != original_mode
        assert new_mode == ("sync" if original_mode else "async")
        assert len(agent_service.session_history) == 1
        
        history_entry = agent_service.session_history[0]
        assert history_entry["operation"] == "toggle_mode"

    @pytest.mark.asyncio
    async def test_run_benchmark(self, agent_service):
        """ベンチマークテスト"""
        # Mock evaluator for both sync and async
        mock_result = 5
        agent_service.async_evaluator.evaluate_with_context = AsyncMock(return_value=mock_result)
        
        # Temporarily create sync evaluator for test
        agent_service.evaluator = Mock()
        agent_service.global_env = Mock()
        agent_service.evaluator.evaluate_with_context = Mock(return_value=mock_result)
        
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.return_value = ["calc", "test"]
            
            result = await agent_service.run_benchmark(["(calc \"2+2\")"])
            
            assert "sync_duration_ms" in result
            assert "async_duration_ms" in result
            assert "improvement_percent" in result
            assert "test_count" in result
            assert result["test_count"] == 1
            
            # 履歴に記録されることを確認
            assert len(agent_service.session_history) == 1
            history_entry = agent_service.session_history[0]
            assert history_entry["operation"] == "benchmark"

    def test_get_available_tools(self, agent_service):
        """利用可能ツール取得テスト"""
        tools = agent_service.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # 内蔵ツールが含まれることを確認
        tool_names = [tool["name"] for tool in tools]
        assert "calc" in tool_names
        assert "notify" in tool_names
        assert "math" in tool_names
        
        # ツール情報の構造確認
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "type" in tool
            assert "status" in tool

    @pytest.mark.asyncio
    async def test_test_tools(self, agent_service):
        """ツールテスト機能のテスト"""
        # Mock evaluate_s_expression for different tools
        mock_results = {
            "(calc \"2+2\")": 4,
            "(notify \"テスト通知\")": None,
            "(math \"x + 2\" \"x=3\")": 5
        }
        
        async def mock_evaluate(s_expr, context=None):
            return mock_results.get(s_expr, "unknown")
        
        agent_service.evaluate_s_expression = mock_evaluate
        
        result = await agent_service.test_tools()
        
        assert isinstance(result, dict)
        assert "calc" in result
        assert "notify" in result
        assert "math" in result
        
        # calc のテスト結果確認
        calc_result = result["calc"]
        assert calc_result["status"] == "success"
        assert calc_result["result"] == 4
        assert calc_result["expected"] == 4

    @pytest.mark.asyncio
    async def test_init_mcp_system(self, agent_service):
        """MCP初期化テスト"""
        result = await agent_service.init_mcp_system()
        
        assert result is True
        assert agent_service.mcp_initialized is True
        
        # 履歴に記録されることを確認
        assert len(agent_service.session_history) == 1
        history_entry = agent_service.session_history[0]
        assert history_entry["operation"] == "init_mcp"

    def test_get_system_status(self, agent_service):
        """システム状態取得テスト"""
        status = agent_service.get_system_status()
        
        assert isinstance(status, dict)
        assert "execution_mode" in status
        assert "mcp_status" in status
        assert "session_count" in status
        assert "available_tools" in status
        assert "llm_model" in status
        assert "llm_base_url" in status
        
        assert status["execution_mode"] == "async"
        assert status["mcp_status"] == "not_initialized"
        assert status["session_count"] == 0
        assert status["llm_model"] == "test-model"
        assert status["llm_base_url"] == "http://test:1234/v1"


class TestAgentServiceIntegration:
    """AgentService 統合テスト"""
    
    @pytest.fixture
    def agent_service(self):
        """統合テスト用 AgentService"""
        return AgentService(use_async=True)
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, agent_service):
        """完全なワークフローテスト"""
        # 1. S式生成
        with patch.object(agent_service.llm, 'ainvoke') as mock_llm:
            mock_response = Mock()
            mock_response.content = "(calc \"5+3\")"
            mock_llm.return_value = mock_response
            
            generated = await agent_service.generate_s_expression("calculate 5 plus 3")
            assert generated == "(calc \"5+3\")"
        
        # 2. S式評価
        with patch.object(agent_service.async_evaluator, 'evaluate_with_context') as mock_eval:
            mock_eval.return_value = 8
            
            with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
                mock_parse.return_value = ["calc", "5+3"]
                
                result = await agent_service.evaluate_s_expression(generated)
                assert result == 8
        
        # 3. 履歴確認
        history = agent_service.get_session_history()
        assert len(history) == 2
        assert history[0]["operation"] == "generate"
        assert history[1]["operation"] == "evaluate"
        
        # 4. システム状態確認
        status = agent_service.get_system_status()
        assert status["session_count"] == 2

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, agent_service):
        """エラーハンドリングワークフローテスト"""
        # 生成エラー
        with patch.object(agent_service.llm, 'ainvoke') as mock_llm:
            mock_llm.side_effect = Exception("LLM Error")
            
            with pytest.raises(Exception, match="LLM Error"):
                await agent_service.generate_s_expression("test")
        
        # 評価エラー
        with patch('s_style_agent.core.parser.parse_s_expression') as mock_parse:
            mock_parse.side_effect = SExpressionParseError("Parse Error")
            
            with pytest.raises(Exception):
                await agent_service.evaluate_s_expression("invalid")
        
        # エラーが履歴に記録されることを確認
        history = agent_service.get_session_history()
        assert len(history) == 2
        assert not history[0]["success"]
        assert not history[1]["success"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])