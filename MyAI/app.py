import streamlit as st
import datetime
import os
import subprocess

# --- 1. セキュアな方法でAPIキーをセット（Streamlit Cloud用） ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]  # secrets.toml or Streamlit Cloud secretsに必ず設定

URIAGE_FILE = "uriage.txt"
CHART_FILE = "sales_chart.png"
MASTER_FILE = "master_data.txt"

# 商品マスター情報の読み書き用関数
def load_master_data():
    """master_data.txtから商品名・金額・原価の辞書を返す"""
    master = {}
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    name, price, cost = parts[0], parts[1], parts[2]
                    try:
                        master[name] = {
                            "price": int(price),
                            "cost": int(cost)
                        }
                    except ValueError:
                        continue
    return master

def save_master_data(master):
    """商品マスター辞書をファイルに保存"""
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        for name, info in master.items():
            f.write(f"{name}, {info['price']}, {info['cost']}\n")

def append_sales(product_name, price, cost):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    profit = price - cost
    with open(URIAGE_FILE, "a", encoding="utf-8") as f:
        # 「日時, 商品名, 売上金額, 利益」
        f.write(f"{now}, {product_name}, {price}, {profit}\n")

def calc_total_sales():
    total = 0
    if os.path.exists(URIAGE_FILE):
        with open(URIAGE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = [p.strip() for p in line.strip().split(",")]
                if len(parts) >= 3:
                    try:
                        total += int(parts[2])
                    except ValueError:
                        continue
    return total

# サイドバーのメニュー（『商品設定』を追加）
st.sidebar.title("ショップ管理メニュー")
menu = st.sidebar.radio(
    "メニューを選択してください",
    ("売上入力", "集計表示", "AI相談", "商品設定")
)

# 1. 売上入力画面
if menu == "売上入力":
    st.header("売上入力")
    product_info = load_master_data()
    if not product_info:
        st.warning("まず『商品設定』から商品を登録してください。")
    else:
        product = st.selectbox(
            "商品を選択してください",
            list(product_info.keys()),
            key="product"
        )
        price = product_info[product]["price"]
        cost = product_info[product]["cost"]
        st.write(f"金額: {price}円")
        st.write(f"原価: {cost}円")

        if st.button("この内容で売上記録！"):
            append_sales(product, price, cost)
            st.success("売上を記録しました！")

# 2. 集計表示
elif menu == "集計表示":
    st.header("売上集計表示")
    total = calc_total_sales()
    st.subheader(f"現在の売上合計: {total} 円")

    # --- パワーアップ: 最新グラフ作成ボタン追加 ---
    if st.button("最新のグラフで集計を見る"):
        with st.spinner("グラフを作成中..."):
            try:
                # graph.py（グラフ作成スクリプト）を実行
                result = subprocess.run(
                    ["python", "graph.py"],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    st.error("グラフ生成（graph.py）でエラーが発生しました。")
                    st.text(result.stderr)
                else:
                    st.info("最新のグラフを作成しました。")
            except Exception as e:
                st.error(f"グラフ作成の実行中にエラーが発生しました: {e}")

    # sales_chart.pngが存在していれば表示、なければ注意喚起
    if os.path.exists(CHART_FILE):
        st.image(CHART_FILE, caption="商品別売上集計グラフ")
    else:
        st.warning("グラフ画像（sales_chart.png）が存在しません。\n[最新のグラフで集計を見る]ボタンを押してグラフを更新してください。")

# 3. AI相談
elif menu == "AI相談":
    st.header("AIコンサルのアドバイス")
    product_info = load_master_data()
    if not product_info:
        st.warning("『商品設定』からまず商品を登録してください。")
    elif st.button("AIに売上を分析してもらう！"):
        with st.spinner("AIが売上データを分析中..."):
            try:
                # secretsが空文字や未設定の場合の対応
                if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
                    st.error("Google APIキーが設定されていません。")
                else:
                    from google import genai

                    # 売上データの読み込み
                    if not os.path.exists(URIAGE_FILE):
                        st.error("売上データuriage.txtがありません。")
                    else:
                        with open(URIAGE_FILE, "r", encoding="utf-8") as f:
                            uriage_content = f.read()

                        prompt = (
                            "あなたは10年の経験を持つ敏腕経営コンサルタントです。\n"
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

                        client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt
                        )
                        st.markdown("#### --- AIアドバイザーからの回答 ---")
                        st.write(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

# 4. 商品設定
elif menu == "商品設定":
    st.header("商品設定（商品名・金額・原価の登録）")
    master = load_master_data()
    with st.form("add_product_form", clear_on_submit=True):
        new_name = st.text_input("商品名（例: コーヒー）", max_chars=30)
        new_price = st.number_input("販売価格[円]", min_value=1, value=500)
        new_cost = st.number_input("原価[円]", min_value=0, value=100)
        add_button = st.form_submit_button("商品を登録・更新する")
        updated = False

    if add_button:
        if new_name.strip() == "":
            st.error("商品名を入力してください。")
        else:
            master[new_name.strip()] = {"price": int(new_price), "cost": int(new_cost)}
            save_master_data(master)
            st.success(f"商品「{new_name.strip()}」を登録（または更新）しました。")
            updated = True

    # 商品一覧の表示
    master = load_master_data()  # 最新情報取得
    if master:
        st.markdown("### ▼ 登録済み商品")
        for pname, info in master.items():
            st.write(f"- {pname}: 販売価格 {info['price']}円 / 原価 {info['cost']}円")
    else:
        st.info("まだ商品が登録されていません。")

# --- requirements.txtの内容（このファイルをプロジェクト直下に新規で作成してください） ---
# requirements.txt ------------------
# streamlit
# google-generativeai
# matplotlib
# japanize-matplotlib
# pandas
# numpy
# -----------------------------------

# --- graph.py 側のフォント設定例（matplotlib使用時。MS Gothicなど安全なフォント指定を追記してください）---
# （graph.pyの冒頭に下記を必ず追加・修正してください。）
"""
import matplotlib
# Windows環境やStreamlit Cloudでは 'MS Gothic' が無い場合 'IPAexGothic' など fallback
# ここでは 'MS Gothic' があれば優先、なければ IPAexGothic や DejaVu Sans を fallback
import matplotlib.pyplot as plt

font_candidates = ["MS Gothic", "IPAexGothic", "Yu Gothic", "Meiryo", "TakaoGothic", "Noto Sans CJK JP", "DejaVu Sans"]
for f in font_candidates:
    try:
        matplotlib.rc("font", family=f)
        # テスト用: plt.figure().text(0.1, 0.5, 'テスト', fontsize=12)
        break
    except Exception:
        continue
matplotlib.rcParams['axes.unicode_minus'] = False
"""
