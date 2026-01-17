import streamlit as st
import datetime
import os
import subprocess
import sys
import pandas as pd
import numpy as np
import japanize_matplotlib  # ★ 日本語グラフ化け防止のため必ずimport

# --- 1. セキュアな方法でAPIキーをセット（Streamlit Cloud用） ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]  # secrets.toml or Streamlit Cloud secretsに必ず設定

# ====== ファイル名を"MyAI/"無しに統一 ======
URIAGE_FILE = "uriage.txt"
CHART_FILE = "sales_chart.png"
MASTER_FILE = "master_data.txt"
GRAPH_FILE = "graph.py"

def ensure_file_exists(path):
    """指定のファイルが存在しなければ空ファイルを作成する。"""
    # グラフ等の画像/pyファイルは確認しない
    if path in [CHART_FILE, GRAPH_FILE]:
        return
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass

# 商品マスター情報の読み書き用関数
def load_master_data():
    """master_data.txtから商品名・金額・原価の辞書を返す"""
    ensure_file_exists(MASTER_FILE)
    master = {}
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
    ensure_file_exists(URIAGE_FILE)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    profit = price - cost
    with open(URIAGE_FILE, "a", encoding="utf-8") as f:
        # 「日時, 商品名, 売上金額, 利益」
        f.write(f"{now}, {product_name}, {price}, {profit}\n")

