Quickstart
==========

Install the library and CLI straight from the repository (Python >= 3.11):

.. code-block:: bash

    pip install git+https://github.com/MaxwelsDonc/cc4q-workbench
    python -m spacy download en_core_web_sm

This installs the ``cc4q`` package and the ``cc4q`` console script. The
three fine-tuned classifiers (about 1.2 GB) are fetched on first use, or
explicitly:

.. code-block:: bash

    cc4q download-models            # download + SHA256-verify + extract
    cc4q download-models --check    # verify only

Build a labeled corpus from any small GitHub repository:

.. code-block:: bash

    cc4q build --repo https://github.com/qiskit-community/qiskit-algorithms \
        --include-dir qiskit_algorithms --output-dir out/algorithms

Then label it, draw a stratified sample, spot-check it in the annotation
UI, and score the agreement:

.. code-block:: bash

    cc4q predict --input out/algorithms/sccus_segmented.json \
        --output out/algorithms/labeled.jsonl
    cc4q sample --input out/algorithms/labeled.jsonl --by SDK --n 200 \
        --output out/algorithms/sample.jsonl
    cc4q annotate --data out/algorithms/sample.jsonl \
        --labels quantum,non-quantum --mode adjudicate \
        --predictions out/algorithms/labeled.jsonl \
        --output-dir out/algorithms/ann
    cc4q evaluate --annotations out/algorithms/ann/annotations.csv \
        --key out/algorithms/key.jsonl

The same steps in Python:

.. code-block:: python

    import cc4q

    models = cc4q.load_models()                      # auto-download once
    labeled = cc4q.predict_corpus("out/algorithms/sccus_segmented.json",
                                  models=models)
    sample = cc4q.sample(labeled, by=["SDK"], n=200, seed=42)
    cc4q.annotate(sample, schema={
        "text_column": "comment_text", "id_column": "id",
        "labels": ["quantum", "non-quantum"]}, mode="adjudicate",
        model_predictions=labeled, output_dir="out/algorithms/ann")
    result = cc4q.evaluate_files(
        csv_path="out/algorithms/ann/annotations.csv",
        key_path="out/algorithms/key.jsonl")
    print(result["agreement"])

To try the full web workbench from a source checkout, see the repository
README (``cc4q serve`` — or ``cc4q demo`` for the same server with the
reviewer quick-start defaults).
