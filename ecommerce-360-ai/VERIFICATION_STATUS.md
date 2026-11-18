# Verification status (2026-11-06)

## What was checked
- The archive opens and passes ZIP integrity validation.
- Reviewed the PostgreSQL setup schema, order-level delivery KPI SQL, and DAX measure definitions included in the project.
- Confirmed the revised DAX `Items` measure is `COUNTROWS(FactSales)`, matching the one-row-per-order-item fact grain.
- Confirmed delivery KPI SQL groups by `order_id` before calculating order-level averages and late rates.

## What was not executed
- No live PostgreSQL server or connection was available in this environment, so the setup/import and SQL scripts were not executed against PostgreSQL.
- The `.pbix` report cannot be refreshed or queried here because Power BI Desktop / its model engine is unavailable. Therefore no SQL-to-dashboard reconciliation is claimed.

## Required local verification
1. Start PostgreSQL and create/import the nine raw Olist CSV tables using `SQL/01_database_setup.sql`.
2. Run `SQL/02_data_cleaning.sql` followed by the analysis scripts in numeric order.
3. Record the results of the order-level delivery KPIs and compare them with the Power BI report after refreshing its data model.
4. Reconcile differences caused by grain/filters/date scope and document the final approved KPI values before connecting the GenAI chat.

## Metric interpretation
`fact_sales` has one row per order item. Sales and item counts belong at item grain; order counts and delivery performance should count each order once. The forecast remains a rolling-mean baseline, not a trained ML model.
