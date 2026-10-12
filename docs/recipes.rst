Recipes
=======

Model-assisted annotation end to end
------------------------------------

``examples/recipe_model_assisted_annotation.py`` chains the full loop and
makes every step runnable standalone:

.. code-block:: bash

    python examples/recipe_model_assisted_annotation.py build \
        --source-dir examples/test_dir --output-dir /tmp/recipe
    python examples/recipe_model_assisted_annotation.py predict \
        --input /tmp/recipe/sccus.jsonl --output /tmp/recipe/labeled.jsonl
    python examples/recipe_model_assisted_annotation.py sample \
        --input /tmp/recipe/labeled.jsonl --by SDK --n 20 \
        --output /tmp/recipe/sample.jsonl
    python examples/recipe_model_assisted_annotation.py annotate \
        --input /tmp/recipe/sample.jsonl --schema /tmp/recipe/schema.yaml \
        --mode adjudicate --predictions /tmp/recipe/labeled.jsonl \
        --output-dir /tmp/recipe/ann
    python examples/recipe_model_assisted_annotation.py evaluate \
        --annotations /tmp/recipe/ann/annotations.csv \
        --key /tmp/recipe/key.jsonl

or all at once (``--auto`` confirms every suggestion as a fixture):

.. code-block:: bash

    python examples/recipe_model_assisted_annotation.py run-all --auto

Reproducing the CC4Q spot-check
-------------------------------

.. code-block:: bash

    python examples/recipe_model_assisted_annotation.py walk-spotcheck

replays the paper's 385-item human spot-check through predict -> sample ->
annotate (the recorded human decisions are clicked through the real UI) ->
evaluate, asserting the published 85.0% agreement (n=379).
