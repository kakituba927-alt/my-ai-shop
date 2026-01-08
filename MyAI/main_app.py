import subprocess

def main_menu():
    while True:
        print("==== ショップ管理メニュー ====")
        print("1: 売上を入力する（test.pyを実行）")
        print("2: 売上を集計する（summary.pyを実行）")
        print("3: グラフを表示・更新する（graph.pyを実行）")
        print("4: AIコンサルの助言を聞く（ai_advisor.pyを実行）")
        print("5: 終了する")

        choice = input("番号を選んでください（1-5）: ").strip()
        if choice == "1":
            subprocess.run(["python", "test.py"], check=False)
        elif choice == "2":
            subprocess.run(["python", "summary.py"], check=False)
        elif choice == "3":
            subprocess.run(["python", "graph.py"], check=False)
        elif choice == "4":
            subprocess.run(["python", "ai_advisor.py"], check=False)
        elif choice == "5":
            print("終了します。ご利用ありがとうございました！")
            break
        else:
            print("正しい番号を入力してください。")
        print()

if __name__ == "__main__":
    main_menu()
