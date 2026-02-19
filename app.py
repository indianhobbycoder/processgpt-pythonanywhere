from __future__ import annotations

import os
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from auth import authenticate, init_user_db
from retriever.router import RAGRouter
from trainer.dashboard import create_process, list_processes
from trainer.rebuild import rebuild_process_knowledge
from trainer.upload import save_uploaded_doc


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_ROOT = BASE_DIR / "knowledge"


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

rag_router = RAGRouter(KNOWLEDGE_ROOT)

init_user_db()
KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("You are not authorized for this action.", "error")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "trainer":
        return redirect(url_for("trainer_dashboard"))
    return redirect(url_for("chat"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = authenticate(username, password)
        if user is None:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        session.clear()
        session["username"] = user.username
        session["role"] = user.role
        session["process_id"] = None
        session["chat_history"] = []
        flash(f"Welcome, {user.username}.", "info")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/chat", methods=["GET", "POST"])
@login_required
@role_required("agent")
def chat():
    processes = list_processes(KNOWLEDGE_ROOT)

    if request.method == "POST":
        if "process_id" in request.form and not session.get("process_id"):
            selected = request.form.get("process_id", "").strip().lower()
            if selected not in processes:
                flash("Invalid process selected.", "error")
            else:
                session["process_id"] = selected
                flash(f"Process locked to: {selected}", "info")
            return redirect(url_for("chat"))

        question = request.form.get("question", "").strip()
        process_id = session.get("process_id")
        if not process_id:
            flash("Select a process first.", "error")
            return redirect(url_for("chat"))

        if question:
            result = rag_router.answer(process_id=process_id, user_question=question, top_k=4)
            history = session.get("chat_history", [])
            history.append(
                {
                    "question": question,
                    "answer": result["answer"],
                    "sources": result.get("sources", []),
                }
            )
            session["chat_history"] = history[-10:]

    return render_template(
        "chat.html",
        username=session.get("username"),
        active_process=session.get("process_id"),
        processes=processes,
        chat_history=session.get("chat_history", []),
    )


@app.route("/trainer", methods=["GET", "POST"])
@login_required
@role_required("trainer")
def trainer_dashboard():
    processes = list_processes(KNOWLEDGE_ROOT)

    if request.method == "POST":
        action = request.form.get("action")

        try:
            if action == "create_process":
                process_name = request.form.get("process_name", "")
                created = create_process(KNOWLEDGE_ROOT, process_name)
                flash(f"Process ready: {created.name}", "info")

            elif action == "upload":
                process_id = request.form.get("process_id", "").strip().lower()
                uploaded = request.files.get("document")
                if process_id not in processes:
                    raise ValueError("Invalid process for upload.")
                if uploaded is None:
                    raise ValueError("No document provided.")
                path = save_uploaded_doc(KNOWLEDGE_ROOT / process_id, uploaded)
                flash(f"Uploaded {path.name} to {process_id}.", "info")

            elif action == "rebuild":
                process_id = request.form.get("process_id", "").strip().lower()
                if process_id not in processes:
                    raise ValueError("Invalid process for rebuild.")
                stats = rebuild_process_knowledge(KNOWLEDGE_ROOT / process_id)
                flash(
                    f"Rebuild complete for {stats['process']}: {stats['chunks']} chunks.",
                    "info",
                )

        except Exception as exc:  # noqa: BLE001
            flash(str(exc), "error")

        return redirect(url_for("trainer_dashboard"))

    return render_template(
        "trainer_dashboard.html",
        username=session.get("username"),
        processes=processes,
    )


if __name__ == "__main__":
    app.run(debug=True)
