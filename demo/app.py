"""Demo launcher supporting both the new Starlette/Uvicorn Web Workbench
and Streamlit backward compatibility.
"""

import sys

if __name__ == "__main__":
    # If run via `python demo/app.py`, launch the new Starlette Web Workbench
    from cc4q.web.server import run_server
    run_server()
else:
    # If imported or executed inside Streamlit (e.g. streamlit run / AppTest),
    # dispatch to the Streamlit app entrypoint
    try:
        from cc4q.app.main import main
        main()
    except Exception:
        pass
