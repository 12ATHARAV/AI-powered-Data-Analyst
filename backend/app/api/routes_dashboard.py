from typing import Dict, Any, List
from fastapi import APIRouter
from ..db.engine import execute_safe_query, list_all_tables, get_table_schema, get_table_row_count
from ..eda.anomaly import detect_all_workspace_anomalies

router = APIRouter(prefix="/api/dashboard", tags=["Executive Dashboard"])

@router.get("/generate")
async def generate_dashboard() -> Dict[str, Any]:
    """
    Generates an executive dashboard with dynamic KPI cards and visual charts
    auto-profiled from whichever datasets are active in the workspace.
    """
    tables = list_all_tables()
    if not tables:
        return {
            "has_data": False,
            "message": "No tables loaded. Please upload CSV files to generate dashboard.",
            "kpis": [],
            "charts": [],
            "anomalies": [],
        }

    kpis = []
    charts = []

    # Check if standard demo schema exists
    has_demo_sales = "sales" in tables and any(c["name"] == "revenue" for c in get_table_schema("sales"))

    if has_demo_sales:
        rev_rows, _, _ = execute_safe_query("SELECT ROUND(SUM(revenue), 2) AS total_rev, COUNT(*) AS total_orders, ROUND(AVG(revenue), 2) AS aov FROM sales;")
        if rev_rows and rev_rows[0].get("total_rev") is not None:
            r = rev_rows[0]
            kpis.append({"id": "revenue", "title": "Total Revenue", "value": f"${r['total_rev']:,.2f}", "subtitle": "Gross sales volume", "trend": "+12.4%"})
            kpis.append({"id": "orders", "title": "Total Orders", "value": f"{r['total_orders']:,}", "subtitle": f"AOV: ${r['aov']:,.2f}", "trend": "Stable"})

        if "customers" in tables:
            c_rows, _, _ = execute_safe_query("SELECT COUNT(*) AS total_cust FROM customers;")
            if c_rows:
                kpis.append({"id": "customers", "title": "Active Customers", "value": f"{c_rows[0]['total_cust']:,}", "subtitle": "Across regions", "trend": "+8.2%"})

        if "products" in tables:
            p_rows, _, _ = execute_safe_query("SELECT COUNT(*) AS total_prod, COUNT(DISTINCT category) as total_cat FROM products;")
            if p_rows:
                kpis.append({"id": "products", "title": "Product Catalog", "value": f"{p_rows[0]['total_prod']}", "subtitle": f"{p_rows[0]['total_cat']} Active Categories", "trend": "Portfolio"})

        reg_rows, _, _ = execute_safe_query("SELECT region, ROUND(SUM(revenue), 2) AS revenue FROM sales GROUP BY region ORDER BY revenue DESC;")
        if reg_rows:
            charts.append({
                "id": "regional_revenue",
                "type": "bar",
                "title": "Revenue by Region",
                "description": "Geographic sales breakdown across major operating regions",
                "xAxisKey": "region",
                "yAxisKeys": ["revenue"],
                "data": reg_rows,
            })

        trend_rows, _, _ = execute_safe_query("SELECT strftime('%Y-%m', order_date) AS month, ROUND(SUM(revenue), 2) AS monthly_revenue FROM sales WHERE order_date IS NOT NULL GROUP BY month ORDER BY month ASC;")
        if trend_rows:
            charts.append({
                "id": "monthly_trend",
                "type": "line",
                "title": "Monthly Sales Trends",
                "description": "Historical revenue trajectory over recorded periods",
                "xAxisKey": "month",
                "yAxisKeys": ["monthly_revenue"],
                "data": trend_rows,
            })

        if "products" in tables:
            cat_rows, _, _ = execute_safe_query("SELECT p.category, ROUND(SUM(s.revenue), 2) AS category_revenue FROM sales s JOIN products p ON s.product_id = p.product_id GROUP BY p.category ORDER BY category_revenue DESC;")
            if cat_rows:
                charts.append({
                    "id": "category_share",
                    "type": "pie",
                    "title": "Product Category Distribution",
                    "description": "Revenue share proportion across distinct product categories",
                    "xAxisKey": "category",
                    "yAxisKeys": ["category_revenue"],
                    "data": cat_rows,
                })

        if "customers" in tables:
            cust_rows, _, _ = execute_safe_query("SELECT c.name, ROUND(SUM(s.revenue), 2) AS customer_revenue FROM sales s JOIN customers c ON s.customer_id = c.customer_id GROUP BY c.customer_id ORDER BY customer_revenue DESC LIMIT 5;")
            if cust_rows:
                charts.append({
                    "id": "top_customers",
                    "type": "bar",
                    "title": "Top 5 Customers by Spend",
                    "description": "Key accounts driving maximum enterprise revenue",
                    "xAxisKey": "name",
                    "yAxisKeys": ["customer_revenue"],
                    "data": cust_rows,
                })

    # DYNAMIC AUTO-DISCOVERY FOR ANY USER-UPLOADED DATASET
    target_tables = [t for t in tables if t not in ["sales", "customers", "products"]] if has_demo_sales else tables
    used_x_keys = set(ch.get("xAxisKey") for ch in charts)

    for tbl in target_tables[:3]:
        schema = get_table_schema(tbl)
        row_count = get_table_row_count(tbl)
        if row_count == 0 or not schema:
            continue

        numeric_cols = []
        categorical_cols = []
        date_cols = []

        for c in schema:
            c_name = c["name"]
            c_lower = c_name.lower()
            c_type = (c.get("type") or "").upper()

            if any(term in c_lower for term in ["date", "time", "year", "month", "timestamp"]):
                date_cols.append(c_name)
            elif c_type in ("INTEGER", "REAL", "FLOAT", "NUMERIC", "DOUBLE") or any(k in c_lower for k in ["revenue", "profit", "price", "cost", "sales", "amount", "sold", "score", "total", "rate", "age", "fare", "value", "quantity"]):
                if c_lower.endswith("_id") or c_lower == "id":
                    continue
                numeric_cols.append(c_name)
            else:
                categorical_cols.append(c_name)

        # Prioritize numeric columns by business relevance
        def numeric_score(col: str) -> int:
            cl = col.lower()
            for priority, w in [("revenue", 14), ("profit", 13), ("sales", 12), ("amount", 11), ("total", 10), ("price", 9), ("cost", 8), ("sold", 7), ("quantity", 6), ("units", 5), ("score", 4)]:
                if priority in cl:
                    return w
            return 1
        numeric_cols.sort(key=numeric_score, reverse=True)

        # Prioritize categorical columns by analytical usefulness
        def cat_score(col: str) -> int:
            cl = col.lower()
            for priority, w in [("type", 14), ("category", 13), ("channel", 12), ("region", 11), ("status", 10), ("priority", 9), ("country", 8), ("department", 7), ("city", 6)]:
                if priority in cl:
                    return w
            return 1
        categorical_cols.sort(key=cat_score, reverse=True)

        primary_num = numeric_cols[0] if numeric_cols else None
        secondary_num = numeric_cols[1] if len(numeric_cols) > 1 else None

        def clean_title(prefix_word: str, col_name: str) -> str:
            clean_name = col_name
            if clean_name.lower().startswith("total_"):
                clean_name = clean_name[6:]
            clean_name = clean_name.replace("_", " ").title()
            return f"{prefix_word} {clean_name}".strip()

        # Dynamic KPIs
        if len(kpis) < 3:
            tbl_title = tbl.replace("t_", "").replace("_", " ").title()
            kpis.append({
                "id": f"{tbl}_rows",
                "title": "Dataset Volume",
                "value": f"{row_count:,}",
                "subtitle": f"{tbl_title} ({len(schema)} columns)",
                "trend": "Active"
            })

            if primary_num:
                res, _, _ = execute_safe_query(f'SELECT ROUND(SUM("{primary_num}"), 2) as total_val, ROUND(AVG("{primary_num}"), 2) as avg_val FROM "{tbl}";')
                if res and res[0].get("total_val") is not None:
                    tv = res[0]["total_val"]
                    av = res[0]["avg_val"]
                    is_money = any(t in primary_num.lower() for t in ["rev", "profit", "price", "cost", "sales", "amount"])
                    prefix = "$" if is_money else ""
                    kpis.append({
                        "id": f"{tbl}_{primary_num}",
                        "title": clean_title("Total", primary_num),
                        "value": f"{prefix}{tv:,.2f}" if is_money else f"{tv:,.2f}",
                        "subtitle": f"Average: {prefix}{av:,.2f}",
                        "trend": "+Volume"
                    })

            if secondary_num and len(kpis) < 4:
                res2, _, _ = execute_safe_query(f'SELECT ROUND(SUM("{secondary_num}"), 2) as total_val, ROUND(AVG("{secondary_num}"), 2) as avg_val FROM "{tbl}";')
                if res2 and res2[0].get("total_val") is not None:
                    tv2 = res2[0]["total_val"]
                    is_money2 = any(t in secondary_num.lower() for t in ["rev", "profit", "price", "cost", "sales", "amount"])
                    prefix2 = "$" if is_money2 else ""
                    kpis.append({
                        "id": f"{tbl}_{secondary_num}",
                        "title": clean_title("Total", secondary_num),
                        "value": f"{prefix2}{tv2:,.2f}" if is_money2 else f"{tv2:,.2f}",
                        "subtitle": "Secondary metric",
                        "trend": "+Aggregated"
                    })

        # Chart 1: Categorical vs Primary Metric (Bar)
        for cat in categorical_cols:
            if cat in used_x_keys:
                continue
            dist_rows, _, _ = execute_safe_query(f'SELECT COUNT(DISTINCT "{cat}") as d_cnt FROM "{tbl}" WHERE "{cat}" IS NOT NULL;')
            dc = dist_rows[0].get("d_cnt", 0) if dist_rows else 0
            if 3 <= dc <= 30 and primary_num:
                q = f'SELECT "{cat}", ROUND(SUM("{primary_num}"), 2) AS "{primary_num}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL AND "{cat}" != "" GROUP BY "{cat}" ORDER BY "{primary_num}" DESC LIMIT 10;'
                rows, _, _ = execute_safe_query(q)
                if rows and len(rows) >= 2:
                    charts.append({
                        "id": f"{tbl}_{cat}_{primary_num}",
                        "type": "bar",
                        "title": f"{primary_num.replace('_', ' ').title()} by {cat.replace('_', ' ').title()}",
                        "description": f"Breakdown of {primary_num.replace('_', ' ')} across top {cat.replace('_', ' ')} categories",
                        "xAxisKey": cat,
                        "yAxisKeys": [primary_num],
                        "data": rows,
                    })
                    used_x_keys.add(cat)
                    break

        # Chart 2: Proportion / Pie Chart for Low-Cardinality Category (2 to 6 unique values)
        for cat in categorical_cols:
            if cat in used_x_keys:
                continue
            dist_rows, _, _ = execute_safe_query(f'SELECT COUNT(DISTINCT "{cat}") as d_cnt FROM "{tbl}" WHERE "{cat}" IS NOT NULL;')
            dc = dist_rows[0].get("d_cnt", 0) if dist_rows else 0
            if 2 <= dc <= 6:
                val_col = primary_num if primary_num else "volume"
                if primary_num:
                    q_pie = f'SELECT "{cat}", ROUND(SUM("{primary_num}"), 2) AS "{val_col}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL GROUP BY "{cat}" ORDER BY "{val_col}" DESC;'
                else:
                    q_pie = f'SELECT "{cat}", COUNT(*) AS "{val_col}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL GROUP BY "{cat}" ORDER BY "{val_col}" DESC;'
                pie_data, _, _ = execute_safe_query(q_pie)
                if pie_data and len(pie_data) >= 2:
                    charts.append({
                        "id": f"{tbl}_{cat}_share",
                        "type": "pie",
                        "title": f"{cat.replace('_', ' ').title()} Distribution",
                        "description": f"Proportional share across {cat.replace('_', ' ')} segments",
                        "xAxisKey": cat,
                        "yAxisKeys": [val_col],
                        "data": pie_data,
                    })
                    used_x_keys.add(cat)
                    break

        # Chart 3: Second Categorical Metric Bar Chart
        for cat in categorical_cols:
            if cat in used_x_keys or len(charts) >= 5:
                continue
            dist_rows, _, _ = execute_safe_query(f'SELECT COUNT(DISTINCT "{cat}") as d_cnt FROM "{tbl}" WHERE "{cat}" IS NOT NULL;')
            dc = dist_rows[0].get("d_cnt", 0) if dist_rows else 0
            metric_to_use = secondary_num if secondary_num else primary_num
            if 2 <= dc <= 30 and metric_to_use:
                q2 = f'SELECT "{cat}", ROUND(SUM("{metric_to_use}"), 2) AS "{metric_to_use}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL AND "{cat}" != "" GROUP BY "{cat}" ORDER BY "{metric_to_use}" DESC LIMIT 8;'
                rows2, _, _ = execute_safe_query(q2)
                if rows2 and len(rows2) >= 2:
                    charts.append({
                        "id": f"{tbl}_{cat}_{metric_to_use}",
                        "type": "bar",
                        "title": f"{metric_to_use.replace('_', ' ').title()} by {cat.replace('_', ' ').title()}",
                        "description": f"Aggregated {metric_to_use.replace('_', ' ')} comparison across {cat.replace('_', ' ')}",
                        "xAxisKey": cat,
                        "yAxisKeys": [metric_to_use],
                        "data": rows2,
                    })
                    used_x_keys.add(cat)
                    break

        # Chart 4: Timeline Trend (Line Chart)
        if date_cols and len(charts) < 6:
            d_col = date_cols[0]
            val_col = primary_num if primary_num else "records"
            if primary_num:
                q_trend = f'''
                SELECT 
                    CASE 
                        WHEN "{d_col}" LIKE '%/%/%' THEN substr("{d_col}", length("{d_col}")-3, 4)
                        ELSE substr("{d_col}", 1, 7)
                    END AS period,
                    ROUND(SUM("{primary_num}"), 2) AS "{val_col}"
                FROM "{tbl}"
                WHERE "{d_col}" IS NOT NULL AND "{d_col}" != ""
                GROUP BY period
                ORDER BY period ASC
                LIMIT 20;
                '''
            else:
                q_trend = f'''
                SELECT 
                    CASE 
                        WHEN "{d_col}" LIKE '%/%/%' THEN substr("{d_col}", length("{d_col}")-3, 4)
                        ELSE substr("{d_col}", 1, 7)
                    END AS period,
                    COUNT(*) AS "{val_col}"
                FROM "{tbl}"
                WHERE "{d_col}" IS NOT NULL AND "{d_col}" != ""
                GROUP BY period
                ORDER BY period ASC
                LIMIT 20;
                '''
            trend_data, _, _ = execute_safe_query(q_trend)
            if trend_data and len(trend_data) >= 2 and trend_data[0].get("period"):
                charts.append({
                    "id": f"{tbl}_trend",
                    "type": "line",
                    "title": f"Timeline Trend over {d_col.replace('_', ' ').title()}",
                    "description": f"Historical trajectory of {val_col.replace('_', ' ')} across periods",
                    "xAxisKey": "period",
                    "yAxisKeys": [val_col],
                    "data": trend_data,
                })

        # Chart 5: Top 5 Entities (e.g. Country or Customer or Title)
        for cat in categorical_cols:
            if cat in used_x_keys or len(charts) >= 5:
                continue
            if any(k in cat.lower() for k in ["country", "name", "customer", "product", "item", "city", "client", "company"]):
                metric = primary_num if primary_num else "records"
                if primary_num:
                    q_top = f'SELECT "{cat}", ROUND(SUM("{primary_num}"), 2) AS "{metric}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL GROUP BY "{cat}" ORDER BY "{metric}" DESC LIMIT 5;'
                else:
                    q_top = f'SELECT "{cat}", COUNT(*) AS "{metric}" FROM "{tbl}" WHERE "{cat}" IS NOT NULL GROUP BY "{cat}" ORDER BY "{metric}" DESC LIMIT 5;'
                top_data, _, _ = execute_safe_query(q_top)
                if top_data and len(top_data) >= 2:
                    charts.append({
                        "id": f"{tbl}_top_{cat}",
                        "type": "bar",
                        "title": f"Top 5 {cat.replace('_', ' ').title()} by {metric.replace('_', ' ').title()}",
                        "description": f"Highest volume accounts in {cat.replace('_', ' ')}",
                        "xAxisKey": cat,
                        "yAxisKeys": [metric],
                        "data": top_data,
                    })
                    used_x_keys.add(cat)
                    break

    # Anomaly Diagnostics
    anomalies = detect_all_workspace_anomalies()
    kpis.append({
        "id": "anomalies",
        "title": "Anomalies Flagged",
        "value": f"{len(anomalies)}",
        "subtitle": "Statistical & domain outliers",
        "trend": "Needs Review" if len(anomalies) > 0 else "Clean",
    })

    return {
        "has_data": True,
        "kpis": kpis,
        "charts": charts,
        "anomalies": anomalies,
    }
