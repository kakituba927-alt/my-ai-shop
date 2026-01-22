import streamlit as st
import datetime
import os
import subprocess
import sys
import pandas as pd
import numpy as np
import japanize_matplotlib  # ★ 日本語グラフ化け防止のため必ずimport

# --- 必要なライブラリ追加 ---
import io
from typing import Optional

# === PDF出力・フォントDL用 ===
import requests
import tempfile
from fpdf import FPDF

# --- 1. セキュアな方法でAPIキーをセット（Streamlit Cloud用） ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# ====== ファイル名を"MyAI/"無しに統一 ======
URIAGE_FILE = "uriage.txt"
CHART_FILE = "sales_chart.png"
MASTER_FILE = "master_data.txt"
GRAPH_FILE = "graph.py"

def ensure_file_exists(path):
    if path in [CHART_FILE, GRAPH_FILE]:
        return
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass

def load_master_data():
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
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        for name, info in master.items():
            f.write(f"{name}, {info['price']}, {info['cost']}\n")

def append_sales(product_name, price, cost):
    ensure_file_exists(URIAGE_FILE)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    profit = price - cost
    with open(URIAGE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{now}, {product_name}, {price}, {profit}\n")

def load_sales_df():
    ensure_file_exists(URIAGE_FILE)
    if os.path.getsize(URIAGE_FILE) == 0:
        return pd.DataFrame(columns=["日時", "商品名", "売上金額", "利益"])
    try:
        df = pd.read_csv(
            URIAGE_FILE,
            names=["日時", "商品名", "売上金額", "利益"],
            header=None,
            encoding="utf-8"
        )
        df["売上金額"] = pd.to_numeric(df["売上金額"], errors="coerce").fillna(0).astype(int)
        df["利益"] = pd.to_numeric(df["利益"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"売上データの読込時にエラーが発生しました: {e}")
        return pd.DataFrame(columns=["日時", "商品名", "売上金額", "利益"])

# -------- フィルター状態（商品・日付範囲）はサイドバーで管理して全体で共通 --------
df = load_sales_df()
if not df.empty:
    df["日時_dt"] = pd.to_datetime(df["日時"], errors="coerce")
    unique_products = sorted(df["商品名"].dropna().unique())
    min_date = df["日時_dt"].min()
    max_date = df["日時_dt"].max()
    default_start = min_date.date() if pd.notnull(min_date) else datetime.date.today()
    default_end = max_date.date() if pd.notnull(max_date) else datetime.date.today()
else:
    unique_products = []
    default_start = datetime.date.today()
    default_end = datetime.date.today()

st.sidebar.title("ショップ管理メニュー")
menu = st.sidebar.radio(
    "メニューを選択してください",
    ("売上入力", "一括表示", "AI相談", "商品設定", "AI秘書"),
    key="main_menu"
)

with st.sidebar:
    st.markdown("### ▼ 売上一覧・AI分析用フィルター")
    filter_disable = len(unique_products) == 0
    selected_products = st.multiselect(
        "商品名で絞り込み",
        options=unique_products,
        default=unique_products,
        key="global_products",
        disabled=filter_disable
    )
    start_date = st.date_input(
        "開始日",
        value=default_start,
        min_value=default_start,
        max_value=default_end,
        key="global_start_date",
        disabled=filter_disable
    )
    end_date = st.date_input(
        "終了日",
        value=default_end,
        min_value=default_start,
        max_value=default_end,
        key="global_end_date",
        disabled=filter_disable
    )
    # 理解度テスト出題ボタンをAI秘書と共通セッションで利用
    if menu == "AI秘書":
        test_btn = st.button("この資料から3問、理解度テストを作成する", key="make_quiz_sidebar")
    else:
        test_btn = False

def get_filtered_sales(df):
    if df.empty:
        return df
    filtered = df.copy()
    if selected_products:
        filtered = filtered[filtered["商品名"].isin(selected_products)]
    else:
        filtered = filtered.iloc[0:0]
    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        filtered = filtered[
            (filtered["日時_dt"] >= start_dt) &
            (filtered["日時_dt"] <= end_dt)
        ]
    except Exception:
        filtered = filtered.iloc[0:0]
    return filtered

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

elif menu == "一括表示":
    st.header("売上一覧・集計＆統計分析 (Pandas利用)")

    if df.empty:
        st.warning("まだ売上データがありません。")
    else:
        filtered_df = get_filtered_sales(df)
        styled_df = filtered_df.copy()
        styled_df = styled_df.sort_values("日時", ascending=True)

        st.subheader("■ 売上履歴データ (最新順) ※絞り込み反映")
        st.dataframe(styled_df[::-1][["日時", "商品名", "売上金額", "利益"]], hide_index=True, use_container_width=True)

        st.markdown("### ▼ 統計情報まとめ (絞り込み条件反映)")

        total_sales = int(filtered_df["売上金額"].sum()) if not filtered_df.empty else 0
        max_sales = int(filtered_df["売上金額"].max()) if len(filtered_df) > 0 else 0
        avg_sales = float(filtered_df["売上金額"].mean()) if not filtered_df["売上金額"].empty else 0
        total_profit = int(filtered_df["利益"].sum()) if not filtered_df.empty else 0
        avg_profit = float(filtered_df["利益"].mean()) if not filtered_df["利益"].empty else 0
        order_count = len(filtered_df) if not filtered_df.empty else 0
        avg_unit_price = avg_sales

        stats_cols = st.columns(3)
        stats_cols[0].metric("最高売上額", f"{max_sales:,} 円")
        stats_cols[1].metric("平均客単価", f"{avg_unit_price:,.0f} 円")
        stats_cols[2].metric("総利益", f"{total_profit:,} 円")

        st.write(f"**売上件数:** {order_count:,} 回　　**平均利益:** {avg_profit:,.1f} 円")

        st.markdown("### ▼ 商品ごとの集計（売上・利益・利益率）(絞り込み反映)")
        group = (
            filtered_df.groupby("商品名")
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

        import matplotlib.pyplot as plt

        st.markdown("### ▼ 商品別売上集計グラフ (絞り込み反映)")
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

        fig, ax = plt.subplots(figsize=(6, 4))
        if not group.empty and group["売上合計"].sum() > 0:
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
        else:
            st.info("該当データがありませんのでグラフは表示できません。")

        if os.path.exists(CHART_FILE):
            st.image(CHART_FILE, caption="保存済みグラフ画像（sales_chart.png）")
        else:
            st.info("（PNG画像：sales_chart.png がまだありません。ボタンから生成してください）")

elif menu == "AI相談":
    st.header("AIコンサルのアドバイス")
    product_info = load_master_data()
    if df.empty:
        st.info("売上データがありません。")
    else:
        filtered_df = get_filtered_sales(df)
        view_df = filtered_df[["日時", "商品名", "売上金額", "利益"]].copy()
        view_df = view_df.sort_values("日時", ascending=True)
        st.dataframe(view_df[::-1], hide_index=True, use_container_width=True)
        st.markdown("※ 上記リストは、サイドバーで指定された絞り込みデータです。この内容のみをAIで分析します。")

        if not product_info:
            st.warning("『商品設定』からまず商品を登録してください。")
        elif st.button("AIに売上を分析してもらう！"):
            if view_df.empty:
                st.warning("該当の絞り込みデータがありません。")
            else:
                with st.spinner("AIが売上データを分析中..."):
                    try:
                        if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
                            st.error("Google APIキーが設定されていません。")
                        else:
                            from google import genai

                            uriage_content = view_df.to_csv(index=False, header=True, encoding="utf-8")

                            prompt = (
                                "現在、ユーザーは特定の条件でデータを絞り込んでいます。このデータセットのみに基づいて分析してください。\n"
                                "あなたは10年の経験を持つ敏腕経営コンサルタントです。\n"
                                "以下の売上履歴は、スタッフまたは店長の希望する特定の条件でフィルターされた限定的な範囲の売上データです。\n"
                                "この範囲だけに集中して、質問の分析や提案・戦略を作成してください。\n"
                                "また、このデータは「日時, 商品名, 売上金額, 利益」というカラム名で、CSV形式で渡されます。\n"
                                "以下のグラフ（sales_chart.png）もある体裁ですが、数値や予測の根拠は必ず今渡したフィルタ済みデータのみから推論してください。\n"
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
                                "- 分析や提案ではsales_chart.png（商品別売上棒グラフ）も参照した体裁ですが、数値や予測の根拠は必ずこの絞り込んだ売上データのみを使ってください。\n"
                                "- 提案は現実的かつ短期的にも実行しやすいものを必ず含めてください。\n"
                                "\n"
                                "【売上履歴（フィルタ済みCSV）】\n"
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

    master = load_master_data()
    if master:
        st.markdown("### ▼ 登録済み商品")
        for pname, info in master.items():
            st.write(f"- {pname}: 販売価格 {info['price']}円 / 原価 {info['cost']}円")
    else:
        st.info("まだ商品が登録されていません。")

# ---------- AI秘書（PDF要約・対話・理解度テスト） ----------
elif menu == "AI秘書":
    st.header("AI秘書（PDF対話・要約＆学習モード）")
    st.markdown(
        "### PDF資料をアップロードしてください。AI秘書が要約し、内容について質問・会話・テストができます！<br>"
        "3点要約：①結論 ②重要なポイント3つ ③次に取るべき行動<br>"
        "・要約下のチャット欄で内容について質問できます<br>"
        "・「理解度テスト作成」ボタンでAIが確認テストも出題します",
        unsafe_allow_html=True
    )

    # --- 初期セッション確保 ---
    if "pdf_text" not in st.session_state:
        st.session_state["pdf_text"] = None
    if "pdf_chat_history" not in st.session_state:
        st.session_state["pdf_chat_history"] = []
    if "pdf_last_filehash" not in st.session_state:
        st.session_state["pdf_last_filehash"] = None
    if "pdf_summary" not in st.session_state:
        st.session_state["pdf_summary"] = None
    if "pdf_quiz" not in st.session_state:
        st.session_state["pdf_quiz"] = None

    # --- 資料アップロード ---
    pdf_file = st.file_uploader("PDFファイルをアップロードしてください", type=["pdf"], key="pdf_upload")

    # --- PDFファイル内容抽出: テキスト化してst.session_state["pdf_text"]へ ---
    def file_hash(f):
        if f is None: return None
        f.seek(0)
        return hash(f.read())  # reset to beginning, should hash all content
    file_changed = False

    if pdf_file is not None:
        # ファイルの内容が変わった場合、セッション内容(テキスト・履歴・要約・テスト)もリセット
        cur_hash = file_hash(pdf_file)
        if st.session_state["pdf_last_filehash"] != cur_hash:
            st.session_state["pdf_last_filehash"] = cur_hash
            st.session_state["pdf_text"] = None
            st.session_state["pdf_summary"] = None
            st.session_state["pdf_chat_history"] = []
            st.session_state["pdf_quiz"] = None
            file_changed = True
        # 既にテキスト解析済みか確認
        if st.session_state["pdf_text"] is None:
            try:
                import pdfplumber
                pdf_file.seek(0)
                with pdfplumber.open(pdf_file) as pdf:
                    pdf_texts = [page.extract_text() for page in pdf.pages]
                pdf_texts = [t for t in pdf_texts if t and t.strip()]
                pdf_full_text = "\n".join(pdf_texts) if pdf_texts else ""
            except Exception as e:
                st.error(f"PDFの読み取り中にエラーが発生しました(pdfplumber): {e}")
                pdf_full_text = ""
            st.session_state["pdf_text"] = pdf_full_text
        else:
            pdf_full_text = st.session_state["pdf_text"]

        # --- テキストが取れたら要約/会話/テスト ---
        if pdf_full_text and pdf_full_text.strip():

            st.markdown("#### --- 抽出内容（AIハイライト用） ---")
            with st.expander("PDF全文の内容を一時確認したい場合はこちら", expanded=False):
                st.text_area("PDFの全文（AIに渡す内容）", pdf_full_text, height=200)

            # --------- AIで要約（session_stateにキャッシュ） ---------
            make_summary = False
            if st.session_state["pdf_summary"] is None:
                if st.button("AI秘書に資料要約してもらう！"):
                    make_summary = True
            else:
                # 表示再現
                st.markdown("#### --- AI秘書による要約 ---")
                st.markdown(st.session_state["pdf_summary"])

            # 実行
            if make_summary:
                with st.spinner("AIがPDF資料の内容を要約中...(Gemini)"):
                    try:
                        if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
                            st.error("Google APIキーが設定されていません。")
                        else:
                            from google import genai

                            prompt = (
                                "あなたは資料を素早く要約することに長けたプロの日本人秘書です。\n"
                                "以下のPDF資料テキスト内容を読んで、次の3点でコンパクトに分かりやすくまとめてください：\n"
                                "①結論\n"
                                "②重要なポイント3つ\n"
                                "③次に取るべき行動\n"
                                "\n"
                                "【PDF資料内容】\n"
                                f"{pdf_full_text}\n"
                            )

                            client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=prompt
                            )
                            summary = response.text
                            st.session_state["pdf_summary"] = summary
                            st.markdown("#### --- AI秘書による要約 ---")
                            st.markdown(summary)
                    except Exception as e:
                        st.error(f"AI要約中にエラーが発生しました: {e}")

            # ----------------- チャット機能エリア -----------------
            st.markdown("---")
            st.markdown("#### 💬 この資料の内容をAI秘書へ質問 (対話学習モード)")
            placeholder = st.empty()

            # チャット履歴描画
            chat_history = st.session_state["pdf_chat_history"]

            # ---- ここで履歴のロール名を「user」「model」のみで統一する処理。 ----
            # 既存履歴中で 'assistant'→'model', 'system'→'model' など全変換
            valid_roles = {"user", "model"}
            for msg in chat_history:
                # 役割の変換
                if msg.get("role") not in valid_roles:
                    if msg.get("role") == "assistant":
                        msg["role"] = "model"
                    elif msg.get("role") == "system":
                        msg["role"] = "model"
                    else:
                        # 万が一他のロール名も"model"で統一
                        msg["role"] = "model"

            # チャット履歴描画
            for m in chat_history:
                # Streamlit描画側のみ識別語「user」(人間)・「model」(AI)で分岐
                if m["role"] == "user":
                    with st.chat_message("user"):
                        st.write(m["content"])
                elif m["role"] == "model":
                    with st.chat_message("assistant"):
                        st.write(m["content"])

            # チャット入力
            user_msg = st.chat_input("この資料について質問してください", key="pdf_chat_input")
            if user_msg and user_msg.strip():
                # 履歴に追加
                chat_history.append({"role": "user", "content": user_msg.strip()})
                # Geminiへ問い合わせ
                with st.spinner("AI秘書が資料を読み取って調べています..."):
                    try:
                        from google import genai

                        # 直近長めに履歴をまとめて文脈として投げる
                        hist_to_send = [
                            {"role": h["role"], "parts": [{"text": h["content"]}]}
                            for h in chat_history[-6:]  # 直近だけに制限
                        ]
                        # 資料内容も必ず含める
                        system_message = (
                            "あなたは資料に詳しい日本人秘書です。\n"
                            "必ず、下記PDF資料の内容に基づいた事実のみ正確に答えてください。\n"
                            "質問に自信がない場合や資料に明記がない場合は「申し訳ありませんが、その内容は資料には記載されていません」とだけ返してください。\n"
                            "\n"
                            "【PDF資料内容】\n"
                            f"{pdf_full_text}"
                        )

                        client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                        # GeminiのAPIでは "system" ロールは使えません
                        # そのため、ヒストリ直列(直近N件/user,modelのみ) + system_messageは最新userメッセージに含める
                        # もしくは、最初の質問のプレフィックスとして渡す
                        # ここでは直近6件+最新user発話の内容にsystem_messageをヘッダ的に付加
                        hist_for_api = []
                        for h in chat_history[-5:]:  # 直近5件
                            hist_for_api.append({"role": h["role"], "parts": [{"text": h["content"]}]})

                        # latest user msg: system_message + ユーザー入力 を結合
                        hist_for_api.append({
                            "role": "user",
                            "parts": [{"text": system_message + "\n\n【質問】\n" + user_msg.strip()}]
                        })

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=hist_for_api
                        )
                        output = response.text
                        chat_history.append({"role": "model", "content": output})
                        # 描画を更新
                        placeholder.empty()
                        # 再度履歴ロール整備＆表示
                        for msg in chat_history:
                            if msg.get("role") not in valid_roles:
                                msg["role"] = "model"
                        for m in chat_history:
                            if m["role"] == "user":
                                with st.chat_message("user"):
                                    st.write(m["content"])
                            elif m["role"] == "model":
                                with st.chat_message("assistant"):
                                    st.write(m["content"])
                    except Exception as e:
                        st.error(f"AI秘書とのチャット中にエラーが発生しました: {e}")

            # --------- 理解度テスト自動出題・解答エリア ---------
            st.markdown("---")
            make_quiz = st.button("この資料から3問、理解度テストを作成する", key="make_quiz_btn_main")
            quiz_to_show = None

            # サイドバー経由で出題ボタン押された場合 or 画面リロードでも維持
            if st.session_state.get("pdf_quiz") is not None:
                quiz_to_show = st.session_state["pdf_quiz"]

            # サイドバーもしくはメイン画面のボタンで
            if make_quiz or test_btn:
                with st.spinner("AI秘書が資料内容から3問テストを作っています..."):
                    try:
                        from google import genai

                        prompt = (
                            "以下のPDF資料の全文に基づいて、読者の理解度を確認できる3問のクイズ（問い）を日本語で作成してください。\n"
                            "各問について「問題」「正答」「詳しい解説」を必ずセットでマークダウン形式で示してください。\n"
                            "例:\n"
                            "【第1問】・・・\n"
                            "**答え:**\n"
                            "**解説:**\n"
                            "\n"
                            "資料の範囲からのみ出し、難易度は初級〜中級程度としてください。\n"
                            "【PDF資料内容】\n"
                            f"{pdf_full_text}\n"
                        )

                        client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt
                        )
                        quiz_text = response.text
                        st.session_state["pdf_quiz"] = quiz_text
                        quiz_to_show = quiz_text
                    except Exception as e:
                        st.error(f"AIによる理解度テスト出題中にエラーが発生しました: {e}")

            if quiz_to_show:
                st.markdown("#### --- AI秘書による理解度テスト ---")
                st.markdown(quiz_to_show)

            # ===== ▼▼▼ ダウンロードボタン追加（TXT＋PDF両方） ▼▼▼ ===========

            # 1. 要約、テスト問題、チャット履歴を1つのテキストにまとめる
            section_texts = []
            # PDF要約
            if st.session_state.get("pdf_summary"):
                section_texts.append("【AI秘書要約】\n" + st.session_state["pdf_summary"])
            # 理解度テスト
            if st.session_state.get("pdf_quiz"):
                section_texts.append("【AI理解度テスト】\n" + st.session_state["pdf_quiz"])
            # チャット履歴
            chat = st.session_state.get("pdf_chat_history", [])
            if chat:
                chat_lines = []
                chat_lines.append("【AI秘書とのQ&Aチャット履歴】")
                for i, msg in enumerate(chat):
                    if msg.get("role") == "user":
                        chat_lines.append(f"\nQ{i//2+1}: {msg.get('content')}")
                    elif msg.get("role") == "model":
                        chat_lines.append(f"AI: {msg.get('content')}")
                section_texts.append("\n".join(chat_lines))
            # ひとまとめ
            full_report = "\n\n".join(section_texts)

            # [1] TXTダウンロードボタン・[2] PDFダウンロードボタンを横並びまたは近くで表示
            if full_report.strip():
                dl_cols = st.columns(2)
                with dl_cols[0]:
                    st.download_button(
                        label="レポートをテキストで保存",
                        data=full_report,
                        file_name="AI秘書レポート.txt",
                        mime="text/plain"
                    )
                with dl_cols[1]:
                    # PDF作成用関数
                    def generate_pdf_report(full_report, font_url="https://github.com/googlefonts/ipaexfont/raw/main/fonts/ipaexg.ttf"):
                        """
                        PDF出力でUnicode日本語フォントが確実に使えるように、IPAexGothicを都度DL。  
                        FPDFUnicodeEncodingExceptionにも対応した堅牢なPDFエクスポート関数。
                        失敗時もアプリ停止しないよう例外ハンドリングを強く。
                        """
                        font_path = None
                        pdf_bytes = None
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".ttf") as tf:
                                font_path = tf.name
                                # フォントをインターネットから確実にダウンロード
                                r = requests.get(font_url)
                                r.raise_for_status()
                                tf.write(r.content)
                            pdf = FPDF(orientation='P', unit='mm', format='A4')
                            pdf.add_page()
                            # 日本語フォントをUnicodeモードで追加
                            try:
                                pdf.add_font('IPAexGothic', '', font_path, uni=True)
                                font_name = 'IPAexGothic'
                                pdf.set_font(font_name, size=13)
                            except Exception as e_font:
                                font_name = ''
                                pdf.set_font("Arial", size=12)
                            # セクション毎に改行を適切に
                            for section in section_texts:
                                for line in section.splitlines():
                                    if pdf.get_y() > 260:
                                        pdf.add_page()
                                        if font_name:
                                            pdf.set_font(font_name, size=13)
                                        else:
                                            pdf.set_font("Arial", size=12)
                                    try:
                                        pdf.multi_cell(0, 8, line)
                                    except Exception as ee:
                                        # 万一日本語で失敗時は無視し空行で置換
                                        pdf.multi_cell(0, 8, "（表示失敗）")
                                pdf.ln(4)
                            try:
                                pdf_bytes = pdf.output(dest='S').encode('latin1')
                            except Exception as e_bytes:
                                pdf_bytes = None
                                st.error("PDF保存時にエラーが発生しました（日本語が含まれる場合は文字化け・保存失敗の可能性があります）: {}".format(e_bytes))
                        except Exception as e:
                            pdf_bytes = None
                            st.error("PDF作成に失敗しました: {}".format(e))
                        finally:
                            # クリーンナップ
                            if font_path and os.path.exists(font_path):
                                try:
                                    os.remove(font_path)
                                except Exception:
                                    pass
                        return pdf_bytes

                    # PDF作成を安全に呼ぶ・例外でアプリ落ちを防ぐ
                    pdf_bytes = None
                    try:
                        pdf_bytes = generate_pdf_report(full_report)
                    except Exception as e:
                        st.error("PDF生成中に致命的なエラーが発生しました: {}".format(e))
                    if pdf_bytes:
                        st.download_button(
                            label="レポートをPDFで保存",
                            data=pdf_bytes,
                            file_name="AI秘書レポート.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("PDF出力に失敗しました。英語名やテキスト保存は可能です。")

            # ===== ▲▲▲ ダウンロードボタン追加ここまで（TXT+PDF） ▲▲▲ ==========

        else:
            st.info("※ PDF内にテキストが含まれていないか抽出できませんでした。")
            st.info("画像として解析を試みます（β）")

            if st.button("画像PDFをGeminiにそのまま解析依頼（実験的機能）"):
                with st.spinner("Geminiが画像形式PDFの解析を試みています..."):
                    try:
                        if not GOOGLE_API_KEY or GOOGLE_API_KEY.strip() == "":
                            st.error("Google APIキーが設定されていません。")
                        else:
                            from google import genai
                            prompt = (
                                "あなたは画像PDFやスキャン資料から重要な内容を要約することができるプロの日本人秘書です。\n"
                                "アップロードされたPDFファイルは画像形式または通常のPDFです。\n"
                                "内容を読み取り、わかりやすく①結論②重要なポイント3つ③次に取るべき行動でまとめてください。\n"
                            )
                            pdf_file.seek(0)
                            pdf_bytes = pdf_file.read()
                            client = genai.Client(api_key=GOOGLE_API_KEY.strip())
                            try:
                                response = client.models.generate_content(
                                    model="gemini-2.5-flash",
                                    contents=[prompt],
                                    files=[{
                                        "file_name": pdf_file.name,
                                        "data": pdf_bytes
                                    }]
                                )
                                st.markdown("#### --- AI秘書による（画像PDFも考慮した）要約 ---")
                                st.markdown(response.text)
                            except Exception as e2:
                                st.warning("Geminiへの画像直接渡しにはAPI対応が必要です。")
                                st.error(f"ファイル送信時エラー: {e2}")

                    except Exception as e:
                        st.error(f"画像型PDFのAI解析時にエラーが発生しました: {e}")

    else:
        st.info("PDFを選択・アップロードしてください。")

# --- requirements.txtの内容（このファイルをプロジェクト直下に新規で作成してください） ---
# requirements.txt ------------------
# streamlit
# google-generativeai
# matplotlib
# japanize-matplotlib
# pandas
# numpy
# pdfplumber
# fpdf2
# requests
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
