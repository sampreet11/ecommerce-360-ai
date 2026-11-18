# Interview guide

**30-second pitch.** I extended an Olist analytics project (SQL, Power BI, Python) into a full-stack app: PostgreSQL views at
the right grain, a FastAPI backend, a React dashboard, and an AI analyst that converts questions to validated read-only SQL,
runs it under a restricted role, and explains only the returned numbers.

**Q: How do you stop the LLM inventing numbers?** It never computes figures: SQL does. Narration gets only result rows, charts
come from rows, and a post-check flags numbers not found in the result.
**Q: How is the SQL made safe?** Tokenizer validation + allow-list + forced LIMIT + read-only role/transaction + timeout + audit log.
**Q: Why not just string-match "DROP"?** Bypasses (CTE writes, comments, functions); defence in depth, with the DB role as the real barrier.
**Q: Grain pitfalls?** fact_sales is per item, so orders/delivery use `v_order_level`; a test asserts orders < item rows.
**Q: What did you find in the data?** README figures used all-status revenue and slightly different denominators; delivered-only
numbers differ (see data-dictionary). I surfaced it rather than hiding it.
**Q: Limitations?** No reviews/payments/cost in the supplied data; historical (2018); baseline forecast; demo auth;
frontend and PostgreSQL paths were not executed in the build sandbox (see README "Verification").
**Q: What would you do next?** Add reviews table, pgvector-free semantic layer, streaming, real auth, CI.
