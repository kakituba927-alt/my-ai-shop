def main():
    import collections

    sales = collections.defaultdict(int)

    with open("uriage.txt", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) != 3:
                continue  # skip lines that don't match the new format
            _, shohin, kingaku = [p.strip() for p in parts]
            try:
                kingaku_int = int(kingaku)
                sales[shohin] += kingaku_int
            except ValueError:
                continue  # skip lines where amount is not numeric

    for i, (shohin, total) in enumerate(sales.items(), 1):
        print(f"{i}. {shohin}の合計は{total}円")

if __name__ == "__main__":
    main()
