# Grounded — ask your documents, see the proof

Upload your documents, ask questions in plain English, and get answers that are
backed by the actual text from those documents — not made up. Every answer comes
with the exact passages it was based on, so you can check the work.

This repository holds **both halves** of the app:

- **`backend/`** — the brains. A Python service that stores your documents, finds
  the most relevant passages for a question, and asks an AI model to write the answer.
- **`frontend/`** — the screen. A React app where you upload files, ask questions,
  and see the answer plus the supporting passages, scores, and timing.

> The frontend folder may be named `frontend/` or `rag-cockpit/` depending on how
> you unzipped it. Wherever it lives, it's the folder that contains `package.json`.

---

## How it works (the 30-second version)

1. You **upload** a document. The app splits it into small passages ("chunks") and
   turns each one into a list of numbers ("an embedding") that captures its meaning.
2. You **ask a question**. The app turns your question into numbers the same way and
   finds the passages whose meaning is closest — and also does a plain keyword match,
   then blends both. This is the "search" step.
3. The best handful of passages are **re-ranked** by a more careful model, and the
   top few are handed to the AI **language model**, which writes an answer using only
   those passages.
4. You get the answer **plus** every passage that was considered, which ones were
   actually used, how well each matched, and how long each step took.

Good to know up front: the AI is told to answer **only** from your documents. If the
relevant text isn't in the passages it received, it will say "I don't have enough
information" on purpose. That's a feature, not a failure — see Troubleshooting.

---

## What you need installed

| Tool | Why | Notes |
|------|-----|-------|
| **Python 3.11+** | runs the backend | `python --version` to check |
| **Node.js 18+** | runs the frontend | `node -v` to check; get the LTS from nodejs.org |
| **Docker Desktop** | runs the database | easiest way to get the special database the app needs |
| **A free Groq API key** | the AI that writes answers | sign up at console.groq.com — takes a minute |

The database isn't a normal one — it needs a vector add-on so it can search by
meaning. The Docker setup below gives you exactly the right version, so you don't
have to configure anything.

You do **not** need an OpenAI key or any paid service. The parts that understand
text run locally on your machine (they download small models the first time).

---

## Setup — Part 1: the backend

All commands below are run from inside the **`backend/`** folder.

### 1. Start the database

```bash
docker compose up -d
```

This starts the database in the background on your machine. The app's default
settings already point at it, so there's nothing to configure. To stop it later:
`docker compose down` (your data is kept). Leave it running while you use the app.

### 2. Install the Python packages

Use a virtual environment so this stays separate from the rest of your system:

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -e .
pip install sentence-transformers
```

That second `pip install` matters: the part of the app that understands text uses a
package called `sentence-transformers` that isn't listed in the project file, so it
has to be installed by hand. It also pulls in a large math library (PyTorch), so this
step can take a few minutes and download a few hundred megabytes. This is normal and
only happens once.

### 3. Add your Groq key

Open **`app/services/llm.py`**. Near the top you'll see a line where the key is blank:

```python
_client = AsyncOpenAI(
    api_key="",                              # <- paste your Groq key here
    base_url="https://api.groq.com/openai/v1"
)
```

Paste your Groq key between the quotes. Without it, uploading and searching will
work, but asking a question will fail at the final "write the answer" step.

### 4. Create the settings file

The backend refuses to start unless one setting is present, even though it's no
longer actually used. Create a file named **`.env`** in the `backend/` folder with:

```
OPENAI_API_KEY=not-used-but-required
```

You can put any text after the `=`. It's a leftover requirement; the app reads it on
startup and won't boot without it.

### 5. Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

The first time you ask a question or upload a file, the app downloads two small
language models (about 80 MB and a similar size). Expect a short pause on the very
first request. After that it's fast.

You'll know it's working when the terminal shows it's running on
`http://localhost:8000`. You can open `http://localhost:8000/health` in a browser —
it should show `{"status":"ok"}`. There's also auto-generated API documentation at
`http://localhost:8000/docs` if you want to poke at it directly.

---

## Setup — Part 2: the frontend

Run these from inside the **frontend** folder (the one with `package.json`).

