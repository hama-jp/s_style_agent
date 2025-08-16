#!/usr/bin/env python3
"""
CLI経由での検索結果抽出テスト（1回のみ）
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.manager import mcp_manager
from s_style_agent.core.evaluator import evaluate_s_expression


async def test_cli_extraction():
    """CLI経由での抽出テスト"""
    print("=== CLI経由での検索結果抽出テスト ===")
    
    try:
        # 1. MCPシステム初期化
        print("\n1. MCPシステム初期化...")
        success = await mcp_manager.initialize()
        
        if not success:
            print("❌ MCP初期化に失敗しました")
            return
        
        print("✅ MCP初期化完了")
        
        # 2. 検索実行（1回のみ、レート制限考慮）
        print("\n2. 検索結果抽出機能付きの検索実行...")
        print("クエリ: 東京駅 住所")
        print("検索実行中...")
        
        s_expr = '(search "東京駅 住所")'
        result = evaluate_s_expression(s_expr, "CLI抽出テスト")
        
        print("\n3. 抽出後の最終結果:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        # 結果の評価
        print("\n4. 結果評価:")
        if "住所" in result or "東京都" in result:
            print("✅ 住所情報が含まれている")
        if len(result) < 1000:  # 生データよりコンパクト
            print("✅ 情報が適切に要約されている")
        if "東京駅" in result:
            print("✅ 検索対象が明確に含まれている")
        
        print("\n✅ CLI経由での検索結果抽出テスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n5. クリーンアップ...")
        if mcp_manager.initialized:
            await mcp_manager.shutdown()


if __name__ == "__main__":
    print("注意: このテストは実際のBrave Search APIを1回使用します")
    print("レート制限を考慮して実行します...")
    asyncio.run(test_cli_extraction())