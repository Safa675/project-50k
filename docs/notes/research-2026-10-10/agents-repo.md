# TradingAgents v0.6.0: deep read for Project 50K

**Method.** I read the clone statically (tag `v0.6.0`, commit `1394a3f`, 2026-10-03). Nothing was installed, imported or run, and that includes the tests. Paths are relative to the clone root (`C:\Users\mirza\AppData\Local\Temp\claude\c--Users-mirza-Desktop-Hackathon-project-50k\fcb59ff2-d20e-4984-b01d-14d47f0bf736\scratchpad\tradingagents`). Two upstream facts were checked in GitHub source on 2026-10-10; the URLs are in section 3. **[unverified]** marks estimates.

**Verdict**
- **Take the pattern, not the framework.** It is a LangGraph/LangChain app, and every decision it produces is investment advice. Its prompts and schemas cannot be used under DEC-028.
- **Copy** three small helpers that have no framework dependency: point-in-time date handling, vendor-error sentinels and secret scrubbing.
- **Adapt:**
  - parallel analysts;
  - arguments injected by the server;
  - a capped tool loop;
  - "absent, not empty" markers;
  - a non-tradeable sentinel for unreadable decisions.
- **Cost and egress.** A default run makes at least 15 LLM calls, typically about 20–25 [unverified]; the plan budgets about 8 per fund run. It also leaves OpenAI's `store` setting unset, so OpenAI retains the responses.

## 1. Architecture

| Agent (tier) | Reads | Produces |
|---|---|---|
| Market, News, Fundamentals analysts (quick) | own tool loop | free-text report + Markdown table |
| Sentiment analyst (quick) | Yahoo news, StockTwits, Reddit pre-fetched into the prompt; no tools | `SentimentReport`: band, 0–10 score, confidence, narrative |
| Bull / Bear researchers (quick) | all four reports, debate history | debate turns |
| Research Manager (deep) | debate history only | `ResearchPlan`: 5-tier recommendation, rationale, strategic actions |
| Trader (quick) | plan, market report, portfolio | `TraderProposal`: Buy/Hold/Sell, entry, stop, sizing |
| Aggressive / Conservative / Neutral (quick) | trader plan, all four reports, history | risk-debate turns |
| Portfolio Manager (deep) | plan, trader plan, risk history, memory lessons | `PortfolioDecision`: rating, summary, thesis, price target, horizon |

**Flow** (`tradingagents/graph/setup.py`, `conditional_logic.py`):
1. The graph starts by running the selected analysts and a Memory Log node at the same time. `tests/test_graph_end_to_end.py` asserts that more than one thread is used.
2. Each analyst is its own subgraph with a private message history, and it returns only its report.
3. When all analysts finish, Bull and Bear alternate until `count >= 2 × max_debate_rounds` (default 1, so 2 turns). The Research Manager then decides.
4. Next come the Trader, then Aggressive, Conservative and Neutral in turn until `count >= 3 × max_risk_discuss_rounds` (3 turns), then the Portfolio Manager, then the end.

Routing between steps uses counters, not LLM choices.

**State** (`agents/state.py`). `AgentState(MessagesState)` holds:
- the ticker, asset type, trade date and a deterministic identity string;
- four report strings;
- two debate dicts (histories as concatenated strings, plus counters);
- the plans, `final_trade_decision`, `final_rating`, `past_context`, `memory_note` and `portfolio_context`.

**Memory and reflection** (`memory/log.py`, `settlement.py`, `reflection.py`):
- Each decision is stored as pending in an append-only, file-locked Markdown log in `~/.tradingagents/`.
- Later runs settle entries that have come due. Yahoo closes over 5 trading days give the raw return and the alpha against a regional benchmark. The quick model then writes a 2–4 sentence reflection.
- Only the Portfolio Manager reads these lessons: 5 for the same ticker and 3 from other tickers. A run dated in the past sees only outcomes known by its date.
- Optional SQLite checkpoints are keyed on a hash of the config (`graph/checkpointer.py`).

## 2. Data layer

