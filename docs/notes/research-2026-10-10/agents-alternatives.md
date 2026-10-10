# Alternatives and supporting-technology scan (AI layer, PDF, debate evidence)

Read-only scan on 2026-10-10. I ran 11 web searches and fetched pages; every URL was accessed that day. Nothing was installed, run or imported, and no LLM provider was called. Clone paths are relative to `C:\Users\mirza\AppData\Local\Temp\claude\c--Users-mirza-Desktop-Hackathon-project-50k\fcb59ff2-d20e-4984-b01d-14d47f0bf736\scratchpad\tradingagents` (TradingAgents v0.6.0, `tradingagents/__init__.py:3`). I also read DEC-028, DEC-029 and the draft build plan (`...\scratchpad\app-lf\plans\2026-10-10-product-build-plan.md`). **[U]** marks a claim not confirmed against a primary source.

## Bottom line

1. **Don't use an agent framework this weekend.** The plan needs one schema-bound call per decision and a bounded, read-only chat loop. The plain `openai` client (plan D5 pins 3.28.0) handles both. Skipping frameworks also avoids a collision with the handoff rule "no multi-agent framework unless a recorded need is approved".
2. **Keep the plan's critic design:** deterministic validators plus one retry. Research shows critique helps when it is grounded in external checks, and that most of what debate gains comes from voting. If more reliability is wanted, use agreement across 3 samples, and only for insurance trigger assessments.
3. **PDF: use Typst** (the `typst` Python package). WeasyPrint is the fallback.
4. **Plan D6 needs a correction.** It says `store: false` means "nothing stored at OpenAI". In fact OpenAI keeps abuse-monitoring logs for up to 30 days by default.
5. **Open-source finance agents are pattern references only.** All the comparable projects produce ratings, price targets or trades.

## 1. OpenAI Agents SDK (Python)

| Item | Finding |
|---|---|
| Package | `openai-agents` 0.23.1 (2026-10-02), MIT licence, Python ≥3.10 |
| Dependencies (main-branch pyproject) | `openai>=3.0.0,<4` (compatible with our pin), pydantic, griffelib, requests, websockets, `mcp`, `starlette>=1.3.1`, pyjwt, python-multipart and more |
| API | "uses the Responses API by default for OpenAI models". Chat Completions is also supported |
| Agents and handoffs | An agent is instructions plus tools. In a handoff, another agent "receives the conversation history and takes over". `as_tool()` keeps a manager agent in control |
| Structured output and tools | `output_type` switches the model to structured outputs. `@function_tool` builds the tool schema from the Python signature (strict mode by default [U]). `needs_approval` pauses a run; the paused state can be saved with `RunState.to_json()` and resumed later |
| Guardrails | Input guardrails run on the first agent, output guardrails on the final agent, tool guardrails on function tools only. A tripped guardrail raises an exception. Input guardrails run in parallel with the agent unless set to blocking |
| Limits and usage | `max_turns` raises `MaxTurnsExceeded`. `ModelSettings` has `store`, `max_tokens`, `timeout`, `retry` and `response_include`. `result.context_wrapper.usage` reports tokens, including cached and reasoning tokens |
| **Tracing** | **On by default.** Traces are exported "to the OpenAI backend". `trace_include_sensitive_data` defaults to **True**, so model and tool inputs and outputs are included. Turn it off with `OPENAI_AGENTS_DISABLE_TRACING=1`, `set_tracing_disabled(True)` or `RunConfig.tracing_disabled`. `set_trace_processors()` replaces the exporter, for example with a local PostgreSQL writer. Tracing is unavailable to Zero Data Retention (ZDR) organisations |

