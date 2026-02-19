"""Compatibility entrypoint for Streamlit Cloud.

Streamlit Cloud commonly boots `app.py` by default. We keep this file as a
lightweight shim that delegates to the Streamlit application so deployments do
not fail if Flask is not installed.
"""

from streamlit_app import main


if __name__ == "__main__":
    main()
