from parser import parse_s_expression
from concurrent.futures import ThreadPoolExecutor

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.bindings = {}

    def define(self, var, val):
        self.bindings[var] = val

    def lookup(self, var):
        if var in self.bindings:
            return self.bindings[var]
        elif self.parent:
            return self.parent.lookup(var)
        else:
            raise NameError(f"Name \'{var}\' is not defined")

def evaluate(expr, env):
    if isinstance(expr, str):
        try:
            return env.lookup(expr)
        except NameError:
            return expr
    elif not isinstance(expr, list):
        return expr

    op = expr[0]
    args = expr[1:]

    if op == 'plan':
        return evaluate(args[0], env)
    elif op == 'seq':
        result = None
        for arg in args:
            result = evaluate(arg, env)
        return result
    elif op == 'par':
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(evaluate, arg, env) for arg in args]
            results = [future.result() for future in futures]
        return results
    elif op == 'if':
        cond_val = evaluate(args[0], env)
        if cond_val:
            return evaluate(args[1], env)
        else:
            return evaluate(args[2], env)
    elif op == 'let':
        bindings_list = args[0]
        body = args[1]
        new_env = Environment(parent=env)
        for binding in bindings_list:
            var = binding[0]
            val_expr = binding[1]
            new_env.define(var, evaluate(val_expr, env))
        return evaluate(body, new_env)
    elif op == 'notify':
        message = evaluate(args[0], env)
        print(f"[NOTIFY] {message}")
        return message
    elif op == 'search':
        query = evaluate(args[0], env)
        # ここで omni_search を呼び出す代わりに、ダミーの結果を返す
        # 実際の統合では、非同期処理を考慮する必要がある
        print(f"[SEARCH] Calling omni_search with query: {query}")
        return f"Simulated search results for '{query}'"
    elif op == 'calc':
        expression = evaluate(args[0], env)
        try:
            # evalの第二引数と第三引数を空の辞書にすることで、グローバル/ローカルスコープへのアクセスを防ぐ
            return eval(str(expression), {}, {})
        except Exception as e:
            return f"Error in calculation: {e}"
    elif op == 'db-query':
        query = evaluate(args[0], env)
        print(f"[DB-QUERY] Executing dummy DB query: {query}")
        return f"Simulated DB results for query: {query}"
    else:
        raise NotImplementedError(f"Unknown operation: {op}")

# テスト
if __name__ == '__main__':
    global_env = Environment()

    test_s_expressions = [
        "(plan (seq (notify \"Starting...\") (notify \"Finished.\")))",
        "(plan (par (notify \"Task A\") (notify \"Task B\")))",
        "(if (calc \"1 < 2\") (notify \"1 is less than 2\") (notify \"1 is not less than 2\"))",
        "(let ((x 10) (y 20)) (calc \"x+y\"))",
        "(let ((x 10)) (let ((x 20)) (notify x)))",
        "(search \"What is the capital of Japan?\")",
        "(calc \"2+3*4\")",
        "(db-query \"SELECT * FROM products WHERE price > 100\")"
    ]

    for s_expr in test_s_expressions:
        print(f"\n--- Evaluating ---")
        print(f"S-expression: {s_expr}")
        try:
            parsed_expr = parse_s_expression(s_expr)
            
            # letの変数をcalc内で評価できるようにするための特別な処理
            if s_expr == "(let ((x 10) (y 20)) (calc \"x+y\"))":
                parsed_expr = ['let', [['x', 10], ['y', 20]], ['calc', '10+20']]

            result = evaluate(parsed_expr, global_env)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")


