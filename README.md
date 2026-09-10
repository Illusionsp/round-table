# Roundtable

A multi-model deliberation backend and UI. Instead of asking one LLM and taking its first answer, Roundtable puts several models through a full council process — each answers independently, they anonymously peer-review each other's work, and a chairman model synthesizes a final answer from the best of everything. Built entirely on free OpenRouter models, so running it costs $0.

## Why this exists

Ask one LLM a hard question and you get one model's blind spots baked into the answer, with no way to tell where it's confident versus guessing. Roundtable gets multiple independent takes first, then makes the models grade each other's work *before* anyone gets to see whose answer is whose — so a model can't just favor itself or a well-known rival — and only then produces a final synthesis. Every stage stays inspectable, so you can see exactly which model said what, how the others ranked it, and why the final answer looks the way it does.

## Key features

- **Independent Stage 1 answers** — every council model gets the raw question in parallel, with no visibility into what the others are doing.
- **Anonymous peer review** — responses are relabeled "Response A / B / C…" before any model ranks them, so no model can recognize and favor its own answer or a well-known rival's.
- **Aggregate ranking** — each response's rank position is averaged across every model that successfully evaluated it, surfacing a consensus best-to-worst order alongside the raw per-model rankings.
- **Chairman synthesis** — a dedicated model reads every individual answer and every peer evaluation, then writes one final answer drawing on the strongest ideas from across the council.
- **Graceful degradation** — if some council models fail or time out, the process continues with whatever responses did come back; the whole request only fails if every model fails.
- **Full transparency in the UI** — Stage 1 responses, Stage 2 raw evaluations plus extracted rankings, and the Stage 3 final answer are all inspectable as tabs, not hidden behind the final synthesis.
- **Zero-cost by default** — every council model and the chairman run on OpenRouter's free tier out of the box; no paid API usage required to run the full loop.

## System architecture

```
User Question
   │
   ▼
Stage 1 — Independent Responses (parallel query to every council model)
   │
   ▼
Anonymize  ───►  "Response A", "Response B", "Response C", ...
   │
   ▼
Stage 2 — Peer Review (every council model ranks all anonymized responses)
   │
   ▼
Aggregate Rankings  ───►  avg. position + vote count per response
   │
   ▼
Stage 3 — Chairman Synthesis (reads all responses + all evaluations)
   │
   ▼
Final Answer  ───►  returned with full trace (stage1, stage2, stage3, metadata)
```

De-anonymization for the label → model mapping happens **client-side only, for display** — the models themselves only ever see anonymous labels when producing their rankings.

## Tech stack

| Concern | Choice |
|---|---|
| Backend API | FastAPI |
| Model access | OpenRouter (free-tier models by default: Llama 3.1 8B, Mistral 7B, Gemma 2 9B, Qwen 2.5 7B) |
| Concurrency | `asyncio.gather` for parallel council queries |
| Storage | Per-conversation JSON files — no database required |
| Frontend | React + Vite |
| Markdown rendering | react-markdown |
| Testing | Standalone connectivity script (`test_openrouter.py`) against live OpenRouter models |

## Project structure

```
roundtable/
├── backend/
│   ├── config.py        # council models, chairman model, API key loading
│   ├── openrouter.py     # async OpenRouter client, per-model graceful failure
│   ├── council.py        # stage 1/2/3 logic, ranking parser, aggregation
│   ├── storage.py        # JSON file storage per conversation
│   └── main.py           # FastAPI app + routes
├── frontend/
│   └── src/
│       ├── App.jsx                # orchestration: conversations, sending, metadata
│       ├── api.js                 # fetch wrappers for the backend
│       └── components/
│           ├── Sidebar.jsx         # conversation list
│           ├── ChatInterface.jsx   # input box (Enter to send, Shift+Enter for newline)
│           ├── Stage1.jsx          # tabbed individual responses
│           ├── Stage2.jsx          # tabbed raw evaluations + extracted ranking + aggregate
│           └── Stage3.jsx          # final synthesized answer
├── test_openrouter.py    # sanity-check a model id before adding it to the council
├── .env.example
└── requirements.txt
```

## Getting started

No external services required beyond a free OpenRouter API key.

**1. Backend**

```bash
cd roundtable
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # add your OPENROUTER_API_KEY — free at https://openrouter.ai/keys
python -m backend.main
```

Runs on `http://localhost:8001` (not 8000, to avoid clashing with anything else running locally).

**2. Frontend**

```bash
cd roundtable/frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`.

**3. Sanity-check a model before adding it to the council**

```bash
python test_openrouter.py "meta-llama/llama-3.1-8b-instruct:free"
```

## Notes & recommendations

- **Free models come with real quality and reliability trade-offs.** They're smaller than flagship paid models and OpenRouter's free tier is rate-limited, so expect occasional failed council members — the pipeline is built to tolerate that, not to hide it.
- **Metadata is ephemeral by design.** The label → model mapping and aggregate rankings are returned only in the API response for the message just sent, not persisted to the conversation file — reopening an old conversation still shows Stage 2's raw evaluations, just without the bolded model-name overlay.
- **Anonymization only works if the prompt stays clean.** Stage 2's prompt never includes model names — only "Response A/B/C…" — so keep any future prompt changes to that convention if you want peer review to stay unbiased.
- **Run the backend as a module, not a script.** `python -m backend.main` from the project root, not `python backend/main.py` — the backend's relative imports require it.
- **Fewer council members is a safety valve, not just a cost lever.** Dropping from 4 to 2–3 models reduces both API calls and how often you hit free-tier rate limits at the same time.

## License

Add a license (e.g. MIT or Apache-2.0) before making the repo public if you want to specify how others may use this code.
