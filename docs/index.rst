CC4Q documentation
==================

CC4Q turns Python-based quantum SDK repositories into labeled comment
corpora (CCPs -> SCCUs with two-stage Quantum-Specific labels) and
provides quantum-centric analyses of them: **build** a corpus, **inspect**
its quantum density, **profile** its six-category quantum-knowledge
distribution.

The same functionality is available three ways: the Web Workbench
(``cc4q serve`` / ``cc4q demo``), the command line (``cc4q <command>``),
and the Python library (``import cc4q``).

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/predict
   guides/train
   guides/annotate

.. toctree::
   :maxdepth: 2
   :caption: Reference

   data-contracts
   api
   recipes