**How it would run in our worker:**
- **Decision jobs:** claim a job with `SKIP LOCKED`, build the evidence packet, then call `Runner.run_sync(agent, packet, max_turns=…, run_config=RunConfig(tracing_disabled=True, model_settings=ModelSettings(store=False, …)))`. In an asyncio worker, use `await Runner.run(...)` instead.
- **Chat in FastAPI:** use `Runner.run_streamed` and map its events to server-sent events.
- **Job lease:** it must outlast the worst-case run.
- **$20 cap:** the per-call cost reservation needs a hook or model wrapper that fires before each call [U which hook does].
- **Reasoning models with `store: false`:** tool loops must request `reasoning.encrypted_content` and send the reasoning items back unchanged. This applies to a hand-written loop too.

**Recommendation:**
- **Decisions:** don't use the SDK. A single schema-bound call gains nothing from it.
- **Chat:** it might save about an hour [estimate]. In exchange it adds a pre-1.0 dependency, a Starlette minimum version to check against FastAPI's pin [U conflict], and tracing that must be switched off.
- **If adopted anyway:** pin `==0.23.1`, disable tracing both by environment variable and in code, and record the need in a DEC.

## 2. LangGraph and LangChain (as TradingAgents uses them)

- **What TradingAgents needs.** It is Apache-2.0 and requires `langgraph>=1.2.12`, `langgraph-checkpoint-sqlite>=3.1.1`, `langchain-core>=1.6.5`, `langchain-openai>=1.6.6`, Anthropic and Google adapters, pandas ≥3 and yfinance (`pyproject.toml:11-29`). It keeps per-ticker SQLite checkpoints (`tradingagents/graph/checkpointer.py:14,42-47`).
- **Current versions on PyPI, all MIT:**
  - `langgraph` 1.2.14 (2026-10-06)
  - `langchain-core` 1.6.9 (2026-10-08)
  - `langchain-openai` 1.7.0 (2026-10-08)
- **Dependency weight:**
  - `langgraph` pulls in langchain-core, langgraph-checkpoint, langgraph-sdk, langgraph-prebuilt and xxhash.
  - `langchain-core` pulls in langsmith, httpx, tenacity, jsonpatch, PyYAML, packaging, uuid-utils and langchain-protocol.
  - `langchain-openai` pulls in `openai>=2.45,<4` and tiktoken.
  - LangSmith tracing is opt-in: it needs `LANGSMITH_TRACING=true` plus an API key.
- **Cost per run** (counted from the code, not run): at least 12 model calls per default run, before any tool-call iterations:
  - 4 analysts (`tradingagents/graph/trading_graph.py:56`);
  - per debate round, 2 bull/bear turns and 3 risk turns (`graph/conditional_logic.py:16,26`);
  - a research manager, a trader and a portfolio manager (`graph/setup.py:148-155`).
- **Output:** a Buy/Overweight/Hold/Underweight/Sell rating (`agents/rating.py:3,23`).

**Recommendation: don't adopt it.** Its checkpoints would duplicate our PostgreSQL queue and the append-only `ai.*` tables. Copying its code or prompts would bring Apache-2.0 §4 notice duties; borrowing ideas would not. Its rating prompts break our no-advice rule.

## 3. Comparable open-source finance agents

| Project | Licence | Approach | Relevance |
|---|---|---|---|
| TauricResearch/TradingAgents | Apache-2.0 | Analysts, then a bull/bear debate, then a trader, a risk debate and a portfolio manager. Data comes from yfinance, Alpha Vantage, SEC EDGAR, FRED, Reddit, StockTwits and Polymarket (`tradingagents/dataflows/vendors/`), with no TEFAS or KAP source | Pattern only |
| virattt/ai-hedge-fund | MIT (~63.9k stars) | Investor-persona agents plus valuation, sentiment, fundamentals and technicals agents, with risk and portfolio managers. Paper trading only, "for educational and research purposes only" | Low. Built on LangGraph [U] |
| AI4Finance-Foundation/FinRobot | Apache-2.0 (~8.2k stars) | Per its README: V0 on AutoGen, V1 on the OpenAI Agents SDK, V2 on PydanticAI. Valuation is computed by deterministic operators. Its stated principle: "models reason, software computes, agents orchestrate, and systems verify" [U, from a README summary] | The principle matches DEC-028; its price-target reports don't |

