# ProcurelAI

Reads supplier quotations, compares them with the purchase request, checks them against the company rules, and gives one answer per document: **Approve**, **Reject** or **Needs a person to check**, with the exact text from the document behind every reason. When it is not sure, it stops and asks a person.

| Part | Technology |
|---|---|
| Backend API | **FastAPI** (Python 3.12), Pydantic |
| Fixed steps | **LangGraph (Python)** `StateGraph` |
| AI | **Groq** free model, `llama-3.3-70b-versatile` by default |
| PDF text | pdfplumber |
| Database | **Supabase** (Postgres) via `supabase-py` |
| Frontend | **Next.js 15** (App Router), **Tailwind CSS 4**, TypeScript |
| Tests | pytest (30 tests) |

```
backend/    FastAPI + LangGraph    (app/, tests/, data/ sample PDFs)
frontend/   Next.js + Tailwind     (proxies /api/* to the backend)
supabase/   schema.sql
```

## Run it

**1. Backend** (Python 3.11 or newer)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                    # keys are optional to start
uvicorn app.main:app --reload --port 8000
```

**2. Frontend** (Node 20 or newer), in a second terminal
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                                             # http://localhost:3000
```

**3. In the app:** click **Load the sample purchase request**, then **Check the 10 sample quotations** (or drop your own PDFs).

Or with Docker: put your keys in `backend/.env`, then `docker compose up --build` and open http://localhost:3000.

### Keys (both optional)
- **Supabase:** create a project, run `supabase/schema.sql` in the SQL editor, then set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`. The key stays on the server. Without them the app uses temporary in-memory storage (a chip at the top of the page says which).
- **Groq:** create a free key at https://console.groq.com/keys and set `GROQ_API_KEY`. Change the model with `GROQ_MODEL` (for example `llama-3.1-8b-instant`). Without a key the app runs on the fixed reader only (a chip says so).

### Tests
```bash
cd backend && pytest        # 24 pipeline tests + 6 API tests
```

## The fixed steps

`backend/app/graph.py` is a LangGraph `StateGraph`. The order is written in code and never chosen by a model:

1. **Read the PDF.** No text (a scan) means stop and ask a person.
2. **Read the layout with fixed patterns** (`extract/rules_reader.py`).
3. **Read the quotation with the AI** (`extract/ai_reader.py`, Groq JSON mode, temperature 0). Every fact must come with a quote.
4. **Check every quote against the document** (`extract/reconcile.py`).
5. **Compare with the purchase request** (`rules/compare.py`): price and quantity, line by line.
6. **Check the contract rules** (`rules/contract.py`).
7. **Give the final answer** (`rules/decide.py`).
8. **Ask a person**, only when the answer is Needs a person to check. The person's Approve or Reject and reason are saved to `human_reviews`.

The only branches are two plain if-checks: stop early if the PDF cannot be read, and ask a person when the answer is not a clear Approve or Reject.

## How it never guesses

- The AI only **copies facts and quotes**. Approve, Reject and Needs a person to check come from plain Python in `app/rules/`, using exact `Decimal` maths.
- Every value needs a quote that appears **word for word** in the PDF text, and the number must appear in its own quote. Otherwise the value is thrown away and flagged.
- The AI and the fixed reader read every field independently. If they **disagree**, the field is left empty and a person is asked.
- A rule that cannot be tested is marked "Could not be tested" and goes to a person. It is never passed by default.
- Doubt never causes a Reject. A Reject always rests on a verified quote (or on a confirmed absence, such as no penalty clause anywhere in the text).
- If the AI is off, fails or returns broken JSON, the fixed reader still works and the step trace says the AI step was skipped.

## API (FastAPI, also browsable at http://localhost:8000/docs)

| Route | What it does |
|---|---|
| `GET /api/health` | Storage and AI mode, sample files |
| `GET /api/purchase-request`, `POST` | Read, or replace (CSV file or `{"sample": true}`) |
| `POST /api/analyze` | Check one PDF (multipart `file`, or `{"sample": "supplier-pack-01.pdf"}`) |
| `GET /api/analyses`, `GET /api/analyses/{id}` | Results |
| `POST /api/analyses/{id}/review` | A person's Approve or Reject (reason optional). Can be sent again to change the answer |
| `DELETE /api/analyses/{id}/review` | Take the person's answer back (the document waits again) |
| `DELETE /api/analyses/{id}` | Delete a result together with its review |

The browser only talks to Next.js. `frontend/next.config.ts` forwards `/api/*` to FastAPI (`API_URL`), so no CORS setup is needed. `API_URL` is read when you build the frontend.

## Decisions I made where the rules were silent

- **Penalty below the minimum** (at least 0.5% of order value per week): treated as **Needs a person to check** (rule id N1). The penalty also goes to a person if it is not stated per week or does not say it applies to order value. For example, Bhairab's "0.5% per week of delay" does not say what the percent applies to.
- **Rule order:** any Reject finding means Reject, even when other items need a check.
- **Delivery date:** quotes give a time after the purchase order ("within 4 weeks of PO"), not a calendar date. It is read as a time and converted to days (4 weeks = 28 days). No date is invented.
- **Payment range:** "30 to 90 days as agreed" is both open wording and outside 30 to 60 days. It is reported once.
- **Rounding:** money amounts match if they differ by no more than 0.01 BDT.
- **Purchase request match:** by the reference printed on the quotation, then by item letter, description and unit.

## Expected results for the sample pack

| File | Supplier | Answer | Why |
|---|---|---|---|
| 01 | Padma Textile Mills | Approve | All rules pass |
| 02 | Jamuna Trims | Approve | All rules pass |
| 03 | Karnaphuli Yarn | Reject | R1: 229.00 is 9.05% above 210.00 |
| 04 | Surma Packaging | Needs a person to check | C1: 6.65 is 2.31% above 6.50 |
| 05 | Meghna Carton | Reject | R2: 40% advance |
| 06 | Teesta Fabrics | Reject | R3: no late-delivery clause |
| 07 | Rupsha Zipper | Needs a person to check | C2: 16,500 vs 20,000 (17.5% below) |
| 08 | Bhairab Thread | Reject | R4: no TIN or BIN (also N1) |
| 09 | Dhaleshwari Poly | Needs a person to check | C3 open payment terms, C6 line total 322,000 should be 320,000 |
| 10 | Kushiyara Box | Reject | R5: 60 days delivery (also C5, VAT included) |

## Results list behaviour

- **Reload clears the results.** The list lives in the browser tab's memory (`frontend/src/lib/session.tsx`), so reloading the window starts empty. Rows already saved on the server (memory or Supabase) are not shown again; use **Delete** to remove them from the server too.
- **Delete** on a row (or on the detail page) removes the result and its person review.
- **Needs a person to check** rows have **Accept** and **Reject** buttons. The choice can be changed any time, or taken back with **Undo**. The reason is optional.
- **Why, with the exact text** column: every reason for a Reject (or a check) is listed with the quote from the document that supports it.

## Notes

- Free Groq limits (confirm in your console): about 12,000 tokens per minute and 100,000 per day on `llama-3.3-70b-versatile`. The upload panel checks one file at a time and the Groq call retries on rate limits.
- Scanned PDFs have no text layer. They are sent to a person rather than OCR'd. Adding Tesseract OCR in `app/pdf.py` is the natural next step.
- A person's answer is stored with the saved result rather than through a LangGraph checkpoint. If you later want LangGraph's own pause and resume (`interrupt`), the `ask_person` step is the place to add it.
