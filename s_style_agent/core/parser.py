"""
S式パーサー - langchainベース実装

conceptディレクトリのparser.pyをベースに、langchainのtraceability機能を追加
"""

import re
from typing import Any, List, Union
from langchain_core.runnables import RunnableLambda
from langsmith import traceable

# 型エイリアスの定義
SExpression = Union[str, int, float, List['SExpression']]
AtomType = Union[str, int, float]


class SExpressionParseError(Exception):
    """S式パースエラー"""
    pass


@traceable(name="tokenize_s_expression")
def tokenize_s_expression(s_expr_str: str) -> List[str]:
    """S式文字列をトークンに分割"""
    # 括弧、文字列リテラル、シンボル、数値を識別する正規表現
    tokens = re.findall(r'"(?:\\"|[^"])*"|\(|\)|[^\s()]+', s_expr_str)
    return tokens


def parse_atom(token: str) -> AtomType:
    """トークンを適切なPythonの型に変換"""
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]  # 文字列リテラルから引用符を削除
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token  # シンボルとして扱う  # シンボルとして扱う


def parse_from_tokens(tokens: List[str]) -> SExpression:
    """トークンリストから再帰的にS式を解析"""
    if not tokens:
        raise SExpressionParseError('Unexpected EOF while reading')
    
    token = tokens.pop(0)
    
    if token == '(':
        expr_list: List[SExpression] = []
        while tokens and tokens[0] != ')':
            expr_list.append(parse_from_tokens(tokens))
        if not tokens or tokens[0] != ')':
            raise SExpressionParseError('Expected )')
        tokens.pop(0)  # pop ')'
        return expr_list
    elif token == ')':
        raise SExpressionParseError('Unexpected )')
    else:
        return parse_atom(token)


def parse_s_expression(s_expr_str: str) -> SExpression:
    """
    S式文字列を解析し、Pythonのリストとアトムの構造に変換
    
    Args:
        s_expr_str: S式の文字列表現
        
    Returns:
        解析されたS式のPython表現
        
    Raises:
        SExpressionParseError: パースエラーが発生した場合
    """
    try:
        tokens = tokenize_s_expression(s_expr_str)
        if not tokens:
            raise SExpressionParseError('Empty expression')
        
        result = parse_from_tokens(tokens)
        
        # 残りのトークンがある場合はエラー
        if tokens:
            raise SExpressionParseError(f'Unexpected tokens after expression: {tokens}')
            
        return result
    except Exception as e:
        if isinstance(e, SExpressionParseError):
            raise
        raise SExpressionParseError(f'Parse error: {str(e)}')


# Langchain Runnable として公開
parser_runnable = RunnableLambda(parse_s_expression)


if __name__ == "__main__":
    # テストケース
    test_cases = [
        "(plan (seq step1 step2))",
        "(plan (par stepA stepB))",
        "(if cond then else)",
        "(let ((var expr)) body)",
        "(notify \"hello world\")",
        "(search \"query with spaces\")",
        "(calc \"2+3*4\")",
        "(db-query \"SELECT * FROM users\")",
        "(plan (seq (notify \"start\") (search \"data\") (notify \"end\")))",
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Input: {case}")
        try:
            parsed = parse_s_expression(case)
            print(f"Parsed: {parsed}")
        except SExpressionParseError as e:
            print(f"Error: {e}")