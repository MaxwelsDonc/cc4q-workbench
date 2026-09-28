# Guideline for Labelling Training

This guideline is written by one author (Ph.D. candidate), who has engaged in quantum software engineering for three years, to train other four authors for **labelling quantum-related code comments**. These authors include two master students and two Ph.D. candidates. All of them are familiar with Python language and software development kits, and two have experienced practice in quantum software engineering beyond one year.


To reduce the bias of this guideline, this markdown keeps iterating after the discussion and agreement by all the authors.

## 1. Classification for Quantum-related comment

### 1.1 Target

We label code comments with **"Yes"** or **"No"**, meaning whether one comment is quantum-related or not. This preliminary labelling could help to discover and identify the quantum-specific features demonstrated in the code comments.

### 1.2  Criteria

#### 1.2.1 Keyword-based Method

If the comment involves the word "quantum", this comment would be attributed to **"Yes"** without doubt. 

For other cases in which the word "quantum" is not included, we can consider some keywords related to quantum computing, where we should pay attention to variants from the same root (e.g., "entangled" sourced from "entanglement"):

(1) Specific terms: 

+ Schrodinger
+ Bell state
+ Hamiltonian
+ Toffoli gate
+ Hadamard gate
+ CNOT
+ potential well
+ ground state
+ ground energy
+ wave function / wavefunction
+ Pauli / Pauli matrix
+ clifford
+ collapse
+ pure state
+ mixed state
+ Bloch

(2) Phenomena in quantum mechanics: 

+ superposition
+ entanglement
+ interference
+ decoherence
+ (quantum) tunnelling
(4) Quantum circuit: 

+ qubit / (quantum) bit
+ (quantum) gate
+ (quantum) circuit
+ ansatz / parameterized quantum circuit
+ (quantum) measurement
+ (quantum) noise
+ ancilla (qubit)
+ measurement outcome

(4) Quantum software stack:

+ backend*
+ simulator*
+ QPU
+ QIR
+ HQC (Quantum Credit)

(5) Math in quantum mechanics:

+ commute / anticommute
+ ket / bra / braket
+ Dirac notation
+ dagger
+ rangle / langle (for $\rangle$, $\langle$)
+ observerable
+ statevector

We mark * implicating that the labelling about this keyword depends on specific comment 

#### 1.2.2 Quantum Circuit Diagram

The code comment is quantum-related, when it shows the (part of) quantum circuit diagram. For instance, 

```python
.. parsed-literal::

            q_0: ─────────────────────────■───────── ... ──────────────────────
                                          │
                                          .
                                          │
        q_(n-1): ─────────────────────────┼───────── ... ───────────■──────────
                  ┌────────────┐  ┌───────┴───────┐       ┌─────────┴─────────┐
            q_n: ─┤ RY(offset) ├──┤ RY(2^0 slope) ├  ...  ┤ RY(2^(n-1) slope) ├
                  └────────────┘  └───────────────┘       └───────────────────┘
```

Besides, the following terms are usually quantum-related:

+ depth, layer (relate to quantum circuits）
+ qreg (quantum register) 
+ [q[0]]

#### 1.2.3 Quantum Mapping

The mathematical mapping that depict the qubit evolution or quantum operation    of the quantum circuit corresponding to the quantum algorithm should be quantum-related. For example, 

```python
    .. math::

        |x\rangle_n |0\rangle_m \mapsto |x\rangle_n |(Q(x) + 2^m) \mod 2^m \rangle_m
```

However, we do not take the following separate block as the quantum-related code comment, since it does not offer the entire quantum operation:

```
    .. math::
```

### 1.3 Testing Examples 

| Id     | Code Comment                                                 | Label | Note                                                 |
| ------ | ------------------------------------------------------------ | ----- | ---------------------------------------------------- |
| 5164-1 | ┌──────┐\nq: ┤ P(π) ├\n└──────┘                              | Yes     | It shows the part of quantum circuit diagram (1.2.2) |
| 5158-1 | Z, CZ and CCZ gates.                                         | Yes     | Relate to the quantum circuit (1.2.1 (3))            |
| 3104-1 | Visit this node of the AST, printing it out to the stream in this class instance. | No     | N/A                                                  |
| 1038-1 | Ordered list of original qubits                              | Yes     | Relate to the quantum circuit (1.2.1 (3))            |
| 1035-1 | This code is part of Qiskit.\n\n(C) Copyright IBM 2017, 2018.\n\nThis code is licensed under the Apache License, Version 2.0. You may\nobtain a copy of this license in the LICENSE.txt file in the root directory\nof this source tree or at http://www.apache.org/licenses/LICENSE-2.0.\n\nAny modifications or derivative works of this code must retain this\ncopyright notice, and modified files need to carry a notice indicating\nthat they have been altered from the originals. | No     | This is only the copyright.                          |
| 8925-5 | bool: True if Pauli's anticommute, False if they commute.    | Yes     | Refer to 1.2.1 (5)                                   |
| 3225-3 | dict: A dictionary where the keys are hexadecimal strings in the\n\nformat \"0x1a\" | No     | N/A                                                  |
| 1170-2 | The result is saved in property_set['num_tensor_factors'] as an integer. | No     | N/A                                                  |
|        |                                                              |       |                                                      |

 ### 1.4 Manual Labelling

|The machinery in this module is for defining subclasses of ~.circuit.| False | `~.circuit.` is a specific term |
|Chi matrix|True|The matrix used to describe the quantum channel|
|Sabre|True|An algorithm for quantum compile|