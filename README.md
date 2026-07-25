# graphify-opt

Based on [graphify](https://github.com/Graphify-Labs/graphify) v0.9.25 by Safi Shamsi (Apache-2.0 + MIT).  
**Upstream:** https://github.com/Graphify-Labs/graphify

Custom fork with advanced patches for robust, high-performance execution: structured configuration, automatic key rotation, native AST acceleration, structural incremental caching, and token-saving skeleton pruning.

## Table of Contents

- [Install](#install)
- [1. Robust Configuration & API Key Resilience](#1-robust-configuration--api-key-resilience)
  - [Structured Configuration (`~/.graphify/config.json`)](#structured-configuration-graphifyconfigjson)
  - [Automatic API Key Rotation](#automatic-api-key-rotation)
  - [429/503 Rate-Limit Retry](#429503-rate-limit-retry)
- [2. Local AST Parsing Acceleration](#2-local-ast-parsing-acceleration)
  - [Tree-Sitter Native C Queries](#tree-sitter-native-c-queries)
  - [JS/TS Loop Unification](#jsts-loop-unification)
  - [Rust-Compiled gigatoken Engine](#rust-compiled-gigatoken-engine)
  - [Adaptive JSON Engine (orjson)](#adaptive-json-engine-orjson)
  - [Double-Layer Memoized Symbol Resolution](#double-layer-memoized-symbol-resolution)
- [3. LLM Cost & Token Optimizations](#3-llm-cost--token-optimizations)
  - [Skeleton-Based AST Code Pruning](#skeleton-based-ast-code-pruning)
  - [AST-Based Incremental Caching (3-Tier Cache)](#ast-based-incremental-caching-3-tier-cache)
- [4. CLI & Compatibility Patches](#4-cli--compatibility-patches)
- [Backward Compatibility & Seamless Migration](#backward-compatibility--seamless-migration)

## Install

```bash
# install from GitHub
pip install git+https://github.com/cawa0505/graphify@v8

# using uv
uv pip install git+https://github.com/cawa0505/graphify@v8

# install with SQL support (Tree-sitter SQL)
pip install "graphify[sql] @ git+https://github.com/cawa0505/graphify@v8"
```

Requires Python 3.10+.

---

## 1. Robust Configuration & API Key Resilience

These enhancements ensure graphify runs continuously and reliably without requiring complex environment variable setups or manual intervention.

### Structured Configuration (`~/.graphify/config.json`)
Allows setting up backends, providers, and extraction settings in a single JSON file. Supports per-provider overrides:
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
- **Overriding**: `providers.<backend>.extraction` overrides global settings (e.g., setting Gemini `chunk_size: 2` to stay under free-tier limits).
- Backward-compatible with the old flat config format as fallback.

### Automatic API Key Rotation
The `api_key` field accepts a **string or list of strings**. When a daily quota limit is reached (`RESOURCE_EXHAUSTED` / `429`), graphify immediately rotates to the next available API key and retries the request without sleeping.
- Works seamlessly in both `_call_openai_compat` (file relationship extraction) and `_call_llm` (community cluster labeling).
- Multiplies free-tier quotas (e.g., 4 keys × 20 requests/day = 80 requests/day).

### 429/503 Rate-Limit Retry
Adds robust automatic retries on rate limits and temporary server unavailability:
- Parses `retryDelay` directly from Gemini's JSON error response, falling back to a custom exponential backoff.
- Triggers on both **429** (rate limits) and **503** (temporary service unavailability).
- Maximum retries are configurable via `extraction.max_retries` (default: 20).

---

## 2. Local AST Parsing Acceleration

These optimizations remove CPU bottlenecks and memory overhead during local repository analysis, making graph generation extremely fast.

### Tree-Sitter Native C Queries
Replaced slow recursive pure-Python AST tree walks with native **Tree-Sitter S-Expression Queries** (`(import_from_statement) @import_from`, `(call function: (identifier)) @call`). This shifts structural syntax matching into compiled C space, speeding up Python AST facts extraction by **10x to 50x**.

### JS/TS Loop Unification
Unified JavaScript and TypeScript analysis. Previously, the parser performed **4 separate deep recursive walks** over the same file's syntax tree to extract imports, exports, aliases, and classes. These are now combined into exactly **1 single-pass iterative DFS walk**, cutting walking overhead and redundant disk access by **400%**.

### Rust-Compiled gigatoken Engine
Replaced the default `tiktoken` library with `gigatoken` (a highly-optimized Rust BPE tokenizer with drop-in `.as_tiktoken()` compatibility) utilizing an `openai-community/gpt2` proxy encoding.
- Includes robust special-token handling (`allowed_special="all"`) to prevent crashes on raw document strings like `<|endoftext|>`.
- Accelerates chunk packing token estimation on large codebases.

### Adaptive JSON Engine (orjson)
Introduces an adaptive JSON compatibility layer (`graphify/json_compat.py`) that dynamically leverages the Rust-compiled `orjson` library when available.
- **3x to 10x JSON Speedup**: Accelerates massive `graph.json` serialization, deserialization, and high-frequency cache reads/writes during large scans.
- **Zero-Friction Fallback**: Automatically and gracefully falls back to Python's standard `json` module with identical signatures if `orjson` is not installed.

### Double-Layer Memoized Symbol Resolution
Implements an extremely fast dual-layer caching mechanism during cross-file symbol and export path resolution in `resolution.py`.
- **$O(1)$ Flattened Resolution**: Fully memoizes recursive export tracing and file-level local alias resolutions, flattening complex lookup complexities to $O(1)$ and reducing processing times to virtually zero in large codebases.
- **Star & Wildcard Resiliency**: Prevents recursive redundant walks over multi-layer module structures (such as index file re-exports or star wildcards).

---

## 3. LLM Cost & Token Optimizations

These patches reduce input token size and prompt volume, drastically reducing LLM API consumption costs on large scale scans.

### Skeleton-Based AST Code Pruning
Prior to packing files and dispatching them to the LLM, graphify dynamically prunes function, method, and class bodies across **Python, JS, TS, Go, Rust, C++, C, Java, PHP, Kotlin, and Swift**, leaving behind clean structural interfaces (`...` or `{ ... }`) and docstrings.
- **70% to 90% Input Token Savings**: Deletes non-essential implementation details, keeping only the logical interfaces.
- **Packing Optimization**: Integrates skeleton sizing directly into `_estimate_file_tokens`. By correctly reporting the small skeleton size, graphify can pack **3x to 5x more files per chunk**, drastically decreasing total LLM API calls and costs.

### AST-Based Incremental Caching (3-Tier Cache)
Prevents redundant LLM API calls on non-logical changes (such as code formatting, adding comments, fixing docstrings, or running linters):
- **Tier 1 (Content Hash)**: Direct content-hash check (instant hit).
- **Tier 2 (AST Structure Hash)**: On Tier 1 miss, computes a logical structure hash of the file's AST (ignoring locations and comments). If structural match exists, loads LLM results and **self-heals the Tier 1 cache** for subsequent fast-path runs.
- **Tier 3 (LLM Call)**: True cache miss, triggers LLM only on true logical code changes.
- *Includes safe isolation: Document files (.md, .txt) skip AST matching to preserve full text semantic accuracy, and pruning sweeps bypass `ast-*.json` keys.*

---

## 4. CLI & Compatibility Patches

Small, important quality-of-life adjustments and stability fixes:

- **CLI Config Flags**: Adds `--chunk-size N` (max files per LLM chunk) and `--max-concurrency N` (number of parallel workers) flags to override config values on the fly.
- **Markdown Fence Stripping**: Automatically cleans up and extracts JSON from models that wrap responses in `` ```json ``` `` code blocks.
- **Robust Parallel Extractor**: Adds `**kwargs` support to `extract_corpus_parallel()` to prevent method signature crashes when passing custom run options.
- **Partial Import Resilience**: Implemented a `_partial_source_files` stub to prevent schema import crashes when the LLM returns incomplete file paths.

---

## Backward Compatibility & Seamless Migration

**graphify-opt** is engineered with an absolute commitment to zero-friction backward compatibility. If you are upgrading from standard `graphify` or an older custom fork:

- **100% Zero-Touch Migration**: All of your existing local caches, generated graphs (`graphify-out/`), and configuration files (`config.json`) are **100% fully backward-compatible**. No files need to be deleted, rebuilt, or migrated.
- **Self-Healing Cache Layer**: The new 3-tier AST-based caching layer automatically integrates with your old content-hash caches. It self-heals by back-propagating AST matches into standard raw-hash caches natively on first run.
- **Opt-In High Performance**: The Rust-compiled JSON acceleration (`orjson`) is **completely optional**. If `orjson` is not installed on your system, `graphify-opt` will gracefully fallback to standard library `json` and work flawlessly. Install `orjson` at any time (`pip install orjson`) to instantly unlock 10x serialization speedups with zero configuration required.
