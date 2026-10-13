"""Thin launcher so `streamlit run demo/app.py` keeps working now that the
app lives in the cc4q package (cc4q/app/). Equivalent to `cc4q demo`.
"""

from cc4q.app.main import main

main()
