"""Page — Home: positioning, numbers, workflow strip, entry points."""

import streamlit as st

from cc4q.app.ui import footer, metric_card  # noqa: E402

GITHUB_URL = "https://github.com/MaxwelsDonc/cc4q-workbench"
PAPER_CITATION = ('"Code Comments for Quantum Software Development Kits: '
                  'An Empirical Study on Qiskit" — ACM Transactions on '
                  'Software Engineering and Methodology (TOSEM), accepted.')
DEMO_VIDEO_URL = "https://github.com/MaxwelsDonc/cc4q-workbench#demo-video"


def render():
    st.markdown(
        """
        <div class="cc4q-hero">
            <h1>From quantum code to labeled<br>comment corpora.</h1>
            <div class="accent-line"></div>
            <p>Build, inspect, profile — CC4Q Workbench turns any
               Python-based quantum SDK repository into a labeled
               code-comment corpus and profiles its quantum knowledge.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4 = st.columns([1, 1, 1, 3])
    with b1:
        st.link_button("GitHub repository", GITHUB_URL, type="secondary",
                       use_container_width=True)
    with b2:
        st.link_button("▶ Demo video (soon)", DEMO_VIDEO_URL,
                       type="secondary", use_container_width=True)
    with b3:
        with st.popover("Companion paper — citation", use_container_width=True):
            st.markdown(PAPER_CITATION)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    ec1, ec2 = st.columns(2)
    import os
    from cc4q.app import PAGES_DIR
    with ec1:
        st.markdown(
            '<div class="cc4q-card"><h3>🔎 Explore the ready-made '
            'corpora</h3><p>Precomputed dashboards for six Qiskit-ecosystem '
            'SDKs, a paste-a-snippet playground, and 17.5k labeled units to '
            'filter and download.</p></div>', unsafe_allow_html=True)
        st.page_link(os.path.join(PAGES_DIR, "p_analyze_repo.py"),
                     label="Open SDK Dashboards →", use_container_width=True)
    with ec2:
        st.markdown(
            '<div class="cc4q-card"><h3>🛠️ Build your own</h3><p>Four '
            'guided steps: get data from any repository, label it with the '
            'models, train your own classifier, and evaluate it.</p></div>',
            unsafe_allow_html=True)
        st.page_link(os.path.join(PAGES_DIR, "p_get_data.py"),
                     label="Start at step 1 · Get Data →",
                     use_container_width=True)

    st.markdown(
        "The pipeline labels every unit on three axes — quantum-relatedness, "
        "quantum category, and developer intent — and the workbench UI "
        "foregrounds the two quantum axes: the binary quantum call and the "
        "six-category quantum-knowledge taxonomy are the protagonists of "
        "every page."
    )

    cols = st.columns(3)
    with cols[0]:
        metric_card("6", "Quantum SDKs in the corpus")
    with cols[1]:
        metric_card("39,593", "Labeled SCCUs")
    with cols[2]:
        metric_card("2", "Quantum label axes per unit")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.subheader("Eight primitives, one workflow")

    entries = [
        ("🛠️ Build", "p_analyze_repo.py", "Analyze Repository",
         "Turn a repository into a labeled comment corpus. Precomputed for "
         "six SDKs; live for any small GitHub repo."),
        ("🔬 Analyze", "p_analyze_repo.py", "Analyze Repository",
         "See how much quantum knowledge a corpus carries and where it "
         "lives — density, heatmaps, profiles."),
        ("🏷️ Predict", "p_analyze_code.py", "Analyze Code",
         "Label every comment unit on the three CC4Q axes, with the "
         "released or your own models."),
        ("🎲 Sample", "p_label.py", "2. Label",
         "Draw a fair subset for human review — random or balanced across "
         "projects and labels."),
        ("✍️ Annotate", "p_label.py", "2. Label",
         "Confirm, fix, or skip model labels in a click-through UI; "
         "exports are train-ready."),
        ("🎓 Train", "p_train.py", "3. Train",
         "Fine-tune a classifier on your annotations, right in the "
         "browser."),
        ("📏 Evaluate", "p_evaluate.py", "4. Evaluate",
         "Score agreement, precision, and recall — against humans or "
         "against the released models."),
        ("📊 Visualize", "p_analyze_repo.py", "Analyze Repository",
         "Radar profiles and quantum-residence heatmaps, exportable "
         "anywhere."),
    ]
    for row_start in (0, 4):
        cols = st.columns(4)
        for col, (title, target, page_name, blurb) in zip(
                cols, entries[row_start:row_start + 4]):
            with col:
                st.markdown(
                    f'<div class="cc4q-card"><h3>{title}</h3>'
                    f'<p>{blurb}</p></div>',
                    unsafe_allow_html=True,
                )
                import os
                from cc4q.app import PAGES_DIR
                st.page_link(os.path.join(PAGES_DIR, target),
                             label=f"Open {page_name} →",
                             use_container_width=True)

    footer()


render()
