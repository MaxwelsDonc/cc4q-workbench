Recipes
=======

Model-assisted annotation end to end
------------------------------------

``examples/recipe_model_assisted_annotation.py`` chains the full loop and
makes every step runnable standalone:

.. code-block:: bash

    python examples/recipe_model_assisted_annotation.py build --source-dir examples/test_dir --output-dir out/recipe
    python examples/recipe_model_assisted_annotation.py predict --input out/recipe/sccus.jsonl --output out/recipe/labeled.jsonl
    python examples/recipe_model_assisted_annotation.py sample --input out/recipe/labeled.jsonl --by SDK --n 20 --output out/recipe/sample.jsonl
    python examples/recipe_model_assisted_annotation.py annotate --input out/recipe/sample.jsonl --schema out/recipe/schema.yaml --mode adjudicate --predictions out/recipe/labeled.jsonl --output-dir out/recipe/ann
    python examples/recipe_model_assisted_annotation.py evaluate --annotations out/recipe/ann/annotations.csv --key out/recipe/key.jsonl

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
