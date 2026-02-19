# ProcessGPT (PythonAnywhere Free Tier)

ProcessGPT is a process-locked RAG assistant for BPO operations.

## Architecture Summary

- **Frontend/App Runtime:** Streamlit (`streamlit_app.py`)
- **Backend Logic:** Python modules for auth/trainer/retrieval
- **Auth:** Session-based, role-based (`agent`, `trainer`) with SQLite in `users/users.db`
- **Storage:** Local filesystem only
- **Retrieval:** Per-process TF-IDF vectors persisted to local files (no vector DB)
- **Isolation:** Every process has independent `raw_docs`, chunks, vectors, and metadata

## Directory Layout

```
processgpt-pythonanywhere/
├── streamlit_app.py
├── app.py                      # Streamlit Cloud compatibility entrypoint
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
├── templates/                  # legacy Flask templates
└── static/                     # legacy Flask styles
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

## Local Run (Streamlit)

> Note: `app.py` is a Streamlit compatibility shim for cloud hosts that default to `app.py`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## PythonAnywhere Deployment (Free Tier)

1. Upload code to your PythonAnywhere home folder.
2. Create a virtualenv and install dependencies from `requirements.txt`.
3. Create a **Manual configuration** web app.
4. Set WSGI to launch Streamlit as your app process (using PythonAnywhere-recommended Streamlit setup).
5. Ensure working directory points to this repo and `streamlit_app.py` is accessible.

## Seed Users

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
