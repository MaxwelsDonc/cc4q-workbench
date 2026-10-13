"""Page — Your Models: registry of trained/uploaded model packages."""

import os
import tempfile

import streamlit as st

from cc4q.app import registry


def render():
    st.header("Your Models")
    st.write("Models you trained on the Train page or uploaded here. Pick "
             "one as the default prediction model on the Analyze pages; "
             "single-axis packages fall back to the released checkpoints "
             "for the other axes.")

    upload = st.file_uploader("Upload a model zip (HF format; a directory "
                              "per axis: quantum_related, "
                              "quantum_category, developer_intent)",
                              type=["zip"])
    if upload is not None:
        try:
            entry = registry.register_uploaded_zip(upload)
            st.success(f"Registered **{entry['name']}**.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    entries = registry.list_models()
    if not entries:
        st.info("No user models yet — train one on the Train & Evaluate "
                "page or upload a zip above.")
        return

    for entry in entries:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            with c1:
                star = "★ default — " if entry["is_default"] else ""
                st.markdown(f"**{entry['name']}**  \n"
                            f"{star}axes: {', '.join(entry['axes'])} · "
                            f"{entry['source']} · {entry['created']}")
            with c2:
                if not entry["is_default"]:
                    if st.button("Set default", key=f"def_{entry['id']}"):
                        registry.set_default(entry["id"])
                        st.session_state["model_handle_cache"] = {}
                        st.rerun()
            with c3:
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".zip")
                tmp.close()
                registry.zip_package(entry["id"], tmp.name)
                with open(tmp.name, "rb") as f:
                    st.download_button(
                        "Download", data=f.read(),
                        file_name=f"{entry['id']}.zip", type="secondary",
                        key=f"dl_{entry['id']}")
                os.unlink(tmp.name)
            with c4:
                if st.button("Delete", key=f"del_{entry['id']}"):
                    registry.delete(entry["id"])
                    st.session_state["model_handle_cache"] = {}
                    st.rerun()


render()
