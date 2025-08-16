#!/usr/bin/env python3
"""
検索結果抽出機能のテスト
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.mcp.manager import mcp_manager
from s_style_agent.core.evaluator import evaluate_s_expression
from s_style_agent.tools.search_result_extractor import search_extractor


async def test_search_extraction():
    """検索結果抽出機能テスト"""
    print("=== 検索結果抽出機能テスト ===")
    
    try:
        # 1. MCPシステム初期化
        print("\n1. MCPシステム初期化...")
        success = await mcp_manager.initialize()
        
        if not success:
            print("❌ MCP初期化に失敗しました")
            return
        
        print("✅ MCP初期化完了")
        
        # 2. 検索結果抽出機能のテスト（レート制限のため1回のみ）
        print("\n2. 検索結果抽出テスト...")
        
        # ユーザー確認
        print("実際の検索を1回実行して抽出機能をテストします。")
        confirm = input("実行しますか？ (y/n): ").strip().lower()
        
        if confirm == 'y':
            # 検索実行
            s_expr = '(search "高松市役所 座標")'
            print(f"検索S式: {s_expr}")
            print("検索実行中...")
            
            result = evaluate_s_expression(s_expr, "抽出機能テスト")
            
            print(f"\n✅ 抽出後の検索結果:")
            print("=" * 50)
            print(result)
            print("=" * 50)
            
            # 結果の分析
            if "緯度" in result and "経度" in result:
                print("✅ 座標情報が正常に抽出されました")
            if "住所" in result or "番町" in result:
                print("✅ 住所情報が含まれています")
            if len(result) < 500:  # 元の結果より短い場合
                print("✅ 情報が適切に要約されています")
            
        else:
            print("検索をスキップしました")
            
            # 代わりにサンプルデータでテスト
            print("\n3. サンプルデータでの抽出テスト...")
            
            sample_result = {
                'content': [{'type': 'text', 'text': 'Title: 高松市役所（高松市/市役所・区役所・役場）の地図｜地図マピオン\nDescription: 地図マピオンが提供する高松市役所（高松市/市役所・区役所・役場）の詳細地図。<strong>中心点の緯度経度は[34.34275059,134.04663029]、マップコード[60 605 687*61]、標高(海抜)3m</strong>。最寄り駅、バス停、ルート検索、距離測定、天気も...\nURL: https://www.mapion.co.jp/m2/34.34275059,134.04663029,16/poi=ILSP0000000798_ipclm\n\nTitle: 高松市役所（香川県高松市） - Yahoo!くらし\nDescription: <strong>高松市役所</strong> · 公式サイト · 地域一覧 · タカマツシヤクショ · 住所 · 開庁時間 · 電話番号 · 〒760-8571 香川県高松市番町1丁目8-15 · 詳細な地図を見る · 高松琴平電気鉄道瓦町駅 西出口から徒歩約11分 ·\nURL: https://kurashi.yahoo.co.jp/facility/a372010001'}], 'isError': False}
            
            extracted = search_extractor.extract_information("高松市役所 座標", sample_result)
            
            print("サンプル抽出結果:")
            print("=" * 50)
            print(extracted)
            print("=" * 50)
            
            if "34.34275059" in extracted and "134.04663029" in extracted:
                print("✅ 座標情報が正常に抽出されました")
            if "高松市番町" in extracted:
                print("✅ 住所情報が抽出されました")
            print("✅ サンプルデータでの抽出テスト完了")
        
        print("\n✅ 検索結果抽出機能テスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # クリーンアップ
        print("\n4. クリーンアップ...")
        if mcp_manager.initialized:
            await mcp_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(test_search_extraction())