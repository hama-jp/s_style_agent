#!/usr/bin/env python3
"""
サンプルデータでの検索結果抽出テスト
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from s_style_agent.tools.search_result_extractor import search_extractor


async def test_sample_extraction():
    """サンプルデータでの抽出テスト"""
    print("=== サンプルデータでの検索結果抽出テスト ===")
    
    try:
        # サンプル検索結果
        sample_result = {
            'content': [{'type': 'text', 'text': 'Title: 高松市役所（高松市/市役所・区役所・役場）の地図｜地図マピオン\nDescription: 地図マピオンが提供する高松市役所（高松市/市役所・区役所・役場）の詳細地図。<strong>中心点の緯度経度は[34.34275059,134.04663029]、マップコード[60 605 687*61]、標高(海抜)3m</strong>。最寄り駅、バス停、ルート検索、距離測定、天気も...\nURL: https://www.mapion.co.jp/m2/34.34275059,134.04663029,16/poi=ILSP0000000798_ipclm\n\nTitle: 高松市役所（香川県高松市） - Yahoo!くらし\nDescription: <strong>高松市役所</strong> · 公式サイト · 地域一覧 · タカマツシヤクショ · 住所 · 開庁時間 · 電話番号 · 〒760-8571 香川県高松市番町1丁目8-15 · 詳細な地図を見る · 高松琴平電気鉄道瓦町駅 西出口から徒歩約11分 ·\nURL: https://kurashi.yahoo.co.jp/facility/a372010001\n\nTitle: 高松市役所 | たかまつユニバーサルデザインマップ\nDescription: http://www.city.takamatsu.kagawa.jp/kurashi/shinotorikumi/profile/info/shiyakusho/annnai.html\nURL: https://takamatsu-udmap.jp/ud/2019021803536/'}], 'isError': False}
        
        print("1. 検索結果抽出実行中...")
        query = "高松市役所 座標"
        
        # 抽出実行
        extracted = search_extractor.extract_information(query, sample_result)
        
        print(f"\n2. 元の検索クエリ: {query}")
        print(f"元のデータサイズ: {len(str(sample_result))} 文字")
        
        print("\n3. 抽出された情報:")
        print("=" * 60)
        print(extracted)
        print("=" * 60)
        
        print(f"\n4. 抽出後データサイズ: {len(extracted)} 文字")
        
        # 結果分析
        print("\n5. 抽出結果分析:")
        analysis_results = []
        
        if "34.34275059" in extracted and "134.04663029" in extracted:
            analysis_results.append("✅ 座標情報（緯度・経度）が正常に抽出")
        elif "緯度" in extracted and "経度" in extracted:
            analysis_results.append("✅ 座標情報が抽出された")
        else:
            analysis_results.append("❌ 座標情報が抽出されていない")
        
        if "高松市番町" in extracted or "番町1丁目8-15" in extracted:
            analysis_results.append("✅ 住所情報が抽出された")
        else:
            analysis_results.append("⚠️  住所情報が明確でない")
        
        if "760-8571" in extracted:
            analysis_results.append("✅ 郵便番号が抽出された")
        
        if len(extracted) < len(str(sample_result)) * 0.3:
            analysis_results.append("✅ 情報が適切に要約された（元の30%以下）")
        else:
            analysis_results.append("⚠️  要約が十分でない可能性")
        
        for result in analysis_results:
            print(f"   {result}")
        
        # 別のクエリでもテスト
        print("\n6. 別のクエリでのテスト...")
        query2 = "高松市役所 電話番号"
        extracted2 = search_extractor.extract_information(query2, sample_result)
        
        print(f"クエリ: {query2}")
        print("抽出結果:")
        print("-" * 40)
        print(extracted2)
        print("-" * 40)
        
        if "087-839-2011" in extracted2:
            print("✅ 電話番号が抽出された")
        else:
            print("⚠️  電話番号が見つからない")
        
        print("\n✅ サンプルデータでの抽出テスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_sample_extraction())