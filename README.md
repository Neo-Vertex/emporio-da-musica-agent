# Empório da Música — Customer Service Agent

A Python text agent ("Lia") that answers customers of Empório da Música, a fictional musical instrument store in Campo Grande/MS. It looks up **data** (products, prices, stock, promotions, orders) through tools and answers **policy** questions (hours, payment, returns, shipping) from the store manual.

Author: **Nelson Araujo**

**Live demo:** https://artefact-desafio-tecnico.neovertex.top — password **`artefact`** (optional: everything also runs locally, see below).

The core deliverable is the agent (`emporio/`) with a terminal interface. The web page, the purchase flow and the evals are extras built on top of the same agent.

## Quick start

Requirements: Python 3.10+ and an OpenAI API key.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
cp .env.example .env            # then put your key in OPENAI_API_KEY
```

| Command | What it does |
|---|---|
| `python cli.py` | Chat with Lia in the terminal (`reset` starts over, `exit` quits) |
| `python cli.py --debug` | Same, also showing which tools the agent called |
| `python -m emporio.tools` | Self-check of the business rules (no API key needed) |
| `python evals.py` | Automated evaluation: 15 scenarios against the real model (~2 min) |
| `uvicorn app:app --port 8000` | Optional web page at http://localhost:8000 — **password: `artefact`** |

**Web page (optional).** Made so the evaluator can test without a terminal. Besides the chat, it has an **"agent brain" panel** that shows, live, each step of the code: the call to the model (with token count and how much came from the prompt cache), the tool the model chose and its arguments, the Python result sent back, and whether the answer came from data or from the manual. A **CRM** list shows orders created during the demo. An **EN/PT** toggle switches the page, Lia's replies and the step explanations (English by default; the store's real customers would use Portuguese). The password can be changed with `CHAT_PASSWORD` in `.env`.

The model is set in `.env` (`OPENAI_MODEL`, default `gpt-5.4-mini`).

## How it works

```
customer message
   → agent.py sends: system prompt (persona + rules + full manual) + current time + history + tool list
   → the model either answers, or asks for a tool
   → tools.py runs the tool on the CSV data and returns ready-to-use numbers
   → the model writes the final answer (up to 5 tool rounds per message)
