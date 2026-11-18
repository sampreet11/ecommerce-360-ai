# E-Commerce 360° Customer & Business Intelligence Platform

An end-to-end Business Intelligence project built on the **Olist Brazilian E-Commerce Public Dataset**, combining SQL, Python, Excel, Power BI and DAX to analyze customer behavior, category performance, delivery operations and near-term revenue trends.

## Quick start (Python forecast)

From the extracted repository root:

```bash
python -m pip install -r requirements.txt
python Python/analysis_and_forecasting.py
```

The script locates `Data/processed/fact_sales.csv` relative to its own location, so it does not depend on your terminal's working directory. It prints a six-month rolling-mean baseline forecast; this is a simple directional baseline, not a trained machine-learning model.

## Project at a glance

| Area | What was analyzed |
|---|---|
| Customer Intelligence | Repeat behavior, RFM segmentation, cohort retention and customer lifecycle |
| Product & Category | Revenue concentration, category performance and product-level trends |
| Operations | Delivery time, late-order rate, freight and seller-state patterns |
| Forecasting | Six-month revenue forecast based on historical monthly performance |
| BI Delivery | Interactive Power BI dashboard with executive recommendations |

## Key business metrics

- **$13.59M** total sales
- **2.9%** repeat-customer rate
- **7.9%** late-delivery rate
- **12.5 days** average delivery time
- **~8K** late orders
- **$2.25M** total freight

> Metrics are calculated from the project model and should be interpreted within the Olist dataset's historical coverage and definitions.

## Dashboard

The Power BI report contains five pages:

1. **Executive Overview** — overall sales, customers, orders and business performance
2. **Customer Intelligence** — retention, cohorts, RFM segments and revenue contribution
3. **Product & Category Intelligence** — category and product performance
4. **Operations & Forecasting** — delivery performance, freight, late orders and six-month forecast
5. **Executive Insights & Business Recommendations** — key findings translated into business actions

### Dashboard screenshots

Open the `Screenshots/` folder for the available dashboard views.

## Business questions

- How strong is repeat purchasing and where is the retention opportunity?
- Which customer segments contribute the most revenue?
- Which product categories drive the largest share of sales?
- Where are delivery delays concentrated?
- How does delivery performance relate to customer experience?
- What does the near-term revenue trend look like?

## Analytical approach

### 1. Data preparation

The project uses the Olist public e-commerce dataset and combines orders, order items, customers, products, sellers, payments, reviews and geographic information.

### 2. Data modeling

A dimensional Power BI model was created with a central `fact_sales` table and supporting dimensions for customers, products, sellers and dates.

### 3. Customer analytics

- Repeat-customer analysis
- RFM segmentation
- Cohort retention
- Customer lifecycle analysis
- Revenue contribution by customer segment

### 4. Product analytics

- Category revenue analysis
- Category concentration
- Product-level performance
- Market-basket category pair analysis

### 5. Operations analytics

- Average delivery time
- Late-delivery rate
- Late orders by seller state
- Freight by state
- Review-score analysis where available in the model

### 6. Forecasting

A six-month revenue forecast was prepared from historical monthly revenue trends. The forecast is directional and should not be interpreted as a guaranteed business outcome.

## Technology stack

**Power BI · DAX · SQL · Python · Pandas · Excel**

## Repository structure

```text
Ecommerce-360-Analytics/
├── README.md
├── PowerBI/
│   ├── Ecommerce 360 Analytics.pbix
│   └── DAX_measures.txt
├── SQL/
│   └── SQL analysis scripts
├── Python/
│   └── analysis_and_forecasting.py
├── Excel/
│   └── ecommerce_360_analysis.xlsx
├── Data/
│   └── processed/ model-ready datasets
└── Screenshots/
```

## Important data limitation

The Olist dataset does **not** contain true product cost, profit/margin or discount fields. Therefore, this project does not present those metrics as actual historical business facts. The dataset is also historical and is not a subscription dataset, so customer lifecycle findings are framed as repeat/lapsed behavior rather than definitive subscription churn.

## Business recommendations

Based on the analysis, the project highlights five areas for action:

1. **Customer retention:** strengthen post-purchase engagement, cross-sell and reactivation initiatives.
2. **Delivery operations:** investigate seller/state combinations with consistently high late-order volumes.
3. **Category strategy:** prioritize high-revenue categories for assortment and inventory planning.
4. **Customer experience:** investigate operational factors associated with lower review scores.
5. **Regional operations:** compare freight and delivery performance across major seller/customer states.

## Project deliverables

- Interactive Power BI dashboard (`.pbix`)
- DAX measure library
- SQL analysis scripts
- Python analysis and forecasting script
- Excel analysis workbook
- Model-ready processed datasets

## Dataset

This project uses the **Olist Brazilian E-Commerce Public Dataset**, a publicly available historical e-commerce dataset. The repository contains model-ready processed data rather than a full duplicate of the original raw dataset to keep the GitHub repository practical.

---

**Portfolio project:** E-Commerce 360° Customer & Business Intelligence Platform  
**Focus:** Data Analytics · Business Intelligence · Customer Analytics · Operations Analytics


## Local analytics chatbot prototype (Windows)

This adds a small local chat interface over the included `Data/processed/fact_sales.csv`.
It currently answers a limited set of predefined analytics questions with deterministic
calculations and explains the basis for each answer. **It is not yet an LLM/GenAI chatbot**:
there is no API key, generated SQL, or external service required. This safe first milestone
lets you verify the app and data flow before connecting an LLM.

### Run it

1. Install Python 3.10 or newer.
2. Open PowerShell in the extracted `Ecommerce_360_GitHub` project folder.
3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   ```

   If PowerShell blocks activation, use Command Prompt instead:

   ```bat
   .venv\\Scripts\\activate.bat
   ```

4. Install dependencies:

   ```powershell
   py -m pip install -r requirements.txt
   ```

5. Start the local app:

   ```powershell
   py -m uvicorn ai_chatbot.app:app --reload
   ```

6. Open `http://127.0.0.1:8000` in your browser. Stop the server with `Ctrl+C`.

### Supported starter questions

- What is total revenue / sales?
- How many orders?
- Top product categories by revenue?
- Show monthly revenue.
- What is average delivery time?
- What is the late delivery rate?
- What is the repeat customer rate?
- Help

The late-delivery and average-delivery metrics count each delivered order once,
rather than counting each order-item row as a separate order. The source CSV is
order-item grain; revenue is calculated by summing its `sales` column. Revenue here
means sales, not profit.

### Troubleshooting

- Run commands from the extracted project root, the folder containing `README.md`.
- Confirm `Data\\processed\\fact_sales.csv` exists.
- If `py` is not recognized, install Python from python.org and enable the PATH option.
- If port 8000 is busy, run `py -m uvicorn ai_chatbot.app:app --reload --port 8001`
  and open `http://127.0.0.1:8001`.

### Next implementation milestone

After the local prototype runs, add an LLM-backed intent/SQL layer with strict read-only
database permissions, approved tables/columns, query validation, row/time limits, and
answer citations to the executed query. Do not let the model invent KPI values.