At README level, none of them targets funds, data published at NAV cadence, or insurance triggers.

## 4. Server-side PDF for the Turkish trigger specification

| | Typst (`typst`) | WeasyPrint | ReportLab | Playwright + Chromium |
|---|---|---|---|---|
| Licence | Apache-2.0 | BSD | BSD | Apache-2.0 |
| Version | 0.15.0 (2026-06-16); the repo's main branch shows 0.15.1 | 70.0 (2026-09-08) | 5.0.1 (2026-08-20) | 1.63.0 (2026-09-15), bundles Chromium 153 |
| Turkish text | Any bundled OTF/TTF font via `font_paths`; `lang: "tr"` | Pango/HarfBuzz shaping, `@font-face`, `lang="tr"` | Built-in fonts use WinAnsi encoding, which lacks ğ, ş, ı and İ, so a TTF must be registered [inferred] | Full support; the slim image needs fonts installed |
| Layout control | Strong: tables, page counters, headers | CSS Paged Media | Complete, but verbose code | Best modern CSS; weaker paged-media support [U] |
| Docker weight | One 34 MB wheel, no apt packages | apt `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0` plus fonts | Light | 48 MB wheel, plus the browser download and `--with-deps` system libraries (hundreds of MB [U]) |
| Determinism | `timestamp` (equivalent to SOURCE_DATE_EPOCH), `ignore_system_fonts`, `font_paths` | `pdf_identifier` and `dcterms.created`; output may vary with the system's Pango and fonts [U] | `invariant` option [U] | Weakest [U] |
| Effort [estimate] | 1.5–2.5 h | 1.5–2 h | 3 h or more | 2–3 h plus container work |

**Recommendation: Typst.**
- **Byte-identical output.** It needs no system packages. With a pinned font folder and a fixed timestamp it should produce the same bytes on Windows and in the Linux container, so the PDF's SHA-256 can go into the evidence record. A test that compiles twice and compares hashes would prove it.
- **Data, not markup.** Render from the machine-readable term sheet. Put the template and `data.json` in one temporary root and read the data with `json("data.json")`, so LLM text stays data and is never parsed as markup.
- **No network.** Use no `@preview` packages, because they download from the network.
- **Turkish.** Bundle an OFL font that covers Turkish. Write uppercase Turkish literally; whether `upper()` or `text-transform` handle i/İ correctly is unverified [U].
- **Labels on every page.** "Taslak — sigorta poliçesi değildir", plus the `HISTORICAL_REPLAY` and development-result labels.
- **Fallbacks.** Use WeasyPrint if Barış's HTML/CSS should be reused directly; restrict its `url_fetcher` to local files and turn on Jinja2 autoescape. As a last resort, a print stylesheet and the browser's "Save as PDF" need no server dependencies.

## 5. Debate and critic patterns: what the evidence says

These papers were checked through search-result abstracts and summaries, not full text.

| Source | Finding |
|---|---|
| Du et al., ICML 2024 | 3 agents debating for 2 rounds beat a single agent on reasoning and factuality. The comparison does not hold total compute equal |
| Huang et al., ICLR 2024 | At equal response counts, debate "significantly underperforms" self-consistency (majority voting over independent samples). Self-correction without external feedback is unreliable |
| Smit et al., ICML 2024 | Debate does not reliably beat self-consistency or ensembling, and is sensitive to hyperparameters |
| "Debate or Vote", NeurIPS 2025 | Majority voting accounts for most of debate's gains across seven benchmarks |
| Gou et al. (CRITIC), ICLR 2024 | Self-correction works when the critique comes from external tools |
| Cemri et al. (MAST), NeurIPS 2025 | 14 failure modes, mostly from system design, inter-agent misalignment and verification |
| Anthropic engineering, 2025-06-13 | Multi-agent systems use about 15× the tokens of a chat. They suit parallel, breadth-first research, not tightly coupled tasks |
| OpenAI's agent-building guide, 2025 | Get the most out of a single agent before adding more [from secondary summaries; the PDF was not parsed] |