```bash
npm install

# copy the example settings file:
# Windows:
copy .env.example .env
# macOS / Linux:
cp .env.example .env

npm run dev
```

Then open the address it prints — **`http://localhost:3000`**.

The frontend has to run on **port 3000** specifically. The backend only accepts
requests coming from that exact address (a security setting called CORS). The setup
is already pinned to 3000 and will stop with an error rather than quietly switch to a
different port, so if something else is using 3000, close that first.

The `.env` file tells the frontend where the backend is. The default
(`http://localhost:8000`) matches the backend setup above, so you usually don't need
to change it. If you ever move the backend, update `VITE_API_BASE_URL` in that file
and restart `npm run dev`.

---

## Daily use

You need three things running at once: the database (Docker), the backend
(`uvicorn`), and the frontend (`npm run dev`). Then:

1. Open `http://localhost:3000`.
2. The dot in the top-left should say **"backend online."** If it says offline, the
   backend isn't running or isn't on port 8000.
3. Drop in a PDF, text, or Markdown file from the left panel.
4. Type a question and press Enter.
5. The answer appears with its supporting passages below. Open any passage to read
   the exact text the AI saw. Passages that actually fed the answer are highlighted.

You can drag the **depth** slider to widen the search, and click a document in the
library to limit your question to just that file.

---

## Settings you might want to change

These live in **`backend/app/core/config.py`**. After changing any of them, restart
the backend. A few are worth knowing about:

| Setting | What it controls | Default |
|---------|------------------|---------|
| `rerank_top_n` | how many passages get handed to the AI to write the answer | `3` |
| `top_k` | how many passages the search pulls before narrowing down | `10` |
| `chunk_size` | how big each passage is, in rough word-pieces | `200` |
| `chunk_overlap` | how much neighbouring passages share, to avoid cutting mid-thought | `20` |
| `use_hybrid_search` | blend meaning-search with keyword-search (vs. meaning only) | `true` |
| `use_reranker` | do the careful second-pass ranking (more accurate, a bit slower) | `true` |
| `track_latency` | report how long each step took (powers the timing bar in the UI) | `true` |

If answers feel too stingy, the biggest lever is `rerank_top_n` — raising it to
around 6–8 gives the AI more to work with. Changing `chunk_size` only affects
documents you upload **after** the change, so re-upload older files to feel the
difference.

Note: the database connection details (`database_url`) already match the Docker
setup, so leave that alone unless you're running your own database.

---

## Troubleshooting

**"I don't have enough information in the provided documents."**
This means the passages the AI received didn't clearly contain the answer. Look at
the supporting passages in the UI to find out why:
- If the right passage **isn't listed at all**, the search missed it — try a higher
  depth, or rephrase the question with words closer to the document.
- If it's listed but **not highlighted as used**, it was found but didn't make the
  final cut — raise `rerank_top_n` in the settings.
- If it **is** highlighted as used and the AI still refused, the model was being
  overly cautious — this is common with the small, fast model used by default.

**The status dot says "backend offline."**
The backend isn't running, or it's not on port 8000. Check the backend terminal for
errors, and confirm `http://localhost:8000/health` works in a browser.

**The page won't load / port 3000 error.**
Something else is already using port 3000. Close it, then run `npm run dev` again.

**Uploading a PDF gives an error or finds nothing.**
The backend reads text directly from PDFs; it can't read scanned or photographed
documents (images of text). Use a PDF that has selectable text, or a plain-text file.

**The first question takes a long time.**
The first request downloads the local language models. This happens once. Later
questions are quick.

**Backend won't start, complains about a missing setting.**
You're missing the `.env` file with `OPENAI_API_KEY` in the `backend/` folder. See
backend setup step 4.

---

## A few honest limitations

- Answers come back all at once, not word-by-word, so there's no live "typing" effect.
- There are no user accounts — anyone who can reach the app can use it. Keep it on
  your own machine or a trusted network.
- The default AI model is small and fast, chosen so the app is free to run. For
  better answers you can switch to a larger Groq model in `app/services/llm.py`.
- The database setup here is meant for local development, not production.
