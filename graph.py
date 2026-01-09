import matplotlib.pyplot as plt

# 売上データを読み込む
sales = {}
with open("uriage.txt", "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(",")
        if len(parts) != 3:
            continue
        _, shohin, kingaku = [p.strip() for p in parts]
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
    plt.xlabel("商品名", fontname="MS Gothic", fontsize=14)
    plt.ylabel("合計売上(円)", fontname="MS Gothic", fontsize=14)
    plt.title("商品別売上集計", fontname="MS Gothic", fontsize=16)
    plt.xticks(fontname="MS Gothic", fontsize=12)
    plt.yticks(fontsize=12)
    for i, v in enumerate(values):
        plt.text(i, v, str(v), ha="center", va="bottom", fontname="MS Gothic", fontsize=12)
    plt.tight_layout()
    plt.savefig("sales_chart.png")
    print("グラフをsales_chart.pngとして保存しました。")
