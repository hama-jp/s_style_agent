"""
pytest設定ファイル

S式エージェントシステムのテスト用共通設定
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))