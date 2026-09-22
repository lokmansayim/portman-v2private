# Agent frameworks & hosted-agent products for a WhatsApp dealer assistant: token economics and operational fit (as of 2026-09-21)

Scope note: all prices below were read on 2026-09-21 unless a different "as of" date is given. Currency is USD unless marked. Prices from official vendor pages are labelled (official); prices from third-party trackers are labelled (secondary) and should be re-checked before being put in front of the owner. The company's own observation (gpt-6-astra/medium in an OpenAI Agents-API hosted environment, ~200k input tokens per run of which ~157k cached, 1 turn, 6 tool calls, ~90 s overhead) is treated as a given input, not a sourced fact.

---

## Key Question 1: Why do hosted agent / computer-use style loops burn 200–300k tokens per run, while a structured-extraction call uses ~3k?

### Takeaway
A hosted agent run is not one model call; it is a loop of N model requests (roughly one per tool call plus one final), and every request re-sends the whole rendered context: harness instructions, developer prompt, tool/MCP schemas, skills, file listings and every previous tool output. Tokens therefore grow roughly quadratically with the number of steps; prompt caching cuts the price of the repeated prefix to ~10% but does not reduce the token count. A structured-extraction pipeline makes exactly one small call per user message (system prompt + message → JSON) and lets code decide the next step, so it stays at ~3k tokens.

