from parser import parse_s_expression
from evaluator import evaluate, Environment

# ダミーのLLM呼び出し関数
# 実際には、ここにGemini APIなどのLLM呼び出しロジックが入る
def call_llm(prompt):
    print(f"[LLM] Calling LLM with prompt:\n---\n{prompt}\n---")
    # ここでは、テスト用のS式を返す
    if "今日の天気" in prompt:
        return "(seq (notify \"今日の天気は晴れです\") (search \"今日の天気\"))"
    elif "2+3*4" in prompt:
        return "(calc \"2+3*4\")"
    elif "自己紹介" in prompt:
        return "(notify \"私はS式ベースのエージェントです。\")"
    else:
        return "(notify \"理解できませんでした。\")"

def run_agent(user_query):
    print(f"[AGENT] User query: {user_query}")

    # 1. LLMに計画を生成させるためのプロンプトを作成
    # ここでは簡略化しているが、実際には利用可能なツールや過去の対話履歴などを含める
    prompt = f"ユーザーの要求をS式で表現してください。利用可能な関数は以下の通りです。\n\n"
    prompt += "- (plan (seq step1 step2 ...)): 順次実行\n"
    prompt += "- (plan (par stepA stepB ...)): 並列実行\n"
    prompt += "- (if cond then else): 条件分岐\n"
    prompt += "- (let ((var expr) ...) body): 変数束縛\n"
    prompt += "- (notify \"msg\"): ユーザー通知\n"
    prompt += "- (search \"query\"): 情報検索\n"
    prompt += "- (calc \"expression\"): 数式計算\n"
    prompt += "- (db-query \"query\"): データベースクエリ\n\n"
    prompt += f"ユーザーの要求: {user_query}\n"
    prompt += "S式: "

    # 2. LLMを呼び出し、S式を取得
    s_expression_str = call_llm(prompt)
    print(f"[AGENT] LLM generated S-expression: {s_expression_str}")

    # 3. S式をパース
    try:
        parsed_s_expression = parse_s_expression(s_expression_str)
        print(f"[AGENT] Parsed S-expression: {parsed_s_expression}")
    except SyntaxError as e:
        print(f"[AGENT] Error parsing S-expression: {e}")
        return f"S式の解析エラー: {e}"

    # 4. S式を評価
    global_env = Environment()
    try:
        result = evaluate(parsed_s_expression, global_env)
        print(f"[AGENT] Evaluation result: {result}")
        return f"実行結果: {result}"
    except Exception as e:
        print(f"[AGENT] Error evaluating S-expression: {e}")
        return f"S式の実行エラー: {e}"

if __name__ == '__main__':
    print("--- Agent Test: 今日の天気 ---")
    run_agent("今日の天気は？")

    print("\n--- Agent Test: 計算 ---")
    run_agent("2+3*4を計算して")

    print("\n--- Agent Test: 自己紹介 ---")
    run_agent("自己紹介して")

    print("\n--- Agent Test: 不明なクエリ ---")
    run_agent("何か面白い話をして")


