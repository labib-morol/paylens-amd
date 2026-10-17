# PayLens Architecture Rules (Mandatory)
1. CODE COMPUTES, MODEL EXPLAINS: All matching, leak totals, Holt-Winters demand forecasts, STL anomalies, and ranking scores (impact * confidence * goal_weight) MUST be computed in Python/DuckDB/statsmodels. The LLM (google/gemma-4-31B-it on AMD MI300X via vLLM) never calculates numbers.
2. GROUNDING CHECK: Every number in the LLM's English or Bangla output must be regex-extracted (converting Bengali digits ০১২৩৪৫৬৭৮৯ to ASCII) and verified against the tool results. If a mismatch occurs, retry once, then fall back to a deterministic template and log the telemetry.
3. ENDPOINT FALLBACK: Support primary `AMD_VLLM_BASE_URL` (`http://localhost:8000/v1` for MI300X SSH tunnel), backup `AMD_TOKENFACTORY_BASE_URL` (`https://notebooks.amd.com/tokenfactory/v1`), and instant offline template fallback so local development works with zero GPU connected.
4. NO SECRETS IN GIT: Load all keys from `.env` and exclude `.env` in `.gitignore`.
