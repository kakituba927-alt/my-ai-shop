import datetime

def main():
    # 商品名, 売上金額, 原価
    menu = {
        "1": ("コーヒー", 500, 100),
        "2": ("ケーキ", 800, 300),
        "3": ("紅茶", 600, 150)
    }
    print("メニュー:")
    for num, (name, price, cost) in menu.items():
        print(f"{num}: {name} {price}円 (原価:{cost}円)")

    while True:
        choice = input("番号を選んでください: ").strip()
        if choice in menu:
            break
        print("正しい番号を入れてください")

    shohin, kingaku, genka = menu[choice]
    rieki = kingaku - genka
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("uriage.txt", "a", encoding="utf-8") as f:
        # 日付時刻, 商品名, 売上金額, 利益
        f.write(f"{now}, {shohin}, {kingaku}, {rieki}\n")
    print("記録しました！")

if __name__ == "__main__":
    main()
