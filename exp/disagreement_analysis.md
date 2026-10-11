# Disagreement analysis: human vs model quantum-axis labels (3 new SDKs)

Sample: 379 author-verified SCCUs (385 sampled per Cochran's formula; 6
calibration items excluded). Disagreements: 57 (32 false positives, 25
false negatives). Overall agreement 85.0% (95% CI 81.0-88.2).

## False-positive patterns (model=quantum, human=non-quantum; 32)

1. **Classical-numerical components of variational workflows** (~13 items): ODE
   solvers (#15, #326), Nelder-Mead (#122), L-BFGS-B (#276), Clopper-Pearson CI
   (#298), Bernoulli perturbation (#315), Sigmoid (#330), stochastic ranking
   (#375), Fisher information (#112, #124), generic optimizer mechanics (#94,
   #23, #240, #269, #307). The classifier over-associates classical numerical
   terms that frequently co-occur with quantum variational algorithms.
2. **"Lattice" polysemy** (~5 items): lattice visualization / data-structure
   comments (#58, #71, #90, #283) where "lattice" denotes a plain graph object,
   not a physics lattice model.
3. **Sphinx directives / module paths** (~3 items): `currentmodule` /
   `autosummary` directives whose module path contains quantum-ish names
   (#265, #348, #385).
4. **Short ambiguous units** (~8 items): e.g. #101 (Gaussian log driver = file
   parser), #134 (sparse conversion), #279 (deprecation TODO), #305 (generic
   math), #150/#151 (borderline domain terms), #51 (tensor symmetry check),
   #106/#153 (probable annotation slips, see below).
5. **Probable annotation slips (human corrected)**: #91 (ANNNI Hamiltonian),
   #106 (qubits/measure), #153 (amplitude estimation) — re-reviewed.

## False-negative patterns (model=non-quantum, human=quantum; 25)

1. **Context-poor short units with specialized abbreviations** (~12 items):
   MP2 (#26), VSCF (#46), FCIDump (#133), "Returns the spin" (#310), "lowest
   eigenstate" (#337), excitations (#163, #217), orbital indices (#328), Route
   lines (#211), Hartree conversion (#257), six-axis states (#243),
   commutator/imaginary phase (#284), +/- operator order (#321).
2. **Engineering comments about quantum primitives** (~7 items): SamplerV2
   counts (#88), fidelity/estimator options (#141), transpiler/ansatz (#145),
   Primitive job (#264), BaseSampler->V2 migration (#287), variational
   principle (#186), time evolution (#203).
3. **Operator-algebra internals** (~5 items): #20 (orbital reordering), #174
   (operator simplification), #208 (dU/dp gradient), #327 (non-commuting
   excitations), #266 (Grover operator reference).

## Implications (for the paper's limitation paragraph)

- Errors are systematic, not random: over-triggering on classical numerical
  components, and missing context-poor domain abbreviations.
- Net effect on corpus statistics roughly cancels (32 FP vs 25 FN on a 50/50
  stratified sample), but the quantum proportion is best read with the
  precision/recall figures (P~78-87%, R~84-89%).
- Both patterns are addressable by fine-tuning on multi-SDK data or adding
  SDK-context features — future work, out of scope for this tool paper.