| Analyst | Tools (`agents/tools.py`) | Default vendors |
|---|---|---|
| Market | `get_stock_data`, `get_indicators`, `get_verified_market_snapshot` | yfinance + stockstats (Alpha Vantage optional) |
| News | `get_news`, `get_global_news`, `get_macro_indicators`, `get_prediction_markets` | Yahoo news/search (5 fixed US/global queries), FRED (key), Polymarket |
| Fundamentals | profile, balance sheet, cash flow, income, insider trades | SEC EDGAR (US filers), then yfinance |
| Sentiment | none | Yahoo, StockTwits API, Reddit RSS; optional TypeSafe "Jev" post classifier |

- **Binding.** Tools are bound with `llm.bind_tools(TOOLS)` in `agents/analysts/turn.py` and run by LangGraph's `ToolNode`.
  - The ticker and trade date are `InjectedState`, so the model never sees them as arguments.
  - Any date the model supplies is clamped to the trade date (`dataflows/date_window.py`).
- **Routing** (`dataflows/router.py`). Only the configured vendor chain is used; nothing falls back silently to another vendor. Typed errors (`dataflows/errors.py`) become text such as `DATA_UNAVAILABLE … do not estimate or fabricate values`.
- **How data reaches prompts.**
  - Tool output arrives as text (OHLCV CSV, indicator lists).
  - Reports are pasted verbatim into later f-string prompts.
  - Retrieved posts and news sit between tags like `<start_of_reddit>`, with no framing that tells the model to treat them as data rather than instructions.
- **Coverage.** Stocks and crypto only. There is no support for Borsa Istanbul, TEFAS, KAP, SPK or funds. A `.IS` ticker would be benchmarked against SPY, because `benchmark_map` has no `.IS` entry.

## 3. LLM layer

- **Providers** (`llm_clients/factory.py`, `openai_client.py`):
  - OpenAI, Anthropic, Google, Azure and Bedrock.
  - A registry of OpenAI-compatible providers: xAI, DeepSeek, Qwen, GLM, MiniMax, OpenRouter, Mistral, Kimi, Groq, NVIDIA, Ollama and a generic endpoint.
  - The quick and deep tiers may use different providers. Any model ID is accepted, with a warning.
- **OpenAI uses the Responses API.**
  - `ChatOpenAI(use_responses_api=True)` is used when `base_url` is unset or points at `*.openai.com` (`openai_client.py` lines 213 and 320–321). Custom endpoints and the other providers use Chat Completions.
  - The tests for this (`tests/test_openai_responses_base_url.py`) sit in classes that pytest's default rules do not collect, so they never run.
