# Image Extract Prompt (Vision LLM)

This document records the full content of `EXTRACT_PROMPT` in `src/services/image_stock_extractor.py`, for evaluating instruction effectiveness during PR reviews.

**When modifying EXTRACT_PROMPT**: Please update this file accordingly and include the full before/after change in the PR description so reviewers can assess the optimization level for code+name+confidence extraction.

---

## Current Prompt (Full)

```
Please analyze this stock market screenshot or image and extract all visible stock codes and their names.

Important: If the image displays both stock names and codes (e.g., watchlist, ETF list), you must extract both for each element. Each element must include code and name fields.

Output format: Return only a valid JSON array, no markdown, no explanation.
Each element is an object: {"code":"stock code","name":"stock name","confidence":"high|medium|low"}
- code: required, stock code (A-share 6-digit, HK 5-digit, US 1-5 letters, ETF like 159887/512880)
- name: required if visible in the image (e.g., Kweichow Moutai, Bank ETF, Securities ETF), corresponding one-to-one with the code; may be omitted only if no name is visible in the image
- confidence: required, recognition confidence, high=certain, medium=likely, low=uncertain

Examples (when both name and code are in the image):
- A-shares: 600519 Kweichow Moutai, 300750 CATL
- HK stocks: 00700 Tencent Holdings, 09988 Alibaba
- US stocks: AAPL Apple, TSLA Tesla
- ETFs: 159887 Bank ETF, 512880 Securities ETF, 512000 Broker ETF, 512480 Semiconductor ETF, 515030 New Energy Vehicle ETF

Output example: [{"code":"600519","name":"Kweichow Moutai","confidence":"high"},{"code":"159887","name":"Bank ETF","confidence":"high"}]

Do not return only a code array like ["159887","512880"]; you must use the object format. If no stock codes are found, return: []
```
