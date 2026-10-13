"""Load Olist CSVs into SQLite and build the review-level base table."""
import sqlite3, pathlib
import pandas as pd

RAW = pathlib.Path("data/raw")
TABLES = {"customers": "olist_customers_dataset.csv", "orders": "olist_orders_dataset.csv",
          "order_items": "olist_order_items_dataset.csv", "order_reviews": "olist_order_reviews_dataset.csv",
          "products": "olist_products_dataset.csv", "category_translation": "product_category_name_translation.csv"}

def main():
    con = sqlite3.connect("data/olist.db")
    for t, f in TABLES.items():
        pd.read_csv(RAW / f).to_sql(t, con, if_exists="replace", index=False)
    df = pd.read_sql(open("sql/01_review_base.sql").read(), con)
    df.to_csv("data/review_base.csv", index=False)
    print(f"review_base: {len(df):,} orders with a review; {df.comment.notna().sum():,} with a comment")

if __name__ == "__main__":
    main()
