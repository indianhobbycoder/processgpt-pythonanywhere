from __future__ import annotations

from pathlib import Path

import streamlit as st

from auth import authenticate, init_user_db
from retriever.router import RAGRouter
from trainer.dashboard import create_process, list_processes
from trainer.rebuild import rebuild_process_knowledge


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_ROOT = BASE_DIR / "knowledge"

init_user_db()
KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
rag_router = RAGRouter(KNOWLEDGE_ROOT)


def _ensure_state() -> None:
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,
        "active_process": None,
        "chat_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _logout() -> None:
    for key in ["authenticated", "username", "role", "active_process", "chat_history"]:
        if key in st.session_state:
            del st.session_state[key]
    _ensure_state()


def _save_uploaded_txt(process_dir: Path, filename: str, data: bytes) -> Path:
    if not filename.lower().endswith(".txt"):
        raise ValueError("Only .txt files are allowed.")

    safe_name = Path(filename).name
    raw_docs_dir = process_dir / "raw_docs"
    raw_docs_dir.mkdir(parents=True, exist_ok=True)

    destination = raw_docs_dir / safe_name
    destination.write_bytes(data)
    return destination


def _login_screen() -> None:
    st.title("ProcessGPT")
    st.caption("Process-locked SOP assistant (Streamlit)")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = authenticate(username, password)
        if user is None:
            st.error("Invalid username or password.")
            return

        st.session_state.authenticated = True
        st.session_state.username = user.username
        st.session_state.role = user.role
        st.session_state.active_process = None
        st.session_state.chat_history = []
        st.success(f"Welcome, {user.username}.")
        st.rerun()

    st.info("Seed users: agent1 / Agent@123, trainer1 / Trainer@123")


def _render_agent_console() -> None:
    st.header("Agent Console")
    st.write(f"Logged in as: **{st.session_state.username}** (agent)")

    processes = list_processes(KNOWLEDGE_ROOT)
    if not processes:
        st.warning("No processes are available. Contact a trainer.")
        return

    if st.session_state.active_process is None:
        selected = st.selectbox("Select process", options=[""] + processes, index=0)
        if st.button("Lock Process", type="primary"):
            if not selected:
                st.error("Please select a process.")
            else:
                st.session_state.active_process = selected
                st.success(f"Process locked to: {selected}")
                st.rerun()
        return

    active_process = st.session_state.active_process
    st.subheader(f"Active Process: {active_process}")
    st.caption("Process is locked for this session. Logout to change process.")

    with st.form("ask_form", clear_on_submit=True):
        question = st.text_area("Ask process question", height=120)
        asked = st.form_submit_button("Submit")

    if asked:
        question = question.strip()
        if not question:
            st.error("Question cannot be empty.")
        else:
            result = rag_router.answer(process_id=active_process, user_question=question, top_k=4)
            st.session_state.chat_history.append(
                {
                    "question": question,
                    "answer": result["answer"],
                    "sources": result.get("sources", []),
                }
            )
            st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.markdown("### Conversation")
    if not st.session_state.chat_history:
        st.caption("No chat yet.")
        return

    for i, item in enumerate(reversed(st.session_state.chat_history), start=1):
        with st.expander(f"Exchange {i}", expanded=(i == 1)):
            st.write(f"**Q:** {item['question']}")
            st.write("**A:**")
            st.text(item["answer"])
            if item["sources"]:
                st.write("**Sources:**")
                for src in item["sources"]:
                    st.write(f"- {src['source']}#{src['chunk_index']} (score={src['score']})")


def _render_trainer_console() -> None:
    st.header("Trainer Dashboard")
    st.write(f"Logged in as: **{st.session_state.username}** (trainer)")

    st.subheader("Create Process")
    with st.form("create_process"):
        process_name = st.text_input("Process name")
        created = st.form_submit_button("Create")
    if created:
        try:
            process_dir = create_process(KNOWLEDGE_ROOT, process_name)
            st.success(f"Process ready: {process_dir.name}")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    processes = list_processes(KNOWLEDGE_ROOT)

    st.subheader("Upload SOP (.txt)")
    upload_process = st.selectbox("Upload target process", options=[""] + processes, key="upload_process")
    uploaded_file = st.file_uploader("Choose .txt SOP file", type=["txt"], key="uploader")
    if st.button("Upload", key="upload_btn"):
        try:
            if not upload_process:
                raise ValueError("Select a process first.")
            if uploaded_file is None:
                raise ValueError("Choose a file to upload.")
            saved = _save_uploaded_txt(KNOWLEDGE_ROOT / upload_process, uploaded_file.name, uploaded_file.getvalue())
            st.success(f"Uploaded {saved.name} to {upload_process}.")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    st.subheader("Rebuild Process Knowledge")
    rebuild_process = st.selectbox("Rebuild target process", options=[""] + processes, key="rebuild_process")
    if st.button("Rebuild", type="primary"):
        try:
            if not rebuild_process:
                raise ValueError("Select a process first.")
            stats = rebuild_process_knowledge(KNOWLEDGE_ROOT / rebuild_process)
            st.success(
                f"Rebuild complete for {stats['process']}: {stats['chunks']} chunks from {stats['documents']} docs."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    st.subheader("Current Processes")
    if processes:
        st.write("\n".join([f"- {p}" for p in processes]))
    else:
        st.caption("No processes found.")


def main() -> None:
    st.set_page_config(page_title="ProcessGPT", page_icon="🧠", layout="wide")
    _ensure_state()

    if not st.session_state.authenticated:
        _login_screen()
        return

    with st.sidebar:
        st.title("ProcessGPT")
        st.write(f"User: **{st.session_state.username}**")
        st.write(f"Role: **{st.session_state.role}**")
        if st.button("Logout"):
            _logout()
            st.rerun()

    if st.session_state.role == "agent":
        _render_agent_console()
    elif st.session_state.role == "trainer":
        _render_trainer_console()
    else:
        st.error("Unknown role configured for this account.")


if __name__ == "__main__":
    main()
