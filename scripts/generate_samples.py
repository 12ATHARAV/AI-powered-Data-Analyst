from pathlib import Path

import numpy as np
import pandas as pd


def generate_samples(output_dir: str | Path = "data/samples") -> dict[str, int]:
    """Generate deterministic sample CSV datasets for the AI Data Analyst.

    Datasets:
      - customers.csv (200 rows)
      - products.csv (30 rows)
      - sales.csv (~5,000+ rows with seeded anomalies and quality issues)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)

    # 1. customers.csv (200 rows)
    num_customers = 200
    customer_ids = np.arange(1, num_customers + 1)
    customer_names = [f"Customer {cid:03d}" for cid in customer_ids]
    segments = rng.choice(["Consumer", "Corporate", "Small Business"], size=num_customers, p=[0.5, 0.3, 0.2])
    countries = rng.choice(["UK", "Germany", "France", "India", "USA"], size=num_customers, p=[0.25, 0.2, 0.15, 0.15, 0.25])

    # signup_date between 2021-01-01 and 2023-12-31
    start_date = pd.Timestamp("2021-01-01")
    end_date = pd.Timestamp("2023-12-31")
    days_range = (end_date - start_date).days
    random_days = rng.integers(0, days_range + 1, size=num_customers)
    signup_dates = [start_date + pd.Timedelta(days=int(d)) for d in random_days]

    customers_df = pd.DataFrame({
        "customer_id": customer_ids,
        "name": customer_names,
        "segment": segments,
        "country": countries,
        "signup_date": [d.strftime("%Y-%m-%d") for d in signup_dates],
    })
    customers_file = output_path / "customers.csv"
    customers_df.to_csv(customers_file, index=False)

    # 2. products.csv (30 rows)
    num_products = 30
    product_ids = np.arange(1, num_products + 1)
    product_names = [f"Product {pid:02d}" for pid in product_ids]
    categories = ["Electronics", "Furniture", "Office", "Clothing"]
    product_categories = rng.choice(categories, size=num_products, p=[0.3, 0.25, 0.25, 0.2])
    costs = np.round(rng.uniform(5.0, 200.0, size=num_products), 2)

    prod_start = pd.Timestamp("2020-01-01")
    prod_end = pd.Timestamp("2022-12-31")
    prod_days_range = (prod_end - prod_start).days
    prod_random_days = rng.integers(0, prod_days_range + 1, size=num_products)
    launch_dates = [prod_start + pd.Timedelta(days=int(d)) for d in prod_random_days]

    products_df = pd.DataFrame({
        "product_id": product_ids,
        "name": product_names,
        "category": product_categories,
        "cost": costs,
        "launch_date": [d.strftime("%Y-%m-%d") for d in launch_dates],
    })
    products_file = output_path / "products.csv"
    products_df.to_csv(products_file, index=False)

    # Map product cost for pricing
    cost_lookup = dict(zip(product_ids, costs))

    # 3. sales.csv (~5,000 base orders)
    # Order probabilities for products: Products 27-30 get 0.5% total (~0.125% each)
    p_weights = np.ones(num_products)
    p_weights[26:] = 0.005 / 4  # 0.00125 each
    p_weights[:26] = 0.995 / 26
    p_weights /= p_weights.sum()

    base_orders_count = 5000
    all_dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    total_days = len(all_dates)

    # Weight per date based on seasonality & trend
    date_weights = []
    for d in all_dates:
        # Yearly seasonality: Nov/Dec 1.5, Jan/Feb 0.8, others 1.0
        m = d.month
        if m in (11, 12):
            season = 1.5
        elif m in (1, 2):
            season = 0.8
        else:
            season = 1.0

        # Upward trend 1.2x over 2 years (day 0 -> 1.0, day total_days-1 -> 1.2)
        day_idx = (d - all_dates[0]).days
        trend = 1.0 + 0.2 * (day_idx / (total_days - 1))
        date_weights.append(season * trend)

    date_weights = np.array(date_weights)
    date_weights /= date_weights.sum()

    chosen_date_indices = rng.choice(len(all_dates), size=base_orders_count, p=date_weights)
    order_dates = [all_dates[i] for i in chosen_date_indices]

    # Seed extra 60 orders specifically on 2024-03-15 (Issue 6)
    spike_date = pd.Timestamp("2024-03-15")
    extra_spike_dates = [spike_date] * 60
    order_dates.extend(extra_spike_dates)

    total_orders = len(order_dates)
    order_ids = np.arange(100001, 100001 + total_orders)

    # Region distribution: North (20%), South (20%), East (~35%), West (25%)
    regions = rng.choice(["North", "South", "East", "West"], size=total_orders, p=[0.20, 0.20, 0.35, 0.25])
    cust_ids = rng.choice(customer_ids, size=total_orders)
    prod_ids = rng.choice(product_ids, size=total_orders, p=p_weights)
    quantities = rng.integers(1, 11, size=total_orders)  # 1 to 10
    discounts = rng.choice([0.0, 0.05, 0.1, 0.2], size=total_orders, p=[0.5, 0.2, 0.2, 0.1])

    # Unit prices: product cost * uniform(1.4, 2.2)
    multipliers = rng.uniform(1.4, 2.2, size=total_orders)
    unit_prices = np.array([round(cost_lookup[pid] * mult, 2) for pid, mult in zip(prod_ids, multipliers)])

    sales_df = pd.DataFrame({
        "order_id": order_ids,
        "order_date": [d.strftime("%Y-%m-%d") for d in order_dates],
        "customer_id": cust_ids,
        "product_id": prod_ids,
        "region": regions,
        "quantity": quantities,
        "unit_price": unit_prices,
        "discount": discounts,
    })

    # Initial revenue calculation
    sales_df["revenue"] = np.round(sales_df["quantity"] * sales_df["unit_price"] * (1.0 - sales_df["discount"]), 2)

    # Seeded issues:
    # 1. order_id 100500: revenue * 25 (spike)
    mask_100500 = sales_df["order_id"] == 100500
    if mask_100500.any():
        sales_df.loc[mask_100500, "revenue"] = np.round(sales_df.loc[mask_100500, "revenue"] * 25.0, 2)

    # 2. order_id 100777: quantity = -3 with negative revenue
    mask_100777 = sales_df["order_id"] == 100777
    if mask_100777.any():
        sales_df.loc[mask_100777, "quantity"] = -3
        sales_df.loc[mask_100777, "revenue"] = np.round(-3 * sales_df.loc[mask_100777, "unit_price"] * (1.0 - sales_df.loc[mask_100777, "discount"]), 2)

    # 4. 20 rows with empty region
    empty_region_indices = rng.choice(sales_df.index[~sales_df["order_id"].isin([100500, 100777, 101200])], size=20, replace=False)
    sales_df.loc[empty_region_indices, "region"] = ""

    # 5. order_id 101200: unit_price * 40 and revenue recomputed
    mask_101200 = sales_df["order_id"] == 101200
    if mask_101200.any():
        sales_df.loc[mask_101200, "unit_price"] = np.round(sales_df.loc[mask_101200, "unit_price"] * 40.0, 2)
        sales_df.loc[mask_101200, "revenue"] = np.round(sales_df.loc[mask_101200, "quantity"] * sales_df.loc[mask_101200, "unit_price"] * (1.0 - sales_df.loc[mask_101200, "discount"]), 2)

    # 7. 15 rows where region is " east" or "EAST"
    eligible_east = sales_df.index[(sales_df["region"] == "East") & (~sales_df["order_id"].isin([100500, 100777, 101200]))]
    chosen_east_indices = rng.choice(eligible_east, size=15, replace=False)
    sales_df.loc[chosen_east_indices[:8], "region"] = " east"
    sales_df.loc[chosen_east_indices[8:], "region"] = "EAST"

    # 3. 5 exact duplicate rows: copies of order_id 100010 to 100014
    duplicates = sales_df[sales_df["order_id"].isin([100010, 100011, 100012, 100013, 100014])].copy()
    sales_df = pd.concat([sales_df, duplicates], ignore_index=True)

    sales_file = output_path / "sales.csv"
    sales_df.to_csv(sales_file, index=False)

    counts = {
        "customers": len(customers_df),
        "products": len(products_df),
        "sales": len(sales_df),
    }

    print("=== Sample Data Generation Summary ===")
    print(f"customers.csv: {counts['customers']} rows")
    print(f"products.csv:  {counts['products']} rows")
    print(f"sales.csv:     {counts['sales']} rows")
    print("\nSeeded Issues in sales.csv:")
    print("1. Order 100500: revenue spiked 25x")
    print(f"   Value: {sales_df.loc[sales_df['order_id'] == 100500, 'revenue'].values[0]}")
    print("2. Order 100777: negative quantity (-3) and negative revenue")
    print(f"   Qty: {sales_df.loc[sales_df['order_id'] == 100777, 'quantity'].values[0]}, Rev: {sales_df.loc[sales_df['order_id'] == 100777, 'revenue'].values[0]}")
    print("3. 5 exact duplicate rows: copies of order_id 100010..100014")
    print(f"   Duplicates count: {sales_df.duplicated().sum()}")
    print("4. 20 rows with empty region")
    print(f"   Empty region count: {(sales_df['region'] == '').sum()}")
    print("5. Order 101200: unit_price 40x and revenue recomputed")
    print(f"   Unit Price: {sales_df.loc[sales_df['order_id'] == 101200, 'unit_price'].values[0]}")
    print("6. 2024-03-15 volume spike: 60 extra orders added")
    print(f"   Orders on 2024-03-15: {(sales_df['order_date'] == '2024-03-15').sum()}")
    print("7. 15 rows with inconsistent region labels (' east' or 'EAST')")
    print(f"   ' east': {(sales_df['region'] == ' east').sum()}, 'EAST': {(sales_df['region'] == 'EAST').sum()}")

    return counts


if __name__ == "__main__":
    generate_samples()