- **`store` is never set** (checked by grep).
  - The OpenAI SDK says it "Defaults to true when omitted… stored for at least 30 days" (https://raw.githubusercontent.com/openai/openai-python/main/src/openai/types/responses/response_create_params.py, accessed 2026-10-10).
  - langchain-openai sends nothing when it is unset (https://raw.githubusercontent.com/langchain-ai/langchain/master/libs/partners/openai/langchain_openai/chat_models/base.py, accessed 2026-10-10).
- **Structured output.** The Sentiment, Research Manager, Trader and Portfolio Manager agents use `with_structured_output`.
  - The method is `function_calling`, a forced tool call (`llm_clients/capabilities.py`), not `json_schema`. No `strict` flag is passed anywhere.
  - If the structured call fails, one free-text call follows. The Portfolio Manager's rating is then read with a regex, and an unreadable rating becomes `REVIEW` (`agents/rating.py`).
  - The docstring in `agents/schemas.py` that claims json_schema is out of date.
- **Calls per run with defaults (from the code):**
  - The total is: for each of the 3 tool analysts, its tool rounds plus 1; plus 1 for sentiment; plus 2D for the research debate; plus 1 each for the Research Manager and Trader; plus 3R for the risk debate; plus 1 for the Portfolio Manager. D and R are the research and risk debate rounds, both 1 by default.
  - Add 1 reflection per past decision that has come due, and up to 4 free-text fallbacks.
  - **Minimum: 15.** This matches the arithmetic of the scripted checkpoint test.
  - **Typical: about 20–25 [unverified].** The market analyst's prompt asks for prices, then indicators, then the snapshot, then the report.
  - **Ceiling: about 76** with `max_tool_rounds=20`, plus reflections.
  - Two calls use the deep model, `gpt-6-sol`; the rest use `gpt-6-luna`.
  - Five calls carry all four full reports [token volume unverified].
- **Knobs** (`default_config.py`, `TRADINGAGENTS_*` environment variables):
  - per-tier provider, model and URL;
  - debate rounds, risk rounds, `max_tool_rounds` and the recursion limit;
  - temperature, `max_tokens`, retries and reasoning effort;
  - output language and which analysts run;
  - vendor per category or per tool, and news limits;
  - holding period, benchmarks and checkpointing.
- **Online/offline.** There is no offline mode. Runs dated in the past withhold undated data, but news and social feeds are always live. Only the tests run offline.

## 4. Output

- **Decision.** `propagate()` returns `(state, rating)`. The rating is Buy, Overweight, Hold, Underweight or Sell, or `REVIEW` when it cannot be read.
  - The decision Markdown has Rating, Executive Summary ("the call and how to act on it"), Investment Thesis, Price Target and Time Horizon.
  - The Trader adds Buy/Hold/Sell, an entry price, a stop-loss and position sizing.
- **Files** (`reporting.py`):
  - one `.md` per agent in `1_analysts`…`5_portfolio`;
  - `complete_report.md` and `complete_report.html`;
  - a state JSON;
  - the memory log.
- **HTML** (`report_html.py`). The page is self-contained:
  - CSP `default-src 'none'`;
  - raw HTML and images disabled;
  - print CSS;
  - the Tauric logo.
- **No PDF or other document generation exists.** Printing from a browser is the only route.

## 5. Engineering quality

- **Tests.** 84 files and 907 `def test_` functions (counted, **not run**).
  - A fixture that applies to every test blocks network access.
  - A scripted fake model drives the whole graph offline. It covers wiring, parallelism, resume, the tool cap and settlement.
  - CI runs Python 3.11–3.14, one run outside UTC, a clean-install smoke test and strict ruff.
- **Typing.** Pydantic schemas, TypedDict state and type annotations. There is no mypy or pyright, and LLM objects are typed `Any`.
- **Error handling.**
  - Vendor errors are typed, and tools return sentinel text instead of raising.
  - LLM failures fail *open* to free text, with broad `except Exception`.
  - A failed settlement does not stop the run.
- **Dependencies** (`pyproject.toml`). Versions have lower bounds only, and there is no lockfile (`uv.lock` was removed in 0.3.0).
  - Agent stack: `langgraph>=1.2.12`, `langgraph-checkpoint-sqlite>=3.1.1`, `langchain-core>=1.6.5`, `langchain-openai>=1.6.6`.
  - Required even for OpenAI-only use: `langchain-anthropic` and `langchain-google-genai`.
  - Data and CLI: `pandas>=3.0.6`, `yfinance>=1.7.0`, stockstats, typer/rich/questionary.
- **Docker.**
  - The image is the interactive CLI, built in multiple stages on `python:3.13-slim`, running as a non-root user with a data volume.
  - There is no server or healthcheck, and image tags are not pinned (`ollama:latest`).
  - `.dockerignore` does not exclude `.env.enterprise`, which holds Azure keys. Because the build runs `COPY . .`, a local copy would end up inside the image. I read this from the files; I did not build the image.
- **Side effects.**
  - `import tradingagents` loads `.env` from the working directory.
  - The CLI fetches `api.tauric.ai/v1/announcements` at startup.

## 6. License obligations (Apache-2.0)

- The standard `LICENSE` is present. There is **no NOTICE file**, no copyright header in any source file and no project copyright line.
- To copy code:
  - (§4a) ship the license text, e.g. `third_party/tradingagents/LICENSE`;
  - (§4b) mark each copied file as modified, e.g. "Adapted from TauricResearch/TradingAgents v0.6.0 (1394a3f), Apache-2.0; modified by Project 50K, <date>";
  - (§4c) keep any notices that are present (there are none today);
  - (§4d) carry a NOTICE file if a later version adds one.
- **Trademarks (§6).** The license grants no right to the "Tauric Research" or "TradingAgents" branding. Strip the logo and footer if we adapt `report_html.py`.
- **Permissive.** Our own code keeps its own license. Reusing only the structure creates no obligation, but crediting the project and citing arXiv 2412.20138 is good practice.

## 7. Fit for Project 50K

**Copy (with §4 notices):**
- `dataflows/date_window.py`: `as_of`, `as_of_window`, `in_window` and `coverage_gap`. They enforce date cutoffs and treat "unavailable" as different from "absent".
- `dataflows/errors.py` and the sentinel functions in `router.py`.
- `get_scrubbed` from `dataflows/net.py`, which strips keys from HTTP errors.

**Adapt (rewrite in our worker on the OpenAI SDK):**
- **Parallel analysts.** Each works on a private history, and the next step waits for all of them. Ours would read slices of the evidence packet with no tools, as their sentiment analyst does.
- **Server-injected fund and date.** The model never chooses them.
- **Tool-round cap.** After the cap, a forced final turn with no tools (`turn.py`); usable for the chat limits.
- **Missing-input markers for the challenger.** `report_or_absent` and `opponent_argument_or_opening` (`agents/context.py`).
- **Run signature and settings allowlist.** The config-digest signature becomes our cache key, and `run_settings()` our decision provenance.
- **TASLAK base.** Their self-contained, printable HTML, with our own PDF renderer added.

**Pattern only.** Their shape is: a bull/bear pair, a judge, a three-way risk critique, then a final judge. It maps to analysts → challenger → committee (about 6–8 calls), as section 7 of the build plan proposes.

**Conflicts**

| Area | TradingAgents | Our rule |
|---|---|---|
| Advice | Buy…Sell, entry/stop, price target, sizing, portfolio-aware | No buy/hold/sell or personalized advice |
| Numbers | LLM writes prices; sentiment LLM assigns score and confidence | Detectors compute every score; placeholders only |
| Decisions | Any rating; no allowed options, citations, prompt version or override | Server-computed options, cited IDs, validator, append-only override |
| Untrusted text | Posts and news spliced into prompts without framing | Retrieved content is data |
| Egress | Raw OHLCV, news text, full reports | D7: derived evidence only |
| OpenAI storage | Default (stored ≥30 days) | D6: `store: false` |
| Data/tools | US/global vendors; live web, news, social | TEFAS/KAP/SPK; fixed-SQL read-only tools |
| Persistence | Markdown/SQLite under `~/` | PostgreSQL, append-only |
| Learning | Reflection on realized alpha | Development results; no outcome-tuned rules |
| Cost | ≥15 (~20–25) calls per ticker, plus reflections | ~8 per fund run; $20 cap |
| Framework | LangGraph/LangChain hard dependency | Handoff "no multi-agent framework" guide |

**Framework guide.** Using TradingAgents itself would need a recorded exception to the handoff's "no multi-agent framework" guide. This study finds no need for one:
- the graph is a fixed fan-out and join plus two counter loops;
- our PostgreSQL queue already gives durability;
- their structured-output path is not strict.

**Failure modes to design out** (from their CHANGELOG):
- an unreadable decision became Hold (#1170);
- the first debater invented the opponent's case (#1176);
- a rating quoted in the text replaced the decision (#1383, #1466);
- translated labels broke parsing (#1435);
- tool loops ran without limit (#1420);
- percentages appeared in price fields (#1288);
- structured calls reached for a search tool (#1130);
- memory leaked future outcomes into past-dated runs (#1251).

**Model IDs.** The repo's third-party catalog lists `gpt-6-sol`, `gpt-6-luna`, `gpt-6-astra` and `gpt-5.6*`. It does not list the plan's `gpt-6.1-sol` or `gpt-5.4-nano`, so keep the T3.1 smoke test.

**Unverified:**
- the typical call count and token use;
- whether the tests pass;
- the `.env.enterprise` leak into the image (not built);
- whether the catalog's model IDs exist at OpenAI.