#!/usr/bin/env python3
"""
while構文シンプルテスト
"""

import os
from s_style_agent.core.evaluator import ContextualEvaluator, Environment
from s_style_agent.core.parser import parse_s_expression

# LangSmith設定
os.environ['LANGSMITH_PROJECT'] = 's-style-agent'
os.environ['LANGSMITH_TRACING'] = 'true'

def test_basic_operations():
    """基本操作のテスト"""
    print("=== 基本操作テスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 1. 算術演算テスト
    print("\n1. 算術演算:")
    expr = parse_s_expression('(+ 1 2)')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"(+ 1 2) = {result}")
    
    # 2. 比較演算テスト
    print("\n2. 比較演算:")
    expr = parse_s_expression('(< 1 3)')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"(< 1 3) = {result}")
    
    # 3. 変数定義とset
    print("\n3. 変数操作:")
    expr = parse_s_expression('(let (("x" 5)) x)')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"let x=5: {result}")

def test_simple_while():
    """シンプルなwhile構文テスト"""
    print("\n=== シンプルwhile構文テスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    
    # 1. 基本while（変数事前定義）
    print("\n1. 基本while:")
    env.define("counter", 0)  # 事前に変数定義
    
    # シンプルなwhileループ
    expr = parse_s_expression('''
    (while (< counter 3)
        (seq
            (notify counter)
            (set counter (+ counter 1)))
        10)
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")
    
    # 2. 条件が最初から偽
    print("\n2. 条件偽:")
    expr = parse_s_expression('(while (< 5 3) (notify "実行されない") 5)')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")

def test_max_iterations():
    """最大反復数テスト"""
    print("\n=== 最大反復数テスト ===")
    
    evaluator = ContextualEvaluator()
    env = Environment()
    env.define("i", 0)
    
    # 最大3回に制限
    print("最大3回反復:")
    expr = parse_s_expression('''
    (while (< i 100)
        (seq
            (notify i)
            (set i (+ i 1)))
        3)
    ''')
    result = evaluator.evaluate_with_context(expr, env)
    print(f"結果: {result}")

def main():
    """メインテスト実行"""
    print("while構文シンプルテスト開始")
    
    test_basic_operations()
    test_simple_while()
    test_max_iterations()
    
    print("\n✅ while構文シンプルテスト完了！")

if __name__ == "__main__":
    main()