**What this means for us:**
- **We already have an external critic.** The plan's validators check the schema, the cited IDs, the number placeholders, the wording and that numbers match.
- **Debate doesn't fit the budget.** It takes about 6–7 calls per decision instead of 1–2, so it multiplies decision cost roughly 3–6×. The plan's own estimate (about $19.5) already sits at the $20 cap.
- **Cheaper alternative:** take 3 independent samples (default sampling), and only for insurance trigger assessments.
  - If all three agree, that is the answer.
  - Otherwise the result is `UNDETERMINED` and the fund goes to the review queue.
  - Store every sample.
  - The agreement rate then becomes a measurable figure, labelled as a development result.

## 6. Collisions and corrections to raise with Mirza

1. **Plan §2 D6 (line 48):** the claim "nothing stored at OpenAI" is wrong.
   - OpenAI says abuse-monitoring logs "are generated for all API feature usage and retained for up to 30 days".
   - With `store: false`, `/v1/responses` keeps no application state ("None"), but that does not stop the abuse-monitoring logs.
   - Zero Data Retention requires OpenAI's approval.
   - Reword D6 and tell Safa, since it affects D7.
2. **Agents SDK tracing** would send prompts and outputs to OpenAI unless it is disabled.
3. **Framework rule:** adopting either framework runs into the handoff's recorded-need rule. Under DEC-028 that rule is a guide, but the collision should still be raised.
4. **No rating prompts:** don't reuse TradingAgents' rating prompts.

## Sources (all accessed 2026-10-10)

- **Agents SDK:**
  - https://pypi.org/project/openai-agents/
  - https://raw.githubusercontent.com/openai/openai-agents-python/main/pyproject.toml
  - https://openai.github.io/openai-agents-python/ and its pages `tracing/`, `guardrails/`, `human_in_the_loop/`, `running_agents/`, `agents/`, `ref/model_settings/` and `usage/`
- **OpenAI data handling:**
  - https://developers.openai.com/api/docs/guides/your-data
  - https://community.openai.com/t/how-to-use-reasoning-encrypted-content-with-store-false-stateless/1286934
- **LangChain and LangGraph:**
  - https://pypi.org/project/langgraph/
  - https://pypi.org/project/langchain-core/
  - https://pypi.org/project/langchain-openai/
  - https://raw.githubusercontent.com/langchain-ai/langgraph/main/libs/langgraph/pyproject.toml
  - https://raw.githubusercontent.com/langchain-ai/langchain/master/libs/core/pyproject.toml
  - https://raw.githubusercontent.com/langchain-ai/langchain/master/libs/partners/openai/pyproject.toml
  - https://docs.langchain.com/langsmith/trace-with-langgraph
- **Comparable projects:**
  - https://github.com/virattt/ai-hedge-fund
  - https://github.com/AI4Finance-Foundation/FinRobot
- **PDF tools:**
  - https://pypi.org/project/typst/
  - https://github.com/messense/typst-py (README, `python/typst/__init__.pyi`, `Cargo.toml`)
  - https://pypi.org/project/weasyprint/
  - https://doc.courtbouillon.org/weasyprint/stable/first_steps.html
  - https://doc.courtbouillon.org/weasyprint/stable/api_reference.html
  - https://pypi.org/project/reportlab/
  - https://pypi.org/project/playwright/
- **Debate and critic research:**
  - https://proceedings.mlr.press/v235/smit24a.html
  - https://arxiv.org/abs/2508.17536
  - https://arxiv.org/abs/2310.01798
  - https://icml.cc/virtual/2024/poster/32620
  - https://arxiv.org/abs/2305.11738
  - https://arxiv.org/abs/2503.13657
  - https://www.anthropic.com/engineering/multi-agent-research-system
  - https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/ (returned HTTP 403 on fetch)