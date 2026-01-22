import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys

# --- ipaexg.ttf フォントを明示的に利用（カレントフォルダ想定） ---
font_path = "ipaexg.ttf"
if not os.path.isfile(font_path):
    print("日本語フォント ipaexg.ttf がカレントディレクトリにありません。ファイルを配置してください。")
    sys.exit(1)

# フォントプロパティを生成して全体に反映
jp_font = fm.FontProperties(fname=font_path)
matplotlib.rcParams['font.family'] = jp_font.get_name()
matplotlib.rcParams['font.size'] = 12

# 売上データを読み込む
sales = {}
with open("uriage.txt", "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(",")
        # uriage.txtの新フォーマット: 「日時, 商品名, 売上金額, 利益」
        if len(parts) != 4:
            continue
        _, shohin, kingaku, _ = [p.strip() for p in parts]
        try:
            sales[shohin] = sales.get(shohin, 0) + int(kingaku)
        except ValueError:
            continue

# データがなければ終了
if not sales:
    print("売上データがありません。")
else:
    labels = list(sales.keys())
    values = list(sales.values())

    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, values, color='skyblue')

    # フォントプロパティを個別にも適用
    plt.xlabel("商品名", fontsize=14, fontproperties=jp_font)
    plt.ylabel("合計売上(円)", fontsize=14, fontproperties=jp_font)
    plt.title("商品別売上集計", fontsize=16, fontproperties=jp_font)
    plt.xticks(fontsize=12, fontproperties=jp_font)
    plt.yticks(fontsize=12, fontproperties=jp_font)

    # 数値ラベルにも日本語フォント適用
    for i, v in enumerate(values):
        plt.text(i, v, str(v), ha="center", va="bottom", fontsize=12, fontproperties=jp_font)

    plt.tight_layout()
    plt.savefig("sales_chart.png")
    print("グラフをsales_chart.pngとして保存しました。")
