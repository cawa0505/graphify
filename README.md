# GraphifyCustom

Based on [graphify](https://github.com/Graphify-Labs/graphify) v0.9.25 by Safi Shamsi (Apache-2.0 + MIT).  
**Upstream:** https://github.com/Graphify-Labs/graphify

Custom fork with patches for homelab use: structured config, key rotation, rate-limit resilience, and extraction tuning.

## Install

```bash
# pip (editable, local)
pip install --user --break-system-packages -e /path/to/GraphifyCustom

# uv (editable, local)
uv pip install --user -e /path/to/GraphifyCustom

# remote (from GitHub)
pip install git+https://github.com/cawa0505/graphify@v8
uv pip install git+https://github.com/cawa0505/graphify@v8
```

Requires Python 3.14+. Tree-sitter SQL support: `pip install graphifyy[sql]`.

## Custom Patches

### 1. Structured Config (`~/.graphify/config.json`)

No env vars needed. Providers and extraction settings in one file:

```json
{
  "backend": "gemini",
  "providers": {
    "gemini": {
      "api_key": ["key1", "key2", "key3"],
      "model": "gemini-3-flash-preview",
      "extraction": {
        "chunk_size": 2
      }
    },
    "openai": {
      "api_key": "sk-xxx",
      "base_url": "https://your-proxy/v1",
      "model": "qwen2.5-coder-7b"
    }
  },
  "extraction": {
    "chunk_size": 1,
    "max_concurrency": 1,
    "max_completion_tokens": 8192
  }
}
```

- **Per-provider override**: `providers.<backend>.extraction` overrides global `extraction.*` settings (e.g., Gemini `chunk_size: 2` to stay under 20 req/day).
- Old flat structure (`api_keys`, `base_urls`, `models`) still works as fallback.

### 2. API Key Rotation

`api_key` accepts a **string or array**. On daily quota exhaustion (`RESOURCE_EXHAUSTED`), automatically rotates to the next key and retries — no sleep.

```json
"api_key": ["key-project-1", "key-project-2", "key-project-3", "key-project-4"]
```

Works in both `_call_openai_compat` (extraction) and `_call_llm` (community labeling). 4 keys × 20 req/day = 80 requests/day on Gemini free tier.

### 3. 429/503 Rate-Limit Retry

Automatic retry on rate-limit and temporary unavailability errors:
- Parses `retryDelay` from error response (Gemini format), falls back to exponential backoff
- Retries on both **429** (rate limit / quota exhausted) and **503** (temporary unavailability)
- Configurable via `extraction.max_retries` in config.json (default: 20)

### 4. CLI Flags: `--chunk-size` and `--max-concurrency`

```bash
graphify . --chunk-size 1 --max-concurrency 1
```

- `--chunk-size N` — max source files per extraction chunk (default: 20)
- `--max-concurrency N` — parallel extraction workers (default: 1)

Both fall back to `extraction.*` in config.json (with per-provider override), then to CLI defaults.

### 5. Markdown Fence Stripping

Models that wrap JSON in `` ```json ``` `` fences are handled — the parser strips fences and extracts valid JSON before falling back to depth-based extraction.

### 6. `**kwargs` on `extract_corpus_parallel()`

Allows CLI-passed kwargs (like `cache_root`) without crashing on signature mismatch.

### 7. `_partial_source_files` stub

Prevents import crashes when semantic extraction returns incomplete source file references.
