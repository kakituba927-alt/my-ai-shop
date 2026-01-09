import matplotlib
# 日本語表示（Japanize-matplotlibがあれば必ず使う、なければ安全な代替をセット）
try:
    import japanize_matplotlib
except ImportError:
    import matplotlib.font_manager as fm
    font_candidates = [
        "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/MSGOTHIC.TTC",
        "MS Gothic", "IPAexGothic", "Noto Sans CJK JP"
    ]
    for fc in font_candidates:
        try:
            matplotlib.rc("font", family=fm.FontProperties(fname=fc).get_name())
            break
        except Exception:
            continue

import matplotlib.pyplot as plt

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
    plt.bar(labels, values, color='skyblue')
    plt.xlabel("商品名", fontsize=14)
    plt.ylabel("合計売上(円)", fontsize=14)
    plt.title("商品別売上集計", fontsize=16)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    for i, v in enumerate(values):
        plt.text(i, v, str(v), ha="center", va="bottom", fontsize=12)
    plt.tight_layout()
    plt.savefig("sales_chart.png")
    print("グラフをsales_chart.pngとして保存しました。")
