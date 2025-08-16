"""
検索結果抽出・要約ツール

検索APIの生データをLLMを使って必要な情報に抽出・要約
"""

import json
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langsmith import traceable


class SearchResultExtractor:
    """検索結果抽出・要約クラス"""
    
    def __init__(self, llm_base_url: str = "http://192.168.79.1:1234/v1",
                 model_name: str = "openai/gpt-oss-20b"):
        self.llm = ChatOpenAI(
            base_url=llm_base_url,
            api_key="dummy",
            model=model_name,
            temperature=0.1  # 事実抽出のため低めに設定
        )
    
    @traceable(name="extract_search_info")
    def extract_information(self, query: str, search_result: Dict[str, Any]) -> str:
        """検索結果から必要な情報を抽出"""
        try:
            # 検索結果を解析
            content = self._parse_search_result(search_result)
            
            if not content:
                return "検索結果が見つかりませんでした。"
            
            # LLMで情報抽出
            extracted_info = self._extract_with_llm(query, content)
            
            return extracted_info
            
        except Exception as e:
            return f"検索結果の抽出でエラーが発生しました: {e}"
    
    def _parse_search_result(self, search_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """検索結果を解析して構造化データに変換"""
        try:
            if not isinstance(search_result, dict):
                return []
            
            content = search_result.get('content', [])
            if not content:
                return []
            
            # テキストコンテンツから情報を抽出
            parsed_results = []
            for item in content:
                if item.get('type') == 'text':
                    text = item.get('text', '')
                    
                    # Title, Description, URLを抽出
                    entries = self._extract_entries_from_text(text)
                    parsed_results.extend(entries)
            
            return parsed_results
            
        except Exception as e:
            print(f"[SEARCH] 検索結果解析エラー: {e}")
            return []
    
    def _extract_entries_from_text(self, text: str) -> List[Dict[str, str]]:
        """テキストからTitle, Description, URLのエントリを抽出"""
        entries = []
        lines = text.split('\n')
        
        current_entry = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_entry:
                    entries.append(current_entry.copy())
                    current_entry = {}
                continue
            
            if line.startswith('Title: '):
                if current_entry:
                    entries.append(current_entry.copy())
                current_entry = {'title': line[7:]}
            elif line.startswith('Description: '):
                current_entry['description'] = line[13:]
            elif line.startswith('URL: '):
                current_entry['url'] = line[5:]
        
        # 最後のエントリを追加
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    @traceable(name="llm_extract_search_info")
    def _extract_with_llm(self, query: str, content: List[Dict[str, str]]) -> str:
        """LLMを使って検索結果から必要な情報を抽出"""
        # 検索結果を整理してプロンプトに含める
        formatted_results = []
        for i, entry in enumerate(content[:5], 1):  # 最大5件まで
            title = entry.get('title', '不明')
            description = entry.get('description', '説明なし')
            url = entry.get('url', '')
            
            formatted_results.append(f"{i}. {title}\n   説明: {description}\n   URL: {url}")
        
        results_text = '\n\n'.join(formatted_results)
        
        prompt = f"""あなたは検索結果から必要な情報を抽出する専門家です。

ユーザーの検索クエリ: "{query}"

検索結果:
{results_text}

上記の検索結果から、ユーザーのクエリに最も関連する重要な情報を抽出して、簡潔で読みやすい形式で回答してください。

抽出指針:
- ユーザーが求めている具体的な情報（座標、住所、電話番号、営業時間など）を優先
- 信頼できそうな情報源からの情報を優先
- 重複する情報は統合
- 不明確な情報は含めない
- 簡潔で分かりやすい日本語で回答

回答:"""

        try:
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            return response.content.strip()
        except Exception as e:
            print(f"[SEARCH] LLM抽出エラー: {e}")
            # フォールバック: 基本的な情報抽出
            return self._basic_extract(query, content)
    
    def _basic_extract(self, query: str, content: List[Dict[str, str]]) -> str:
        """基本的な情報抽出（LLM失敗時のフォールバック）"""
        if not content:
            return "関連する情報が見つかりませんでした。"
        
        # 最初の結果から基本情報を抽出
        first_result = content[0]
        title = first_result.get('title', '不明')
        description = first_result.get('description', '')
        
        result = f"検索結果: {title}\n"
        if description:
            result += f"詳細: {description}\n"
        
        # 座標情報があれば抽出
        coordinates = self._extract_coordinates(description)
        if coordinates:
            result += f"座標: {coordinates}\n"
        
        return result.strip()
    
    def _extract_coordinates(self, text: str) -> Optional[str]:
        """テキストから座標情報を抽出"""
        import re
        
        # 緯度経度パターンを検索
        patterns = [
            r'緯度経度は\[([0-9.]+),([0-9.]+)\]',
            r'lat.*?([0-9.]+).*?lng.*?([0-9.]+)',
            r'([0-9.]+),([0-9.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                lat, lng = match.groups()
                return f"緯度: {lat}, 経度: {lng}"
        
        return None


# グローバルインスタンス
search_extractor = SearchResultExtractor()