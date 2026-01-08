from google import genai

# 1. あなたのAPIキーをここに入れてください
API_KEY = "AIzaSyDwyMsY2bs6R_pTQlsBdEBNWugJiVXkWng"

def main():
    try:
        # 2. 最新のAIクライアントを作成
        client = genai.Client(api_key=API_KEY)

        # 3. 売上データを読み込む
        with open("uriage.txt", "r", encoding="utf-8") as f:
            uriage_content = f.read()

        # 4. uriage.txtの新しい形式（「売上金額」と「利益」が含まれている）に合わせて、より深い分析をAIに依頼するプロンプトを作成
        prompt = (
            "あなたは10年の経験を持つ敏腕経営コンサルタントです。\n"
            "これから、" 
            "以下の売上履歴(uriage.txt)と、それをもとに作成された売上グラフ（sales_chart.png）があると仮定します。\n"
            "\n"
            "【アドバイス指示】\n"
            "1. 以下の売上履歴は1行ごとに「日時, 商品名, 売上金額, 利益」というフォーマットで記録されています。\n"
            "2. あなたはこのデータから、単なる売上合計だけでなく、以下を必ず計算し解説してください：\n"
            "   - 「全体の売上合計」\n"
            "   - 「全体のトータル利益（利益合計）」\n"
            "   - 「全体の利益率（トータル利益÷売上合計）」\n"
            "   - 商品別に売上・利益・利益率をまとめ、それぞれ商品ごとに比較・解説してください。\n"
            "3. 特に「どの商品が効率よく儲かっているか（利益額・利益率が高いか）」を明確に指摘してください。\n"
            "4. 利益を最大化するための戦略や提案（例：どの商品を重点的に売ると良いか、セット販売や価格調整のアイデアなど）を複数案、具体的に提案してください。\n"
            "5. 明日の売上や利益の予測も、なるべく数値を使って論理的に述べてください。\n"
            "6. 明日のチャレンジに向けて店長が前向きになれる一言メッセージも最後に添えてください。\n"
            "\n"
            "【制約と補足】\n"
            "- 分析や提案ではsales_chart.png（商品別売上棒グラフ）も参照した体裁ですが、数値や予測の根拠は必ずuriage.txtの履歴のみを使ってください。\n"
            "- 提案は現実的かつ短期的にも実行しやすいものを必ず含めてください。\n"
            "\n"
            "売上履歴(uriage.txt)：\n"
            f"{uriage_content}"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # 5. アドバイスを表示
        print("\n--- AIアドバイザーからの回答 ---\n")
        print(response.text)

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()