import re

def parse_s_expression(s_expr_str):
    """
    S式文字列を解析し、Pythonのリストとアトムの構造に変換する。
    """
    # トークン化
    # 括弧、文字列リテラル、シンボル、数値を識別する正規表現
    # 文字列リテラルは、内部の括弧やスペースを無視するように特別に処理する
    tokens = re.findall(r'"(?:\\"|[^"])*"|\(|\)|[^\s()]+', s_expr_str)
    
    def read_from_tokens(tokens_list):
        if not tokens_list:
            raise SyntaxError('Unexpected EOF while reading')
        
        token = tokens_list.pop(0)
        
        if token == '(':
            L = []
            while tokens_list and tokens_list[0] != ')':
                L.append(read_from_tokens(tokens_list))
            if not tokens_list or tokens_list[0] != ')':
                raise SyntaxError('Expected )')
            tokens_list.pop(0) # pop ')'
            return L
        elif token == ')':
            raise SyntaxError('Unexpected )')
        else:
            return atom(token)
            
    def atom(token):
        """文字列を適切なPythonの型に変換する。"""
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1] # 文字列リテラルから引用符を削除
        try:
            return int(token)
        except ValueError:
            try:
                return float(token)
            except ValueError:
                return token # シンボルとして扱う
                
    return read_from_tokens(tokens)

# テスト
if __name__ == '__main__':
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
        "(if (calc \"1>0\") (notify \"true\") (notify \"false\"))",
        "(let ((x 10) (y \"hello\")) (seq (notify x) (notify y)))"
    ]

    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Input: {case}")
        try:
            parsed = parse_s_expression(case)
            print(f"Parsed: {parsed}")
        except SyntaxError as e:
            print(f"Error: {e}")

    # エラーケース
    print("\n--- Error Cases ---")
    error_cases = [
        "(plan (seq step1 step2)", # 閉じ括弧不足
        "(if cond then)", # 引数不足
        "(notify \"unterminated string)", # 閉じ引用符不足
        ")(" # 不正な括弧
    ]
    for i, case in enumerate(error_cases):
        print(f"\n--- Error Case {i+1} ---")
        print(f"Input: {case}")
        try:
            parsed = parse_s_expression(case)
            print(f"Parsed: {parsed}")
        except SyntaxError as e:
            print(f"Error: {e}")