### Cited Findings
- OpenAI's Agents API (public beta) runs the agent inside a sandboxed *environment* where it can "execute code, edit files, connect to MCP servers, and produce artifacts"; a *session* holds "the agent, instructions, tools, and MCP servers available" plus the execution environment; the managed *Codex harness* handles "running commands and code in a sandbox, applying relevant skills and instructions, connecting to external data through tools or MCP, steering the agent while it works, summarizing previous work to manage its context window, breaking work into subtasks and delegating to subagents." Billing: "Model usage is billed at the selected model's API rates" and "OpenAI-hosted sandboxes use standard container rates." The doc showcases `gpt-6-astra` as the model. Limits: US-only data residency, no Zero Data Retention, beta access — [OpenAI Agents API overview (official)](https://developers.openai.com/api/docs/guides/agents-api/overview)
- The Agents API entered public beta on September 10, 2026; the harness does "automatic context compaction"; advice: "Long-running agents can generate many model turns and tool calls, so per-session budgeting should be based on complete task traces instead of the price of a single request." This article claims "no additional fee beyond the models and tools consumed" — but the official overview says hosted sandboxes bill at container rates (see conflict note below) — [AiCybr, 2026-09-11](https://aicybr.com/blog/openai-agents-api-codex-harness-hosted-sandboxes)
- In agent runs "tool outputs pile back into the context, so by turn ten you're paying for a much larger prompt on every call." Developer quote: "Each response bloats context. By turn 10, you're paying for 100k+ tokens on every LLM call." Responses API and Agents SDK have no separate platform fee ("included with standard API model pricing") — [eesel AI, 2026-09-11](https://www.eesel.ai/blog/openai-agents-api-pricing)
- Mechanism and arithmetic of context accumulation: frameworks "carry forward the information a model needs for the next step: the original request, prior responses, tool definitions, file contents, test results." "If every step adds 1,000 new tokens, a 20-step workflow doesn't use 20,000 input tokens… cumulative input is 210,000 tokens." A cited 2026 study measured ~4.17M tokens per agentic coding task vs 1,190 for a single reasoning call; an audit found "62% of agent bills stemmed from re-sent context alone"; input:output ratio ~154:1 for agentic tasks; token use varied up to 30× across runs of the same task. Mitigations: prompt caching (static content to ~10% of input price), session boundaries between phases, context pruning, model routing — [Larridin, 2026-08-14](https://larridin.com/blog/ai-agent-context-accumulation-cost)
- OpenAI caches "the model's full rendered context including OpenAI-provided instructions, developer messages, tool definitions, and conversation history containing text, images, documents, and supported audio" — i.e., these are all sent (and counted) on every request; caching only changes the price — [OpenAI prompt caching guide (official)](https://developers.openai.com/api/docs/guides/prompt-caching)
- Anthropic's own toolset definitions illustrate fixed per-request overhead: computer use adds "~4,500 input tokens" and browser use "~6,600 input tokens" of tool definitions to every request — [Anthropic pricing page (official)](https://platform.claude.com/docs/en/about-claude/pricing)
- Anthropic (Dec 19, 2024) distinguishes *workflows* (predefined code paths) from *agents* (LLM directs its own process); agentic systems "often trade latency and cost for better task performance"; recommendation: "find the simplest solution possible, and only increasing complexity when needed" — [Anthropic, Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- 12-Factor Agents (Dex Horthy / HumanLayer): "most of the products out there billing themselves as 'AI Agents' are not all that agentic. A lot of them are mostly deterministic code, with LLM steps sprinkled in"; the standard "loop until done" pattern "doesn't work as well as we want it to"; Factor 4 "Tools are just structured outputs", Factor 8 "Own your control flow", Factor 10 "Small, focused agents", Factor 12 "Make your agent a stateless reducer" — [humanlayer/12-factor-agents (GitHub)](https://github.com/humanlayer/12-factor-agents)
- Hosted-sandbox unknowns flagged by a cost tracker: it is not documented which container tier an Agents-API session bills at, nor "whether the up-to-one-hour idle period before deletion is billed" — [TokenCost, 2026-09-13](https://tokencost.app/blog/openai-agents-api-hosted-sandbox-pricing)

### Inferences
- Reconstructing the company's run: 1 "turn" with 6 tool calls means roughly 7 sequential model requests (one per tool result, plus the final answer). 157k cached ÷ 7 ≈ 22.4k tokens — consistent with a ~22k-token static prefix (harness instructions + developer prompt + tool/MCP schemas + skills + environment file listing) re-sent on every request. The ~43k uncached tokens are the growing tail (each new tool output, reasoning summaries, the user task). Total ≈ 200k. This is exactly the quadratic pattern described by Larridin and eesel, not a bug.
- Choosing `medium` reasoning effort on gpt-6-astra adds hidden reasoning tokens that are billed at the $50/M output rate (o-series/reasoning models "bill internal reasoning tokens at output rates" per CloudZero, see KQ2); output tokens were not in the company's numbers, so the true per-run cost is above the input-only estimate in KQ3.
- The ~90 s overhead is consistent with sandbox boot + 7 sequential round-trips of a large reasoning model, but I found no official statement of Agents-API sandbox start-up latency (Gap).
- The 3k pipeline is small because it has no loop: one request = ~2.5k system prompt (cached) + ~0.5k conversation/message, ~200–300 output tokens of JSON; state lives in the company's database, not in the model context; there are no tool schemas or file listings to re-send.
- Caching would not have saved the company: at $1/M cached vs $10/M uncached the 157k cached tokens cost $0.157 instead of $1.57, but the 43k uncached tokens ($0.43) and output still dominate; the only real fix is fewer, smaller requests.

### Gaps
- No official OpenAI page documents the exact composition of the Codex-harness prompt (how many tokens the harness instructions, skills and file listing occupy). The 22k-per-request figure above is an inference from the company's own numbers.
- No official figure for hosted-sandbox cold-start latency; the "~90 s" is the company's observation only.
- I could not find a 2025–2026 practitioner post reporting per-run costs specifically for the OpenAI Agents API (it has been public only since 2026-09-10); reported numbers are for agent loops in general (Larridin, eesel).

---

## Key Question 2: Current price lists (OpenAI, Anthropic, Google), prompt-caching rules, and hosted-runtime fees

### Takeaway
As of 2026-09-21 the models span ~250× in input price (Gemini 2.5 Flash-Lite $0.10/M to GPT-6 Astra $10/M with GPT-5.5 Pro at $30/M). All three vendors now price cached input at ~10% of base input (Anthropic 2.5% on its newest tier), with cache writes at 1.25× on Anthropic and on OpenAI GPT-5.6+. Hosted runtimes add a small but separate meter: OpenAI containers $0.03–$1.92 per 20-minute session by RAM size; Claude Managed Agents $0.08 per active session-hour.

### Cited Findings

**OpenAI model prices (official pricing page, read 2026-09-21; per 1M tokens; "short context" ≤ ~272k tokens)**

| Model | Input | Cached input | Output | Notes |
|---|---|---|---|---|
| GPT-6 Astra | $10.00 | $1.00 | $50.00 | long-context: $20 / $2 / $75 |
| GPT-5.6 Sol | $4.00 | $0.40 | $20.00 | "promotional pricing… at least through November 21, 2026"; long: $8 / $0.80 / $30 |
| GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | long: $4 / $0.40 / $18 |
| GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | long: $0.40 / $0.04 / $1.80 |
| chat-latest | $5.00 | $0.50 | $30.00 | |
| gpt-5.3-codex | $1.75 | $0.175 | $14.00 | |

Tools: web search "$10.00 / 1k calls", file search "$2.50 / 1k calls", Code Interpreter "$0.03–$1.92 per 20-minute session" (tiered by GB). "Cached input rates are uniformly 10% of standard input rates across models." — [OpenAI pricing (official)](https://developers.openai.com/api/docs/pricing)

- Secondary tracker (CloudZero, published 2026-07-10, updated 2026-09-04) lists GPT-5.6 Sol at $5.00 / $0.50 / $30.00 (list price, i.e., without the promo), GPT-5.5 Pro $30 / $180, GPT-5.5 $5 / $30, GPT-5.4 $2.50 / $15, GPT-5.4 Mini $0.75 / $4.50, GPT-5.4 Nano $0.20 / $1.25; long-context threshold "past ~272K tokens": "Input doubles and output rises 50% on the long meter, and cached input doubles with it"; o4-mini $1.10/$4.40, o3 $2/$8; "o-series models bill internal reasoning tokens at output rates, so effective costs run 3x to 10x the base rate depending on task complexity"; Batch API halves rates; "Cache writes: Bill at 1.25x input rate"; "Regional processing uplift: 10% on eligible models released after March 5, 2026". GPT-4.1, GPT-4.1-mini/nano and GPT-4o-mini "do not appear in the pricing tables" — [CloudZero (secondary)](https://www.cloudzero.com/blog/openai-pricing/)
- GPT-5.4 Mini ($0.75 in / $4.50 out, 400K context) and GPT-5.4 Nano ($0.20 / $1.25, 128K context) released 2026-03-18; the same article's comparison tables show GPT-5 mini at $0.25/$2.00 and GPT-4.1 nano at $0.10/$0.40 but give no deprecation status — [AI Cost Check, 2026-03-18 (secondary)](https://aicostcheck.com/blog/gpt-5-4-mini-nano-pricing-benchmarks)
- OpenAI prompt caching rules: prefix-based KV reuse; "For GPT-5.6+, this is 1,024 visible input tokens" minimum; cached input "0.1× the standard uncached rate on GPT-5.6+"; "GPT-5.6 cache writes cost 1.25× uncached rates (earlier models have no additional charge)"; cache lifetime "GPT-5.6+: 30 minutes minimum after last write or reuse", earlier models "5 to 10 minutes of inactivity, up to one hour"; best practice "Place stable developer instructions and shared reference material first"; applies automatically, with explicit breakpoints available on GPT-5.6+; on pre-5.6 models `cached_tokens` is rounded down to a multiple of 128 — [OpenAI prompt caching guide (official)](https://developers.openai.com/api/docs/guides/prompt-caching)
- OpenAI hosted sandbox/container rates per 20-minute session: 1 GB $0.03 ($0.09/h), 4 GB $0.12 ($0.36/h), 16 GB $0.48 ($1.44/h), 64 GB $1.92 ($5.76/h); "OpenAI-hosted sandboxes use standard container rates… the row… Code Interpreter and the shell tool have billed against all year"; worked example: on the cheapest model plus a 1 GB sandbox, a one-hour Luna session totals $0.118 and "sandbox represents 76.3% of total cost" — [TokenCost, 2026-09-13 (secondary, quoting the official pricing row)](https://tokencost.app/blog/openai-agents-api-hosted-sandbox-pricing)

**Anthropic prices (official, read 2026-09-21; per 1M tokens)**

| Model | Input | Output | Cache write 5m | Cache write 1h | Cache read |
|---|---|---|---|---|---|
| Claude Opus 5 / 4.8 / 4.7 / 4.6 / 4.5 | $5 | $25 | $6.25 | $10 | $0.50 |
| Claude Sonnet 5 | $2 | $10 | $2.50 | $4 | $0.20 |
| Claude Sonnet 4.6 / 4.5 | $3 | $15 | $3.75 | $6 | $0.30 |
| Claude Haiku 4.5 | $1 | $5 | $1.25 | $2 | $0.10 |
| Claude Fable 5.1 / Mythos 5.1 | $10 | $50 | $12.50 | $20 | $0.25 (2.5%) |

Multipliers: 5-minute cache write 1.25× input, 1-hour write 2×, cache read 0.1× (0.025× on Fable/Mythos 5.1); "Cache pays off after 1 read for 5m duration; after 2 reads for 1h duration." Batch API 50% off input and output (Haiku 4.5 batch $0.50/$2.50). Web search $10 per 1,000 searches; web fetch free beyond tokens. Sonnet 5's $2/$10 "introductory" price "is now permanent" (the scheduled rise to $3/$15 "will not occur") — [Anthropic pricing (official)](https://platform.claude.com/docs/en/about-claude/pricing)

- Claude Managed Agents: "Pre-built, configurable agent harness that runs in managed infrastructure. Best for long-running tasks and asynchronous work"; tools: bash, file operations, web search/fetch, MCP; "in beta… require the `managed-agents-2026-04-01` beta header"; "not currently eligible for Zero Data Retention or HIPAA" — [Anthropic Managed Agents overview (official)](https://platform.claude.com/docs/en/managed-agents/overview)
- Managed Agents runtime fee: "$0.08 per active session-hour", "Idle time is free"; tokens "billed at the same per-model rate as the standard Claude API"; "Batch API discounts don't apply"; example: one-hour Opus 5 session with 50k input / 15k output = $0.25 + $0.375 + $0.08 = $0.705 — [TrueFoundry, 2026-09-14 (secondary)](https://www.truefoundry.com/blog/claude-managed-agents-pricing); same $0.08/session-hour and same example cited by [TokenCost](https://tokencost.app/blog/openai-agents-api-hosted-sandbox-pricing). Note: a search result titled "Claude Managed Agents Pricing: $0.25/Session-Hour" ([Tygart Media](https://tygartmedia.com/claude-managed-agents-pricing-cost-analysis/)) conflicts; I could not open Anthropic's own Managed Agents pricing page (404), so treat $0.08 as the better-corroborated figure but unverified against the primary source.

**Google Gemini prices (secondary; official ai.google.dev page could not be fetched — see Gaps)**

| Model | Input | Output | Cached input |
|---|---|---|---|
| Gemini 3.6 Flash | $1.50 | $7.50 | $0.15 |
| Gemini 3.5 Flash | $1.50 | $9.00 | $0.15 |
| Gemini 3.5 Flash-Lite | $0.30 | $2.50 | $0.03 |
| Gemini 3.1 Pro | $2.00 | $12.00 | $0.20 |
| Gemini 3.1 Flash-Lite | $0.25 | $1.50 | $0.025 |
| Gemini 3 Flash | $0.50 | $3.00 | $0.05 |
| Gemini 2.5 Flash | $0.30 | $2.50 | $0.03 |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | $0.01 |

Data dated 2026-09-18; "context-cache storage and grounding charges are separate"; free tier is "rate-limited… enough for prototyping but not production traffic" — [BenchLM Gemini pricing (secondary)](https://benchlm.ai/google/api-pricing)

### Inferences
- For a text-only WhatsApp dealer assistant, the flagship tier (GPT-6 Astra $10/$50, Fable/Mythos 5.1 $10/$50) is 50× the input price of GPT-5.6 Luna and 10× Haiku 4.5; the company's hosted-agent experiment used the single most expensive standard OpenAI model on the list.
- Because cached-input pricing is now 10% everywhere, a stable 2.5k-token system prompt placed first in the request is nearly free after the first call; on OpenAI GPT-5.6+ the cache lives ≥30 minutes, on Anthropic 5 minutes (or 1 hour at 2× write price), so with 200 conversations/month (≈7/day) the Anthropic 5-minute cache will usually be re-written per conversation, the OpenAI cache may persist across conversations during busy hours.

### Gaps
- Google's official pricing page (ai.google.dev) was blocked by a fetch-permission prompt; Gemini prices above are from a tracker dated 2026-09-18 and should be verified on ai.google.dev before use.
- The current official OpenAI page did not list gpt-4o-mini, gpt-4.1-mini/nano, gpt-5-mini/nano or GPT-5.4 Mini/Nano in the fetched extract; whether they are still sold, and their cached-input prices, is uncertain (CloudZero says the 4.x minis "do not appear"; AI Cost Check lists GPT-5 mini $0.25/$2.00 and GPT-4.1 nano $0.10/$0.40 as of 2026-03-18). Cached prices for GPT-5.4 Mini/Nano were estimated at 10% in KQ3 and flagged.
- Whether GPT-6 Astra is subject to the 1.25× cache-write charge is implied by "GPT-5.6+" wording but not stated explicitly.

---

## Key Question 3: Concrete cost model — 6-message dealer conversation, 200 conversations/month

### Takeaway
With a cached 2.5k system prompt, a 6-message conversation costs between $0.0015 (Gemini 2.5 Flash-Lite) and $0.16 (GPT-6 Astra); 200 conversations/month is $0.30–$33/month depending on model, i.e., a rounding error next to a €5.49 VPS. By contrast, the company's hosted-agent run (~200k input on gpt-6-astra) costs roughly $0.62–0.87 per run → $130–175/month for 200 runs, about 28–35× more than a 3k pipeline on the same model and ~1,000× more than on a small model.

### Cited Findings (assumptions + arithmetic; prices from KQ2 sources)

Assumptions per conversation: 6 model calls; each call = 3,500 input tokens (2,500 cached system prompt + 1,000 uncached history/message) + 200 output tokens. Cache behaviour: 1 cache write per conversation (first call) + 5 cache reads. Monthly volume 200 conversations.

| Quantity | Per conversation | Per month (×200) |
|---|---|---|
| Cache-write tokens (system prompt, call 1) | 2,500 | 0.5M |
| Cache-read tokens (calls 2–6) | 12,500 | 2.5M |
| Uncached dynamic input | 6,000 | 1.2M |
| Output | 1,200 | 0.24M |
| Total input (no-cache case) | 21,000 | 4.2M |

Formula (prices per 1M): cost/month = 0.5·W + 2.5·R + 1.2·I + 0.24·O (cached) ; = 4.2·I + 0.24·O (no cache).

| Model (price source) | I / R / O / W ($ per 1M) | No-cache $/mo | With cache $/mo | $ per conversation (cached) |
|---|---|---|---|---|
| GPT-6 Astra (official) | 10 / 1 / 50 / 12.50 | 54.00 | 32.75 | 0.164 |
| GPT-5.6 Sol, promo to 2026-11-21 (official) | 4 / 0.40 / 20 / 5 | 21.60 | 13.10 | 0.066 |
| GPT-5.6 Sol, list (CloudZero) | 5 / 0.50 / 30 / 6.25 | 28.20 | 17.57 | 0.088 |
| GPT-5.6 Terra (official) | 2 / 0.20 / 12 / 2.50 | 11.28 | 7.03 | 0.035 |
| GPT-5.6 Luna (official) | 0.20 / 0.02 / 1.20 / 0.25 | 1.13 | 0.70 | 0.0035 |
| GPT-5.4 Mini (AI Cost Check; cached est. 10%, no write surcharge) | 0.75 / 0.075 / 4.50 / 0.75 | 4.23 | 2.54 | 0.013 |
| GPT-5.4 Nano (AI Cost Check; cached est. 10%) | 0.20 / 0.02 / 1.25 / 0.20 | 1.14 | 0.69 | 0.0034 |
| Claude Sonnet 4.5 (official) | 3 / 0.30 / 15 / 3.75 | 16.20 | 9.82 | 0.049 |
| Claude Sonnet 5 (official) | 2 / 0.20 / 10 / 2.50 | 10.80 | 6.55 | 0.033 |
| Claude Haiku 4.5 (official) | 1 / 0.10 / 5 / 1.25 | 5.40 | 3.28 | 0.016 |
| Gemini 3.5 Flash (BenchLM; W = I assumed) | 1.50 / 0.15 / 9 / 1.50 | 8.46 | 5.08 | 0.025 |
| Gemini 3 Flash (BenchLM) | 0.50 / 0.05 / 3 / 0.50 | 2.82 | 1.69 | 0.0085 |
| Gemini 3.5 Flash-Lite (BenchLM) | 0.30 / 0.03 / 2.50 / 0.30 | 1.86 | 1.19 | 0.0059 |
| Gemini 3.1 Flash-Lite (BenchLM) | 0.25 / 0.025 / 1.50 / 0.25 | 1.41 | 0.85 | 0.0042 |
| Gemini 2.5 Flash-Lite (BenchLM) | 0.10 / 0.01 / 0.40 / 0.10 | 0.52 | 0.29 | 0.0015 |

Worked example (GPT-6 Astra, cached): 0.5M × $12.50 = $6.25 (writes) + 2.5M × $1.00 = $2.50 (reads) + 1.2M × $10 = $12.00 (dynamic input) + 0.24M × $50 = $12.00 (output) = $32.75/month. Haiku 4.5: $0.625 + $0.25 + $1.20 + $1.20 = $3.28/month.

**The company's hosted-agent run, same price list** (200k input, 157k cached, 43k uncached, gpt-6-astra; output not reported):
- Input: 43,000 × $10/M = $0.430 + 157,000 × $1/M = $0.157 → $0.587 per run
- Output (unknown; reasoning tokens bill as output): 1k → $0.05; 3k → $0.15; 5k → $0.25
- Sandbox: 1 GB container $0.03 per 20-min session (TokenCost / OpenAI pricing row); larger tiers up to $1.92
- Total ≈ $0.67 (1k out) to $0.87 (5k out) per run → **$133–173 per 200 runs/month**; a 300k-token run with the same 78.5% cached share costs ≈ $0.88 input alone.

**3k-token structured-extraction call** (2,500 cached + 500 uncached input, 300 output), per call → per 200 calls:
- GPT-6 Astra: $0.005 + $0.0025 + $0.015 = $0.0225 → $4.50
- Claude Haiku 4.5: $0.0005 + $0.00025 + $0.0015 = $0.00225 → $0.45
- Gemini 3.1 Flash-Lite: $0.000125 + $0.0000625 + $0.00045 = $0.00064 → $0.13
- GPT-5.6 Luna: $0.0001 + $0.00005 + $0.00036 = $0.00051 → $0.10

Price sources: [OpenAI pricing (official)](https://developers.openai.com/api/docs/pricing); [OpenAI caching rules (official)](https://developers.openai.com/api/docs/guides/prompt-caching); [Anthropic pricing (official)](https://platform.claude.com/docs/en/about-claude/pricing); [CloudZero (secondary)](https://www.cloudzero.com/blog/openai-pricing/); [AI Cost Check (secondary)](https://aicostcheck.com/blog/gpt-5-4-mini-nano-pricing-benchmarks); [BenchLM Gemini (secondary)](https://benchlm.ai/google/api-pricing); [TokenCost container rates (secondary)](https://tokencost.app/blog/openai-agents-api-hosted-sandbox-pricing).

### Inferences
- Model choice matters far less than architecture: the whole spread of the structured pipeline across 15 models ($0.30–$33/month) is smaller than the hosted-agent bill on one model ($130–175/month).
- For Turkish-language dealer dialogue, a mid/small model (Haiku 4.5, Sonnet 5, GPT-5.6 Terra, Gemini 3 Flash) gives headroom for a richer system prompt (e.g., a 6–8k catalog summary) at still under $15/month; doubling the system prompt only raises the cached-read lines, which are the cheapest ones.
- Even if the company's real traffic is 5× the assumed 200 conversations, every structured-pipeline option stays under $170/month, i.e., under the cost of the hosted-agent approach at 1×.

### Gaps
- Output-token counts (including hidden reasoning tokens at `medium` effort) for the company's runs were not given, so the per-run total is a range.
- Cache-write pricing on Gemini and on GPT-5.4 Mini/Nano was assumed (no surcharge; 10% read price) — flagged in the table.

---

## Key Question 4: Framework fit for a 6-state dealer flow (collect → propose → confirm → generate → deliver → revise): LangGraph vs OpenAI Agents SDK vs Claude Agent SDK vs plain Python; observability; lock-in

### Takeaway
For a fixed state machine, plain Python (or PHP) with one structured-output call per state is the lowest-risk choice: no framework hosting requirements, no new abstractions, and every vendor's own guidance (Anthropic, HumanLayer) says start with direct API calls. LangGraph fits if you want a persisted graph with checkpoints; the OpenAI and Claude Agent SDKs are built around open-ended tool loops (handoffs, bash/file access) and add exactly the token-accumulating behaviour the company wants to avoid. Observability is cheap either way: OpenAI's Traces dashboard is free, Langfuse self-host is free/MIT, LangSmith is $39/seat.

### Cited Findings
- Design primitives: LangGraph is built around "stateful workflows" with typed state flowing through graph nodes and checkpointing for resuming after crashes or human approval; OpenAI Agents SDK emphasises "handoffs" between agents with typed sessions and native MCP; Claude Agent SDK centres on "bash execution, file writes, and a hook system" because Anthropic believes capable agents need real shell access; LangChain 1.0 went GA on 2025-10-22 with `create_agent` implemented as "a facade over this graph"; the author's verdict is that choice depends on "the shape of the work" — [Anubhav, Medium, 2026-09-01 (paywalled; excerpt only)](https://medium.com/data-science-collective/the-best-agent-framework-in-2026-langgraph-vs-openai-agents-sdk-vs-claude-agent-sdk-2c64e0b378d9)
- LangGraph persistence: checkpointers "persist a thread's graph state as checkpoints"; `InMemorySaver` loses everything on restart, `SqliteSaver` is "local file-based storage for development", `PostgresSaver` for production with async; a `thread_id` maintains continuity across invocations; persistence enables "conversation continuity, human-in-the-loop workflows, time travel, and fault tolerance"; graphs can be invoked per request with a DB checkpointer, or you run the Agent Server where "you do not need to implement or configure checkpointers or stores manually"; production advice: "use a persistent checkpointer" and prune checkpoints to avoid them "growing unboundedly" — [LangGraph persistence docs (official)](https://docs.langchain.com/oss/python/langgraph/persistence)
- LangSmith / LangGraph Platform pricing (official page, read 2026-09-21): Developer "$0 / seat per month… Up to 5k base traces / mo, then pay-as-you-go"; Plus "$39 / seat per month… Up to 10k base traces / mo"; consumption meters "LCU $1.50" and "LSU $1.00"; Plus includes "1 free Serverless (Small) deployment", extra deployments billed "Runtime Compute · 0.045 LCU / vCPU-hr" and "Runtime Memory · 0.006 LCU / GiB-hr"; self-hosted only on Enterprise — [LangChain pricing (official)](https://www.langchain.com/pricing)
- Langfuse vs LangSmith (June 2026): Langfuse Hobby free (50k units/month, 2 users, 30-day retention), Core $29/month (100k units), Pro $199/month, overage "$8 per 100k units", self-hosting free (Docker Compose/Helm/Terraform), core MIT-licensed, OpenTelemetry-based so you can "instrument once with OTel and keep Langfuse as a swappable backend"; LangSmith free 5k base traces/1 seat, Plus $39/seat with 10k traces, overage "$2.50 per 1k base traces (14-day), $5 per 1k extended (400-day)", closed source, self-host Enterprise only, and its "deepest value (Prompt Hub, native LangGraph tracing)… binds you to the LangChain stack" — [Morph, Langfuse vs LangSmith (secondary)](https://www.morphllm.com/comparisons/langfuse-vs-langsmith)
- OpenAI Agents SDK tracing is "built-in" and "enabled by default", viewable in the "OpenAI Traces dashboard" at no extra cost; captures "LLM generations, tool calls, handoffs, guardrails, and even custom events"; works with non-OpenAI models ("provide an OpenAI API key to the tracing exporter to enable free tracing"); can export to Langfuse, LangSmith, MLflow and others via trace processors — [OpenAI Agents SDK tracing docs (official)](https://openai.github.io/openai-agents-python/tracing/)
- Responses API and Agents SDK carry no separate fee ("included with standard API model pricing") — [eesel AI, 2026-09-11](https://www.eesel.ai/blog/openai-agents-api-pricing); Agents SDK is a "$0 framework" with only API costs — [Markaicode (search result title only)](https://markaicode.com/pricing/openai-agents-sdk-pricing/)
- Claude Agent SDK: "the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript"; use it when "Building an agent without implementing the tool loop yourself"; use the Client SDK when "Calling the API directly and implementing the tool loop yourself"; use Managed Agents for "long-running or asynchronous agents without managing your own sandbox or session infrastructure"; built-in tools "Read, write, edit files, run commands, and search the web", hooks, subagents, MCP, permissions, sessions, skills loaded from `.claude/`; other languages must "run the CLI as a subprocess with the `-p` flag"; third parties may not offer claude.ai login — API keys only; governed by Anthropic's Commercial Terms — [Claude Agent SDK overview (official)](https://code.claude.com/docs/en/agent-sdk/overview)
- Anthropic on frameworks: they "can obscure the underlying prompts and responses, making them harder to debug" and risk adding unnecessary complexity; "Start with direct LLM APIs"; the listed workflow patterns are prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer — [Anthropic, Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- 12-Factor Agents: Factor 5 "Unify execution state and business state", Factor 6 "Launch/Pause/Resume with simple APIs", Factor 8 "Own your control flow", Factor 12 "Make your agent a stateless reducer"; recommended approach is "small, modular concepts from agent building" rather than relying entirely on frameworks — [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)

### Inferences (framework-fit matrix for this company)

| Option | Maturity | Learning curve (non-dev owner + contractor) | Hosting need | Observability | Lock-in | Fit for 6-state dealer flow |
|---|---|---|---|---|---|---|
| (a) OpenAI Agents API hosted env | Public beta since 2026-09-10; US-only, no ZDR | Low to start, hard to control cost | None (OpenAI runs sandbox) | OpenAI dashboard | High (proprietary harness, sessions, artifacts) | Poor: loop + sandbox + 20k+ prefix per request; $130–175/mo at 200 runs |
| (b) OpenAI Agents SDK / Responses API + own function tools | GA, free framework | Medium (Python) | Your server must run the loop synchronously per webhook, or a worker | Free Traces dashboard | Medium (OpenAI-shaped, but works with other models) | OK if you keep 1 call per state; handoffs/loops not needed |
| (c) Claude Agent SDK | GA; built for coding-style agents with bash/files | Medium-high; Python/TS only | Long-running process with file system; not cron-friendly | Hooks + your own logging; Langfuse | Medium-high (Claude Code harness) | Poor for chat state machine; use plain Messages API + tool use instead |
| (c') Claude Messages API + tool use / structured JSON | GA | Low | Any HTTP client (PHP or Python cron) | Your logs / Langfuse | Low | Good |
| (d) LangGraph (open source) | GA 1.0 since 2025-10 | Medium-high (graph, state schema, checkpointer) | Python process; Postgres/SQLite checkpointer; per-request invocation possible | LangSmith ($39/seat) or Langfuse | Medium (LangChain ecosystem; LangSmith deep integration) | Workable but over-engineered for 6 states |
| (e) Low-code (n8n/Make/Botpress/WATI…) | Mature | Low for owner | n8n cloud €20/mo or self-host | Built-in execution logs | Medium-high per platform | Good for routing/notifications; weaker for multi-step plan generation |
| (f) Structured extraction + deterministic rules (plain Python/PHP) | Uses GA APIs only | Low; a few hundred lines | Runs on existing PHP webhook + Python cron; no persistent process | Log every request/response to DB; optional Langfuse | Lowest (swap model with one config change) | Best: ~3k tokens/turn, state in DB, code decides transitions |

- Hosting inference: (a) and (c) are the only options that inherently need a long-lived process or hosted sandbox; (b), (d) and (f) can be invoked per webhook or per cron tick as long as each model call returns in seconds. The company's current "PHP webhook + Python cron" shape maps directly onto (f) and (c').
- Learning-curve inference: LangGraph's value (checkpoints, time travel, human-in-the-loop interrupts) duplicates what a `conversations` table with a `state` column already provides in (f).

### Gaps
- The Medium comparison was paywalled; I could not extract its maturity/learning-curve verdicts beyond the primitives quoted. No independent 2026 benchmark comparing token overhead of the three SDKs on the same task was found.
- LangGraph open-source license was not confirmed on the pricing page (it is widely reported as MIT but I did not fetch the repo).
- Make.com and Botpress pricing pages were not fetched (Çebi Medya and beevaults pages failed on robots/timeout).

---

## Key Question 5: Reliability patterns — structured outputs, tool calling with validation, "LLM proposes, code disposes", guardrails, evals

### Takeaway
Vendor-guaranteed JSON-schema outputs (OpenAI Structured Outputs; Anthropic tool use) remove the parsing/retry class of failures, and the practitioner consensus (Anthropic, HumanLayer, cost-audit posts) is that keeping control flow in code — the LLM only classifies/extracts/drafts — reduces both cost (fewer, smaller calls; no re-sent context) and error accumulation (each step is validated before the next). Evidence is mostly qualitative and from vendors/practitioners; I found no controlled study quantifying error reduction for a WhatsApp-scale bot.

### Cited Findings
- OpenAI Structured Outputs: "the model will always generate responses that adhere to your supplied JSON Schema, so you don't need to worry about the model omitting a required key, or hallucinating an invalid enum value"; "Reliable type-safety: No need to validate or retry incorrectly formatted responses"; "Explicit refusals: Safety-based model refusals are now programmatically detectable"; available from GPT-4o onward, OpenAI recommends gpt-6-astra for new projects (any current model works); guidance: use function calling "when you are building an application that bridges the models and functionality of your application", and `response_format` "when you want to indicate a structured schema for use when the model responds to the user"; only a subset of JSON Schema is supported — [OpenAI Structured Outputs guide (official)](https://developers.openai.com/api/docs/guides/structured-outputs)
- 12-Factor Agents Factor 1 "Natural Language to Tool Calls", Factor 4 "Tools are just structured outputs" (treat tool calls as deterministic JSON generation), Factor 8 "Own your control flow", Factor 9 "Compact Errors into Context Window"; core observation that production "agents" are "mostly deterministic code, with LLM steps sprinkled in" — [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents)
- Anthropic: workflows are "Best for well-defined, predictable tasks requiring consistency"; agents for "open-ended problems"; "Many applications succeed with optimized single LLM calls"; prompt chaining uses "programmatic checkpoints" between steps; routing classifies inputs to specialised downstream processes — [Anthropic, Building effective agents](https://www.anthropic.com/research/building-effective-agents)
- Cost/error evidence for deterministic control: re-sent context was "62% of agent bills" in production audits and token use varied "up to 30x across runs on identical problems" — i.e., open loops are both expensive and non-deterministic in cost — [Larridin, 2026-08-14](https://larridin.com/blog/ai-agent-context-accumulation-cost)
- OpenAI Agents SDK provides guardrail spans and captures "guardrails" in traces (input/output guardrails are first-class) — [OpenAI Agents SDK tracing docs](https://openai.github.io/openai-agents-python/tracing/)
- Anthropic caching economics reward the pattern: a stable prefix "pays off after 1 read" at the 5-minute tier — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Structured-output practitioner posts in 2026 (schema enforcement, validation in pipelines) exist but were not fetched in full; titles indicate the same message ("JSON Schema Enforcement and Tool Calling Reliability Assurance", 2026-05-06; "How to Stop JSON From Breaking Your AI Workflow", May 2026) — [BetterLink](https://eastondev.com/blog/en/posts/ai/20260506-llm-structured-output/); [Towards AI](https://pub.towardsai.net/llm-structured-outputs-in-production-how-to-stop-json-from-breaking-your-ai-workflow-66703754d341) (search results, not verified in detail)

### Inferences
- Recommended pattern for the dealer flow: per incoming message, one call with a strict JSON schema such as `{intent, extracted_fields{...}, missing_fields[], confidence}`; code then (1) validates fields against the catalog DB, (2) decides the next state, (3) either asks the dealer a templated question or calls the plan generator. The LLM never chooses tools freely and never sees the file system.
- Evals: because every step is a pure function (message + state → JSON), a regression suite is a table of (input message, expected JSON) rows that can be re-run for pennies on every prompt change — this is the "stateless reducer" of Factor 12.
- Guardrails for this use case are mostly deterministic (catalog-ID whitelist, price bounds, required-field checks) and belong in code, not in a second LLM call.

### Gaps
- No quantitative, peer-reviewed comparison of error rates between free tool-loop agents and schema-constrained pipelines for customer-messaging bots was found; the evidence is vendor docs plus practitioner cost audits.
- Anthropic's tool-use/structured-output guarantee wording was not fetched from its own docs page (only the pricing and Agent SDK pages were), so the exact guarantee language for Claude should be confirmed.

---

## Key Question 6: Hosting — what fits shared PHP/Python cron hosting vs what needs a VPS; VPS costs in 2026

### Takeaway
Shared cPanel/CloudLinux hosting caps each account with LVE limits (typically 1 GB physical memory, 20 entry processes, 100 processes) and kills processes that exceed them — cron and SSH jobs included — which is exactly the failure the company hit. A structured-extraction pipeline (short HTTP calls, state in MySQL) fits within those limits; anything long-running (agent loops, LangGraph Agent Server, n8n, vector DB, sub-second webhook workers) needs a small VPS, which in 2026 costs €5.49–8.49/month at Hetzner (after the 15 June 2026 increase), $6–12/month at DigitalOcean, or ~$3.49–7.99/month (171–392 TL) on a 24-month term at a Turkish provider.

### Cited Findings
- CloudLinux LVE limits: SPEED (CPU), PMEM "Physical memory limit (RSS…)", VMEM, EP "Limit on entry processes… max number of concurrent connections", NPROC, IO, IOPS; when PMEM is exceeded "CloudLinux OS will first free up memory used for disk cache, and if that is not enough, it will kill some of the processes within that LVE… This will usually cause web server to serve 500 and 503 errors"; cron jobs and SSH/CLI processes are subject to the limits; typical hosting account: "SPEED=100%; PMEM=1GB; VMEM=0; IO=1024KB/s; IOPS=1024; NPROC=100; EP=20" — [CloudLinux docs (official)](https://docs.cloudlinux.com/cloudlinuxos/limits/)
- Hetzner price adjustment effective "15 June 2026; 8 AM CEST" for new orders and rescales (Germany/Finland): CX23 (2 vCPU/4 GB/40 GB) €3.99 → €5.49/mo (+37.5%); CX33 (4 vCPU/8 GB/80 GB) €6.49 → €8.49/mo (+31%); CAX11 (ARM, 2 vCPU/4 GB) €4.49 → €5.99/mo (+33.3%); CPX22 €7.99 → €19.49/mo (+143.8%) — [Hetzner Docs price adjustment (official)](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/)
- Pre-increase Hetzner plan table (CX23 €3.99, CX33 €6.49, CX43 €11.99, CAX11 €4.49, CPX22 €7.99) with "IPv4 Fee: €0.50/month additional"; DigitalOcean's 2 vCPU/4 GB droplet quoted at "$24/€22" — [Bitdoze (secondary; dates the increase to 2026-04-01, which conflicts with Hetzner's own 15 June 2026 notice — trust Hetzner)](https://www.bitdoze.com/hetzner-cloud-cost-optimized-plans/)
- DigitalOcean Basic Droplets (official page, read 2026-09-21): 512 MiB/1 vCPU $4.00/mo; 1 GiB/1 vCPU $6.00/mo; 2 GiB/1 vCPU $12.00/mo; 2 GiB/2 vCPU $18.00/mo; 4 GiB/2 vCPU $24.00/mo — [DigitalOcean Droplet pricing (official)](https://www.digitalocean.com/pricing/droplets)
- Turkish provider hosting.com.tr VPS (24-month term prices): Small 2 core/2 GB/50 GB NVMe "$3.49/month" (171.01 TL); Medium 4 core/4 GB/100 GB "$7.99/month" (391.51 TL); Large 4 core/6 GB/150 GB "$14.99/month" (734.51 TL); locations "TR, DE, UK, FR ve ABD"; "Fiyatlar 24 aylık alımlarda geçerli aylık maliyeti ifade eder" (monthly billing costs more) — [hosting.com.tr (official vendor page)](https://www.hosting.com.tr/server/vps-server/)
- Turkish VDS market guide (2026-08-23): "VDS ücretleri genellikle giriş seviyesinde aylık birkaç yüz TL'den başlar" (entry-level VDS starts at a few hundred TL/month); no exact tariffs — [Netlen blog](https://www.netlen.com.tr/blog/vds-ucretleri-ne-kadar)
- Managed n8n hosting example: Sliplane €9/month per server "HTTPS, health checks, persistent storage, and backups" — [Sliplane n8n pricing guide, July 2026](https://sliplane.io/blog/n8n-pricing)
- LangGraph production guidance requires a persistent checkpointer (Postgres) — [LangGraph persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence); Claude Agent SDK needs a Python/TS runtime with file/bash tools — [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)

### Inferences (what runs where)

| Workload | Shared cPanel (LVE ~1 GB PMEM, EP 20) | Small VPS (2 vCPU/4 GB, €5.49–8.49) |
|---|---|---|
| Meta webhook receiver (PHP, must ack fast, then enqueue) | Yes — store message, return 200 | Yes |
| Structured-extraction call (one HTTP request, seconds) | Yes, from PHP or Python cron | Yes |
| Python cron every minute processing a queue | Yes if memory-light (avoid heavy ML libs; LVE kills >1 GB) | Yes |
| Plan generation (PDF/DOCX render) | Marginal — memory spikes are what trip LVE | Yes |
| Long-running agent loop / LangGraph Agent Server / Claude Agent SDK | No (killed by PMEM/NPROC, no daemon) | Yes |
| n8n / Botpress self-host | No | Yes (n8n self-host is free) |
| Vector DB (pgvector/Qdrant) | No | Yes (or use a hosted DB) |

- The LVE memory kill the company experienced is most plausibly the Python cron importing heavy libraries or holding large payloads (e.g., an SDK plus PDF rendering) rather than the LLM call itself; the structured pipeline's calls are small HTTP requests.
- A €5.49–8.49/month Hetzner CX23/CX33 (or a ~$3.49–7.99 Turkish VPS) is cheaper than one month of the hosted-agent experiment and removes the LVE constraint entirely; keeping the PHP webhook on shared hosting and moving only the Python worker to the VPS is a valid split.

### Gaps
- No Turkish-provider VPS page besides hosting.com.tr gave concrete monthly (non-24-month) prices; Turkish VAT (KDV) treatment on those prices was not confirmed.
- Hetzner's Helsinki/Nuremberg vs Ashburn/Singapore price differences after 15 June 2026 were not captured; the IPv4 add-on (€0.50) is from the secondary source.

---

## Key Question 7: Low-code options, Turkish-market WhatsApp bot vendors, and Meta WhatsApp Cloud API pricing (2025–2026)

### Takeaway
Since 1 July 2025 Meta bills per delivered template message, not per 24-hour conversation; dealer-initiated chats inside the 24-hour service window are free, so a dealer assistant's Meta bill is essentially zero except for out-of-window utility templates (Turkey ≈ $0.0009 each; marketing ≈ $0.0109). Low-code platforms cost €20–200/month plus message markups and are good for routing/notifications but weak at multi-step plan generation; Turkish vendors mostly hide prices behind demos.

### Cited Findings

**Meta WhatsApp Business Platform pricing**
- Per-message model: "You are only charged when a template message is delivered"; four categories — Marketing (full rate), Utility and Authentication (volume-tier discounts), Service ("Free for all businesses"); "Utility template messages sent within an open customer service window are free"; the 24-hour customer service window opens when the user messages first; Click-to-WhatsApp ad entry gives a "72 hour" free window; volume tiers are monthly, market- and category-specific; effective April 1, 2026: "Turkey – Lower utility and authentication rates"; billing localisation for Brazil starts July 1, 2026 — [Meta for Developers, WhatsApp pricing (official)](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- Turkey rates as relayed by a Turkish BSP citing Meta's rate card effective 1 April 2026: Marketing "$0,0109 / mesaj", Utility "$0,0009 / mesaj", Authentication "$0,0009 / mesaj", Service "Ücretsiz / pencere içi"; "1 Temmuz 2025 İtibarıyla… 24 saatlik konuşma penceresi bazlı ücretlendirme sona erdi. Artık gönderilen her şablon mesajı ayrı ayrı, kategorisine göre ücretlendiriliyor"; VatanSMS adds no platform fee ("ayrı bir platform ücreti eklenmez") — [VatanSMS (Turkish BSP; secondary for Meta rates)](https://www.vatansms.com/whatsapp/business-api-fiyatlar/)
- Twilio's WhatsApp channel: "Zero monthly subscription" plus "$0.005 lookup" per message on top of Meta's template charges; "Requires development — Twilio gives you the connection layer, not a ready-made bot"; SOC 2 / HIPAA / ISO 27001 — [Achiya, 2026-05-24 (reviewed 2026-08-25)](https://achiya-automation.com/en/blog/whatsapp-bot-platforms-comparison-2026/)

**Low-code / bot platforms (2026)**

| Platform | Price (2026) | Notes | Source |
|---|---|---|---|
| n8n Cloud Starter | €20/mo (annual) — 2,500 executions, 5 concurrent | unlimited users/workflows | [Sliplane, July 2026](https://sliplane.io/blog/n8n-pricing) |
| n8n Cloud Pro | €50/mo (annual) — 10,000 executions, 20 concurrent | insights, workflow history | same |
| n8n self-hosted Community | Free software; "you still pay for the server, storage, backups, monitoring, and your own maintenance time" | needs a VPS | same |
| ManyChat | $15–$200+/mo, grows with contacts ("10,000 contacts pays $200+/month") | English-only UI | [Achiya](https://achiya-automation.com/en/blog/whatsapp-bot-platforms-comparison-2026/) |
| WATI | Plan varies by market; "Message charges are additional and vary by category and WATI's current rate card" | managed official API, no-code bot, team inbox | same |
| WAHA (unofficial) | $10–30/mo server only | not official Meta API; "broadcast risk = account ban" | same |
| Twilio | $0 base + $0.005/msg + Meta | connection layer only | same |
| Custom bot (agency example) | $1,000–$3,500 one-time + ₪100–300/mo ops; "After 6–12 months, cheaper than SaaS" | | same |
| Botpress | listed as "Open-source/custom" in Turkish comparison; no price captured | | [Supsis, 2026-04-24](https://supsis.com/blogs/en-iyi-whatsapp-bot) |

**Turkish-market vendors (brief)**
- Supsis AI: Turkish/local, "Omnichannel & yerli destek", TL pricing described as "ekonomik", "✅ Tam Destek" for Turkish; the same comparison rates Intercom and Zendesk "Yüksek / USD", ManyChat and Wati "Orta / USD"; no numeric prices — [Supsis blog, 2026-04-24 / modified 2026-05-20](https://supsis.com/blogs/en-iyi-whatsapp-bot)
- VatanSMS: Turkish BSP-style provider passing Meta rates through with no platform fee (see above) — [VatanSMS](https://www.vatansms.com/whatsapp/business-api-fiyatlar/)
- YazılımPark (Turkish chatbot vendor, 2026-05-19): no public prices; warns "'Önce demo yapalım' diye fiyat saklayanlar genellikle pahalı çıkar" (vendors that hide prices behind a demo usually turn out expensive) — [YazılımPark](https://yazilimpark.com/blog/whatsapp-chatbot-fiyatlari-2026-kurulum-ve-maliyet-rehberi)
- Other Turkish names surfaced by search but not verified in detail: Jetlink ("AI Agent platform for all customer touch points", enterprise) — [jetlink.io](https://www.jetlink.io/); Sestek (enterprise conversational AI, insurance/banking) — [Sestek blog](https://www.sestek.com/revolutionizing-the-insurance-industry-with-chatbots-blog); Palmate AI (WhatsApp API setup guides) — [Palmate](https://palmate.ai/tr/cozumler/whatsapp-business-api-fiyat-ve-kurulum); WaMessage (price calculator) — [WaMessage](https://wamessage.app/whatsapp-api-fiyat-hesaplama.php); Kommo/WATI-style CRM bots are represented by WATI above.

### Inferences
- For 200 dealer conversations/month the Meta bill is negligible: if every conversation needed two out-of-window utility templates, 400 × $0.0009 = $0.36/month; marketing templates are ~12× dearer ($0.0109) and should be avoided for operational messages.
- Low-code tools are best used as a thin layer (receive webhook, route, send template) around the deterministic Python/PHP core; n8n self-hosted on the same VPS costs nothing extra, but the multi-step "collect → propose → generate" logic is easier to test as plain code with a JSON-schema call than as a visual flow.
- Turkish vendors' opacity on pricing (and their positioning toward enterprise) makes them a poor fit for a non-developer owner who wants predictable per-conversation cost; a direct Meta Cloud API integration (already in place) plus a cheap model is the most transparent option.

### Gaps
- Meta's own Turkey rate card values were not read directly from Meta (only the structure and the "lower utility/authentication rates from 1 April 2026" note); the $0.0109 / $0.0009 figures are from VatanSMS quoting Meta and should be confirmed on Meta's rate-card download.
- Botpress, Make, Kommo and Twilio Studio pricing pages were not fetched; WATI's 2026 plan prices were not captured.
- Only one Turkish vendor comparison (Supsis) was accessible; Çebi Medya's price table timed out; none of the Turkish sources published numeric monthly plan prices.
