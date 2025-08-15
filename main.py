#!/usr/bin/env python3
"""
S式エージェントシステム メインエントリーポイント
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをpythonpathに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from s_style_agent.cli.main import main

if __name__ == "__main__":
    asyncio.run(main())