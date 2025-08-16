#!/usr/bin/env python3
"""
ローカルLLMサーバーの動作確認テスト
"""

import requests
import json

def test_local_llm():
    base_url = "http://localhost:1234/v1"  # GitHub公開用にlocalhost表記に変更
    model_name = "openai/gpt-oss-20b"
    
    # APIエンドポイントの確認
    endpoints_to_test = [
        f"{base_url}/models",
        f"{base_url}/chat/completions"
    ]
    
    print("=== ローカルLLMサーバー動作テスト ===")
    
    # 1. モデル一覧の取得テスト
    print("\n1. モデル一覧の取得テスト")
    try:
        response = requests.get(f"{base_url}/models", timeout=60)
        if response.status_code == 200:
            models = response.json()
            print("✓ モデル一覧取得成功")
            print(f"利用可能モデル: {json.dumps(models, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ モデル一覧取得失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
    except Exception as e:
        print(f"✗ モデル一覧取得エラー: {e}")
    
    # 2. チャット完了APIのテスト
    print("\n2. チャット完了APIのテスト")
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user", 
                    "content": "Hello! Can you respond in Japanese?"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = requests.post(
            f"{base_url}/chat/completions", 
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ チャット完了API成功")
            print(f"応答: {result['choices'][0]['message']['content']}")
        else:
            print(f"✗ チャット完了API失敗: {response.status_code}")
            print(f"レスポンス: {response.text}")
            
    except Exception as e:
        print(f"✗ チャット完了APIエラー: {e}")
    
    # 3. S式生成テスト
    print("\n3. S式生成テスト")
    try:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": """あなたはS式を生成するエージェントです。ユーザーの要求をS式で表現してください。
利用可能な関数:
- (seq step1 step2 ...): 順次実行
- (par stepA stepB ...): 並列実行  
- (notify "msg"): ユーザー通知
- (search "query"): 情報検索
- (calc "expression"): 数式計算

S式のみを返してください。"""
                },
                {
                    "role": "user", 
                    "content": "今日の天気を調べて教えて"
                }
            ],
            "temperature": 0.3,
            "max_tokens": 200
        }
        
        response = requests.post(
            f"{base_url}/chat/completions", 
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            s_expression = result['choices'][0]['message']['content'].strip()
            print("✓ S式生成成功")
            print(f"生成されたS式: {s_expression}")
        else:
            print(f"✗ S式生成失敗: {response.status_code}")
            
    except Exception as e:
        print(f"✗ S式生成エラー: {e}")

if __name__ == "__main__":
    test_local_llm()