```

| Tool | Purpose |
|---|---|
| `search_products` | Catalog search by text, category, price range or promotion. Returns list price, promo price, PIX price and installments already calculated; for an unavailable item, returns 3 available alternatives. |
| `simulate_installments` | Max interest-free installments for an amount (manual §3.1). |
| `get_order_status` | Status, items, tracking, days late / days since delivery. Requires order number **and** the customer's email or phone. |
| `create_order` | Places a delivery order: validates stock, computes prices, PIX/promotion, shipping (free in Campo Grande from R$500, else R$35; other cities quoted by the team) and installment limits. Called first as a quote; only saved to the simulated CRM (`logs/orders_crm.jsonl`) after the customer explicitly confirms. |
| `handoff_to_human` | Hands the case to the team (complaints, late orders, returns to formalize). Writes to `logs/handoffs.jsonl`. |

```
emporio/tools.py    data loading, business rules, tool schemas
emporio/agent.py    system prompt and function-calling loop (emits each step as an event)
app.py              web backend (FastAPI, streams the agent's steps)
static/index.html   web page: chat, agent brain panel, CRM list
cli.py              terminal interface
evals.py            evaluation scenarios
examples/           5 example conversations
```

## Technical decisions

**Approach: function calling, no framework.** Questions are predictable (price, stock, order), so a few closed tools give control: the model can only call functions I defined and never queries data freely (a SQL agent could read the whole customer table). The official OpenAI SDK covers the loop in ~40 lines; LangChain/LlamaIndex would add weight without benefit at this size.

**Rules live in code, language lives in the model.** Promotion price, the PIX discount (5%, not stackable with promotions), installments, and date math are computed in `tools.py`. The model only decides what to look up and how to say it. This came from testing: the model answered "R$600 in up to 12x" (wrong: the minimum installment in that range is R$100, so 6x).

**Model: OpenAI `gpt-5.4-mini`.** Mature function calling, automatic prompt caching and low cost. A small model is enough because the hard parts are deterministic code. It is configurable via `.env`.

**Retrieval: full manual in the prompt, no RAG.** The manual is 8 pages (~4k tokens). At this size, sending it whole is simpler and more reliable: some answers combine sections (e.g. "PIX on a promoted item" needs §3 and §6.2), which chunk retrieval can split. Rule of thumb I used: up to ~20k tokens → whole document; above ~100k, many documents or frequent updates → RAG (section-based chunks, embeddings, top-k with section citations).

**Prompt strategy.**
- Three layers: a fixed system prompt, a separate current-time message, and the tool descriptions (the model reads them to choose tools).
- System prompt blocks: identity → tone (taken from manual §7.1) → *when to use each source* (explicit routing) → business rules that cause the most mistakes → scope → corrections to the manual → full manual.
- Techniques: explicit format examples (`"de R$ 100,00 por R$ 90,00, 10% off"`), negative examples, emphasis (ALWAYS/NEVER) only on rules that failed in testing.
- Written in English, with the instruction to always reply in Brazilian Portuguese (the store's customers).
- The current time is a separate message so the large prefix stays identical and OpenAI can cache it.

**Data handling.** CSVs are read with the standard library (65 products; pandas was unnecessary). Only active promotions are used (4 of 25). Search is accent-, case- and hyphen-insensitive ("gd-20" matches "GD20").

**Privacy (LGPD).** An order is only shown with the order number plus the matching email or phone (last 8 digits, so any phone format works). A wrong contact and a non-existent order get the same answer, so order numbers cannot be enumerated. The defense is in the tool, not only in the prompt: a prompt injection cannot leak data the tools never return (see example 05).

**Purchase flow (extra).** The case asks for an agent that helps the team with recurring questions; placing orders was not required. I added it because "I want to buy X" is the natural next message after a price question, and it exercises the same rules (promotion, PIX, installments, shipping from manual §5) end to end. It is safe by design: the tool first returns a quote and only saves the order after an explicit "yes" from the customer.

**Interface and history.** A CLI is the simplest thing an evaluator can run; the web page adds visibility into what the agent is doing. Both use the same `Agent` class. History is kept in memory per conversation; `reset` starts over. The public demo has cost guards (password, max turns per conversation, max message length).

**Prompt caching works.** The agent brain panel shows it on every call: e.g. 6,528 of 6,592 input tokens served from cache, because the large prompt prefix never changes.

## Assumptions

- **Phone:** the manual lists two WhatsApp numbers; I use (67) 3341-4444 (cover page and company data) and treat the one in §7 as a typo. The email is used without the accent.
- **Installments:** "no minimum (except below R$50)" for up to 3x is read as a R$50 minimum installment.
- **Delivery date:** the data has no actual delivery date, so the estimated delivery date is used as the receipt date for the 7-day return rule.
- **Current date:** the agent uses the real date (Campo Grande, UTC-4). Since the orders are from early 2026, open orders show up as late and the agent apologizes and hands them off.
- **Partner stores:** the manual mentions suggesting partners but lists none, so the agent does not invent names.

**Data issues found and how the agent handles them.** The CSVs are the store's source of truth, so they were not edited; the agent handles each case safely and the issues are reported here so the store can fix them at the source.

| Issue in the data | How the agent handles it |
|---|---|
| 21 of 25 promotions are inactive | Only the 4 active ones are used, so Lia never offers an expired discount (manual §7.3). |
| Product 136 is discontinued but has 13 units in stock | Status wins over stock: Lia says it is discontinued and `create_order` refuses to sell it. |
| Product 130 is "coming soon" but was sold before (order 3, delivered) and has a pending order (14) | Read as a **restock**, not a launch: it cannot be bought right now, Lia says it is expected back soon and offers alternatives. This also explains the pending order (waiting for the item). Past orders are shown normally. |
| Totals of orders 3 (R$3,450 vs R$3,498) and 20 (R$1,400 vs R$1,488) differ from the sum of their items | Lia reports the recorded total (what the customer paid) and never recalculates it; likely a discount missing from the data. |
| 3 categories have no products (woodwinds, brass, orchestral strings), although the manual says the store sells them | The search returns nothing and Lia says there are no options right now, without inventing products or denying that the store works with them. |
| Some products have more than one promotion record | No product has two *active* promotions, and only active ones count, so there is no conflict. |

## Testing

- `python -m emporio.tools` checks the deterministic rules (installments, PIX not stacking, alternatives for out-of-stock items, identity check, order quote vs. confirmation, shipping).
- `python evals.py` runs 15 scenarios against the real model and checks behavior, not exact wording: which tools were called and what the answer must or must not contain (prices, refusals, no data leaks, the purchase flow asking for confirmation). Results vary between **14/15 and 15/15** across runs, because the model is not fully deterministic (e.g. once it asked to confirm the quantity before quoting, which is reasonable, so that check was relaxed to what matters: never placing an order without confirmation). On its first run it caught a real bug: the agent **solved a math homework question** (23 × 47) despite the scope rule; the prompt was tightened and the case now passes. It also showed that checks must be flexible ("não abrimos" is as valid as "fechado").
- I generated the conversations in `examples/` with the real agent and reviewed each one. What the review found, and the fix:

| Finding | Fix |
|---|---|
| Wrong installment count (12x instead of 6x) | New `simulate_installments` tool |
| Promotion shown without the discount % | Format rule with example in the prompt |
| No alternatives for out-of-stock items (prompt alone did not fix it) | `search_products` returns `available_alternatives` |
| Confusing phrasing ("tem, mas está esgotado") | Wording rules in the prompt |
| Order lookup called with an empty email | Guard inside the tool |

**Iteration example (out-of-stock item).** The manual (§7.3) says to suggest similar available products when an item is out of stock.
1. *Test:* asked for the Giannini GF-3D (0 units). Lia said it was out of stock and only *offered* to suggest alternatives.
2. *Prompt fix:* added "in the same reply, suggest 2–3 alternatives". Re-ran the test: same behavior. The model would have to decide on its own to run a second search, and it didn't.
3. *Code fix:* `search_products` now returns `available_alternatives` (same category, closest price, in stock) whenever the requested item is unavailable, and the prompt only tells Lia to present them.
4. *Validation:* an assertion in the self-check (`python -m emporio.tools`) guarantees 3 alternatives for this case, and the regenerated conversation (`examples/05_out_of_scope.md`) shows them in the answer.

Lesson: exact rules belong in code; tone and wording belong in the prompt.

## Known limitations and next steps

- **Search** is keyword-based: no synonyms or typos ("takamini"). Next: fuzzy matching or embeddings.
- **Alternatives** match category and price only (may suggest nylon to someone looking for steel strings). Next: filter by specs.
- **Evals** are keyword-based and run once per case; model answers vary. Next: run each case several times, use an LLM judge for tone, and run them in CI on every prompt change.
- **Orders** do not decrement stock (CSVs are read-only) and only the city of Campo Grande counts as the metro area; split payment (e.g. PIX + card above R$2,000) is not supported.
- **API failures** are not handled in the CLI. Next: retries with backoff, timeout and a fallback message.
- **History** is in memory only. Next: persist per customer (Redis/Postgres) and summarize long conversations.
- **Channel:** the agent is channel-agnostic (`agent.reply(text)`), so WhatsApp would be a webhook (e.g. Evolution API or Meta Cloud API) calling it, with human handoff in a tool like Chatwoot.
- **Security:** no rate limit on order lookups; handoff log has no retention policy.

## Use of AI coding assistants

I built this project with the help of **Claude (Anthropic)**, used throughout the work to orchestrate the project, generate the code from my specifications, align the business rules with the tests, and catch errors that could otherwise go unnoticed. My workflow:

1. **Understand.** I read the case brief and the store manual, then went through them with the assistant to make sure my interpretation had no mistakes, including each inconsistency in the manual and the data (see *Assumptions*).
2. **Plan.** I listed the requirements and set priorities: mandatory deliverables first. I chose OpenAI as the provider and decided not to build a live WhatsApp integration, since an evaluator would likely not test it.
3. **Build in steps.** The assistant generated the code from my specifications, one step at a time, each step in its own commit. I required an explanation of every decision (architecture, why no RAG, why rules in code) before moving on.
4. **Verify.** The test conversations were reviewed one by one, and that review found errors such as the wrong installment count; each one was fixed and re-tested. I then decided to add an automated eval, which caught a real bug on its first run (the agent answering a math question).
5. **Think about the evaluator.** I added the web page so the agent can be tested without a terminal (the CLI is still there for whoever prefers it), the EN/PT toggle, and the live demo.

This let me deliver a working, tested agent while focusing on the decisions, which is the part I can explain and defend.
