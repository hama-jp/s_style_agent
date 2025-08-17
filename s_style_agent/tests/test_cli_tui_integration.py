"""
CLI/TUI統合テストスイート

共通サービス経由でのCLI/TUI動作テスト
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from ..cli.main import SStyleAgentCLI
from ..ui.main_app import MainTUIApp


class TestCLIIntegration:
    """CLI統合テスト"""
    
    @pytest.fixture
    def cli(self):
        """テスト用CLIインスタンス"""
        return SStyleAgentCLI(
            llm_base_url="http://test:1234/v1",
            model_name="test-model",
            use_async=True
        )
    
    def test_cli_initialization(self, cli):
        """CLI初期化テスト"""
        assert hasattr(cli, 'agent_service')
        assert cli.use_async is True
        assert cli.agent_service.use_async is True
        assert hasattr(cli, 'llm')
        assert hasattr(cli, 'session_history')
    
    @pytest.mark.asyncio
    async def test_cli_generate_s_expression(self, cli):
        """CLI S式生成テスト"""
        # Mock agent service
        cli.agent_service.generate_s_expression = AsyncMock(return_value="(calc \"2+2\")")
        
        result = await cli.generate_s_expression("calculate 2 plus 2")
        
        assert result == "(calc \"2+2\")"
        cli.agent_service.generate_s_expression.assert_called_once_with("calculate 2 plus 2")
    
    @pytest.mark.asyncio
    async def test_cli_execute_s_expression(self, cli):
        """CLI S式実行テスト"""
        # Mock agent service
        cli.agent_service.evaluate_s_expression = AsyncMock(return_value=4)
        
        result = await cli.execute_s_expression("(calc \"2+2\")", "test context")
        
        assert result == 4
        cli.agent_service.evaluate_s_expression.assert_called_once_with(
            "(calc \"2+2\")", {"context": "test context"}
        )
    
    @pytest.mark.asyncio
    async def test_cli_run_benchmark(self, cli):
        """CLI ベンチマークテスト"""
        # Mock agent service
        mock_result = {
            "sync_duration_ms": 100.0,
            "async_duration_ms": 50.0,
            "improvement_percent": 50.0,
            "test_count": 3
        }
        cli.agent_service.run_benchmark = AsyncMock(return_value=mock_result)
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            await cli.run_benchmark()
            
            # ベンチマーク結果が出力されることを確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("ベンチマーク結果" in call for call in print_calls)
            assert any("50.0%" in call for call in print_calls)
    
    @pytest.mark.asyncio
    async def test_cli_toggle_mode(self, cli):
        """CLI モード切り替えテスト"""
        # Mock agent service
        cli.agent_service.toggle_execution_mode = Mock(return_value="sync")
        cli.agent_service.use_async = False
        
        with patch('builtins.print') as mock_print:
            await cli.toggle_mode()
            
            assert cli.use_async is False
            cli.agent_service.toggle_execution_mode.assert_called_once()
            
            # モード切り替えメッセージが出力されることを確認
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("同期" in call for call in print_calls)


class TestTUIIntegration:
    """TUI統合テスト"""
    
    @pytest.fixture
    def tui_app(self):
        """テスト用TUIアプリインスタンス"""
        return MainTUIApp()
    
    def test_tui_initialization(self, tui_app):
        """TUI初期化テスト"""
        assert hasattr(tui_app, 'agent_service')
        assert tui_app.use_async is True
        assert tui_app.agent_service.use_async is True
        assert hasattr(tui_app, 'session_history')
        assert hasattr(tui_app, 'trace_logger')
    
    @pytest.mark.asyncio
    async def test_tui_evaluate_s_expression(self, tui_app):
        """TUI S式評価テスト"""
        # Mock agent service
        tui_app.agent_service.evaluate_s_expression = AsyncMock(return_value=42)
        
        result = await tui_app.evaluate_s_expression("(calc \"6*7\")")
        
        assert result == 42
        tui_app.agent_service.evaluate_s_expression.assert_called_once_with("(calc \"6*7\")", None)
    
    @pytest.mark.asyncio
    async def test_tui_generate_s_expression(self, tui_app):
        """TUI S式生成テスト"""
        # Mock agent service
        tui_app.agent_service.generate_s_expression = AsyncMock(return_value="(notify \"hello\")")
        
        result = await tui_app.generate_s_expression("say hello")
        
        assert result == "(notify \"hello\")"
        tui_app.agent_service.generate_s_expression.assert_called_once_with("say hello")
    
    @pytest.mark.asyncio
    async def test_tui_run_benchmark(self, tui_app):
        """TUI ベンチマークテスト"""
        # Mock agent service
        mock_result = {
            "sync_duration_ms": 200.0,
            "async_duration_ms": 80.0,
            "improvement_percent": 60.0,
            "test_count": 3
        }
        tui_app.agent_service.run_benchmark = AsyncMock(return_value=mock_result)
        
        result = await tui_app.run_benchmark()
        
        assert result == mock_result
        tui_app.agent_service.run_benchmark.assert_called_once()
    
    def test_tui_toggle_execution_mode(self, tui_app):
        """TUI モード切り替えテスト"""
        # Mock agent service and notification
        tui_app.agent_service.toggle_execution_mode = Mock(return_value="sync")
        tui_app.agent_service.use_async = False
        tui_app.update_status_bar = Mock()
        tui_app.notify = Mock()
        
        tui_app.toggle_execution_mode()
        
        assert tui_app.use_async is False
        assert tui_app.current_mode == "sync"
        tui_app.agent_service.toggle_execution_mode.assert_called_once()
        tui_app.update_status_bar.assert_called_once()
        tui_app.notify.assert_called_once_with("実行モードをsyncに切り替えました")
    
    def test_tui_get_available_tools(self, tui_app):
        """TUI ツール一覧取得テスト"""
        # Mock agent service
        mock_tools = [
            {"name": "calc", "description": "計算", "type": "builtin", "status": "available"},
            {"name": "search", "description": "検索", "type": "mcp", "status": "available"}
        ]
        tui_app.agent_service.get_available_tools = Mock(return_value=mock_tools)
        
        result = tui_app.get_available_tools()
        
        assert result == mock_tools
        tui_app.agent_service.get_available_tools.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_tui_test_tools(self, tui_app):
        """TUI ツールテストテスト"""
        # Mock agent service
        mock_results = {
            "calc": {"status": "success", "result": 4, "expected": 4},
            "notify": {"status": "success", "result": None, "expected": None}
        }
        tui_app.agent_service.test_tools = AsyncMock(return_value=mock_results)
        
        result = await tui_app.test_tools()
        
        assert result == mock_results
        tui_app.agent_service.test_tools.assert_called_once()


class TestCLITUIConsistency:
    """CLI/TUI一貫性テスト"""
    
    @pytest.fixture
    def cli(self):
        return SStyleAgentCLI(use_async=True)
    
    @pytest.fixture  
    def tui_app(self):
        return MainTUIApp()
    
    def test_shared_agent_service(self, cli, tui_app):
        """共通サービス使用の確認"""
        # 両方とも AgentService を使用していることを確認
        assert hasattr(cli, 'agent_service')
        assert hasattr(tui_app, 'agent_service')
        
        # 同じ型のサービスを使用していることを確認
        assert type(cli.agent_service).__name__ == 'AgentService'
        assert type(tui_app.agent_service).__name__ == 'AgentService'
    
    @pytest.mark.asyncio
    async def test_consistent_s_expression_evaluation(self, cli, tui_app):
        """S式評価の一貫性テスト"""
        test_expr = "(calc \"10+5\")"
        mock_result = 15
        
        # 両方のサービスで同じ結果が返されることを確認
        cli.agent_service.evaluate_s_expression = AsyncMock(return_value=mock_result)
        tui_app.agent_service.evaluate_s_expression = AsyncMock(return_value=mock_result)
        
        cli_result = await cli.execute_s_expression(test_expr)
        tui_result = await tui_app.evaluate_s_expression(test_expr)
        
        assert cli_result == tui_result == mock_result
    
    @pytest.mark.asyncio
    async def test_consistent_s_expression_generation(self, cli, tui_app):
        """S式生成の一貫性テスト"""
        test_input = "multiply 3 by 4"
        mock_result = "(calc \"3*4\")"
        
        # 両方のサービスで同じ結果が返されることを確認
        cli.agent_service.generate_s_expression = AsyncMock(return_value=mock_result)
        tui_app.agent_service.generate_s_expression = AsyncMock(return_value=mock_result)
        
        cli_result = await cli.generate_s_expression(test_input)
        tui_result = await tui_app.generate_s_expression(test_input)
        
        assert cli_result == tui_result == mock_result
    
    def test_consistent_mode_toggling(self, cli, tui_app):
        """モード切り替えの一貫性テスト"""
        # 初期状態確認
        assert cli.use_async == tui_app.use_async
        
        # Mock両方のサービス
        cli.agent_service.toggle_execution_mode = Mock(return_value="sync")
        cli.agent_service.use_async = False
        
        tui_app.agent_service.toggle_execution_mode = Mock(return_value="sync")
        tui_app.agent_service.use_async = False
        tui_app.update_status_bar = Mock()
        tui_app.notify = Mock()
        
        # 両方でモード切り替え実行
        asyncio.run(cli.toggle_mode())
        tui_app.toggle_execution_mode()
        
        # 結果の一貫性確認
        assert cli.use_async == tui_app.use_async == False


class TestEndToEndWorkflow:
    """エンドツーエンドワークフローテスト"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_cli(self):
        """CLI完全ワークフローテスト"""
        cli = SStyleAgentCLI(use_async=True)
        
        # 1. S式生成
        with patch.object(cli.agent_service, 'generate_s_expression') as mock_gen:
            mock_gen.return_value = "(calc \"7+8\")"
            generated = await cli.generate_s_expression("add 7 and 8")
            assert generated == "(calc \"7+8\")"
        
        # 2. S式実行
        with patch.object(cli.agent_service, 'evaluate_s_expression') as mock_eval:
            mock_eval.return_value = 15
            result = await cli.execute_s_expression(generated)
            assert result == 15
        
        # 3. ベンチマーク実行
        with patch.object(cli.agent_service, 'run_benchmark') as mock_bench:
            mock_bench.return_value = {
                "sync_duration_ms": 100,
                "async_duration_ms": 50,
                "improvement_percent": 50,
                "test_count": 3
            }
            with patch('builtins.print'):
                await cli.run_benchmark()
            mock_bench.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_workflow_tui(self):
        """TUI完全ワークフローテスト"""
        tui = MainTUIApp()
        
        # Mock通知機能
        tui.notify = Mock()
        tui.update_status_bar = Mock()
        
        # 1. S式生成
        with patch.object(tui.agent_service, 'generate_s_expression') as mock_gen:
            mock_gen.return_value = "(notify \"hello world\")"
            generated = await tui.generate_s_expression("say hello world")
            assert generated == "(notify \"hello world\")"
        
        # 2. S式実行  
        with patch.object(tui.agent_service, 'evaluate_s_expression') as mock_eval:
            mock_eval.return_value = "hello world"
            result = await tui.evaluate_s_expression(generated)
            assert result == "hello world"
        
        # 3. ツールテスト
        with patch.object(tui.agent_service, 'test_tools') as mock_test:
            mock_test.return_value = {"notify": {"status": "success"}}
            test_result = await tui.test_tools()
            assert "notify" in test_result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])