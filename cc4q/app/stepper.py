"""Build-space stepper: a 4-step indicator (Get Data -> Label -> Train ->
Evaluate) rendered on every Build page, with the current step highlighted.

Step state lives in ``st.session_state["build_step"]`` (1-based); each step
stashes its output for the next under ``build_*`` session keys.
"""

import streamlit as st

STEPS = ("Get Data", "Label", "Train", "Evaluate")
KEY = "build_step"


def current():
    return st.session_state.get(KEY, 1)


def set_step(n):
    st.session_state[KEY] = n


def render_stepper(active):
    """Render the indicator; returns True when a step jump was requested."""
    set_step(active)
    cols = st.columns(4)
    jumped = False
    for i, (col, name) in enumerate(zip(cols, STEPS, strict=True), 1):
        with col:
            done = i < active
            state = "▶" if i == active else ("✓" if done else f"{i}.")
            kind = "primary" if i == active else "secondary"
            clicked = st.button(f"{state} {name}", key=f"step_{i}",
                                type=kind, use_container_width=True,
                                disabled=i > active)
            if clicked and i != active:
                set_step(i)
                jumped = True
    return jumped


def continue_button(next_step, next_page_file, label=None):
    """Render the 'Continue to …' button; returns True when clicked (the
    caller should switch_page)."""
    nxt = STEPS[next_step - 1]
    return st.button(label or f"Continue to {nxt} →", type="primary",
                     key=f"continue_{next_step}")
