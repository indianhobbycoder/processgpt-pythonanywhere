# ProcessGPT (PythonAnywhere Free Tier)

ProcessGPT is a process-locked RAG assistant for BPO operations.

## Architecture Summary

- **Backend:** Flask (`app.py`)
- **Auth:** Session-based, role-based (`agent`, `trainer`) with SQLite in `users/users.db`
- **Storage:** Local filesystem only
- **Retrieval:** Per-process TF-IDF vectors persisted to local files (no vector DB)
- **Isolation:** Every process has independent `raw_docs`, chunks, vectors, and metadata

## Directory Layout

```
processgpt-pythonanywhere/
├── app.py
├── auth.py
├── requirements.txt
├── users/
│   └── users.db
├── knowledge/
│   ├── smartbuy/
│   │   └── raw_docs/
│   └── concierge/
│       └── raw_docs/
├── trainer/
│   ├── dashboard.py
│   ├── upload.py
│   └── rebuild.py
├── retriever/
│   ├── router.py
│   └── similarity.py
├── templates/
└── static/
```

## Core Flows

### Agent Flow

1. Login as agent
2. Select one process (locked in session)
3. Ask a question
4. Backend rewrites query, retrieves top chunks from selected process only
5. Returns grounded answer from retrieved chunks only
6. If no chunks found, returns "answer not available"

### Trainer Flow

1. Login as trainer
2. Create process
3. Upload `.txt` SOP docs
4. Rebuild process knowledge (chunk + vectorize)

## Local Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5000`.

### Seed Users

- Trainer: `trainer1 / Trainer@123`
- Agent: `agent1 / Agent@123`

## Rebuild Knowledge for Existing Processes

Use Trainer Dashboard action **Rebuild Process Knowledge** after uploading docs.

## Adding More Processes

1. Login as trainer.
2. Create process from dashboard.
3. Upload one or more `.txt` SOP files.
4. Run rebuild for that process.

Each process remains fully isolated at file, chunk, and vector level.