# DataFrameの読み込み用関数
def load_sales_df():
    ensure_file_exists(URIAGE_FILE)
    if os.path.getsize(URIAGE_FILE) == 0:
        # 空ファイルなら空DataFrameで返す
        return pd.DataFrame(columns=["日時", "商品名", "売上金額", "利益"])
    try:
        df = pd.read_csv(
            URIAGE_FILE,
            names=["日時", "商品名", "売上金額", "利益"],
            header=None,
            encoding="utf-8"
        )
        # 安全のため必要な列の型変換
        df["売上金額"] = pd.to_numeric(df["売上金額"], errors="coerce").fillna(0).astype(int)
        df["利益"] = pd.to_numeric(df["利益"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"売上データの読込時にエラーが発生しました: {e}")
        return pd.DataFrame(columns=["日時", "商品名", "売上金額", "利益"])

# サイドバーのメニュー（『商品設定』を追加＋"一括表示"に置換）
st.sidebar.title("ショップ管理メニュー")
menu = st.sidebar.radio(
    "メニューを選択してください",
    ("売上入力", "一括表示", "AI相談", "商品設定")
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

# 2. 一括表示（集計強化）
elif menu == "一括表示":
    st.header("売上一覧・集計＆統計分析 (Pandas利用)")

    df = load_sales_df()
    if df.empty:
        st.warning("まだ売上データがありません。")
    else:
        # 表示用に整形
        styled_df = df.copy()
        # 日時を昇順（古→新）
        styled_df = styled_df.sort_values("日時", ascending=True)

        st.subheader("■ 売上履歴データ (最新順)")
        st.dataframe(styled_df[::-1], hide_index=True, use_container_width=True)

        # 基本統計
        st.markdown("### ▼ 統計情報まとめ")
        total_sales = int(df["売上金額"].sum())
        max_sales = int(df["売上金額"].max())
        avg_sales = float(df["売上金額"].mean()) if not df["売上金額"].empty else 0
        total_profit = int(df["利益"].sum())
        avg_profit = float(df["利益"].mean()) if not df["利益"].empty else 0
        order_count = len(df)
        avg_unit_price = avg_sales  # 1明細＝1客なら平均客単価≒平均売上金額

        stats_cols = st.columns(3)
        stats_cols[0].metric("最高売上額", f"{max_sales:,} 円")
        stats_cols[1].metric("平均客単価", f"{avg_unit_price:,.0f} 円")
        stats_cols[2].metric("総利益", f"{total_profit:,} 円")

        st.write(f"**売上件数:** {order_count:,} 回　　**平均利益:** {avg_profit:,.1f} 円")

        # 詳細商品別集計
        st.markdown("### ▼ 商品ごとの集計（売上・利益・利益率）")
        group = (
            df.groupby("商品名")
            .agg(
                件数=("売上金額", "count"),
                売上合計=("売上金額", "sum"),
                利益合計=("利益", "sum"),
                平均単価=("売上金額", "mean"),
                平均利益=("利益", "mean"),
            )
            .reset_index()
        )
        group["利益率(%)"] = np.where(
            group["売上合計"] > 0,
            (group["利益合計"] / group["売上合計"] * 100).round(1),
            0
        )
        group = group.sort_values("売上合計", ascending=False)
        st.dataframe(group, use_container_width=True)

        # グラフ生成(Pandas+Matplotlibでスマートに)
        import matplotlib.pyplot as plt
        # ★★★ ここでjapanize_matplotlibにより日本語が化けずに描画される ★★★

        st.markdown("### ▼ 商品別売上集計グラフ")
        if st.button("最新のグラフで集計を見る（PNGも更新）"):
            with st.spinner("グラフを作成中..."):
                try:
                    result = subprocess.run(
                        [sys.executable, GRAPH_FILE],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        st.error("グラフ生成（graph.py）でエラーが発生しました。")
                        st.text(result.stderr)
                    else:
                        st.info("最新のグラフを作成しました。")
                except Exception as e:
                    st.error(f"グラフ作成の実行中にエラーが発生しました: {e}")

        # グラフをStreamlitでも即時描画
        fig, ax = plt.subplots(figsize=(6, 4))
        group.plot(
            kind="bar",
            x="商品名",
            y="売上合計",
            legend=False,
            ax=ax,
            color="#79A3F4"
        )
        ax.set_xlabel("商品名", fontsize=12)
        ax.set_ylabel("合計売上(円)", fontsize=12)
        ax.set_title("商品別売上集計", fontsize=14)
        for i, v in enumerate(group["売上合計"]):
            ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=10)
        plt.tight_layout()
        st.pyplot(fig)

        # PNG画像（外部保存）も表示
        if os.path.exists(CHART_FILE):
            st.image(CHART_FILE, caption="保存済みグラフ画像（sales_chart.png）")
        else:
            st.info("（PNG画像：sales_chart.png がまだありません。ボタンから生成してください）")

# 3. AI相談
elif menu == "AI相談":
    st.header("AIコンサルのアドバイス")
    product_info = load_master_data()
    if not product_info:
        st.warning("『商品設定』からまず商品を登録してください。")
    elif st.button("AIに売上を分析してもらう！"):
        with st.spinner("AIが売上データを分析中..."):
            try:
                if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
                    st.error("Google APIキーが設定されていません。")
                else:
                    from google import genai

                    ensure_file_exists(URIAGE_FILE)
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
# 
# ---- graph.py の安全な日本語フォント設定サンプル ------
#
# import matplotlib
# # 日本語表示（Japanize-matplotlibがあれば必ず使う、なければ安全な代替をセット）
# try:
#     import japanize_matplotlib
# except ImportError:
#     # Japanize-matplotlibがなければMS GothicやIPAexGothic等をfallback
#     import matplotlib.font_manager as fm
#     # Linux環境向け: IPAexGothic, Noto Sans CJK, Axis, MS Gothicなど、環境によって選ぶ
#     font_candidates = [
#         "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
#         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
#         "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
#         "/usr/share/fonts/truetype/msttcorefonts/MSGOTHIC.TTC",
#         "MS Gothic", "IPAexGothic", "Noto Sans CJK JP"
#     ]
#     for fc in font_candidates:
#         try:
#             matplotlib.rc("font", family=fm.FontProperties(fname=fc).get_name())
#             break
#         except Exception:
#             continue
# ---- 必ずこのような安全策をグラフ冒頭で実施してください ----
