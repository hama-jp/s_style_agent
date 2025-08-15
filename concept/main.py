from llm_agent import run_agent

def main():
    print("S式ベースのエージェントプロトタイプへようこそ！")
    print("終了するには 'exit' と入力してください。")

    while True:
        user_input = input("\nあなたの要求: ")
        if user_input.lower() == 'exit':
            print("エージェントを終了します。")
            break
        
        response = run_agent(user_input)
        print(f"エージェント応答: {response}")

if __name__ == '__main__':
    main()


