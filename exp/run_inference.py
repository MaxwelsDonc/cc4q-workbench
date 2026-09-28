"""Three-axis labeling of SCCUs for the CC4Q generalization experiment.

Runs the three release BERT classifiers (checkpoints copied into
models_checkpoints/, originally from the TOSEM release) on the stage-03
segmented outputs of the three new Qiskit-ecosystem repos:

  1. quantum_related  (binary)      -> all SCCUs
  2. quantum_category (6 classes)   -> quantum-related SCCUs only
  3. developer_intent (6 classes)   -> all SCCUs (as in the release workflow)

Writes per-repo labeled JSON (data/output/<repo>/labeled/sccus_labeled.json,
gitignored) and a small summary JSON (exp/labeling_summary.json, committed)
with label counts and wall-clock timings.

Usage (from the workbench root, with .venv activated):
    python exp/run_inference.py
"""

import json
import os
import sys
import time
from collections import Counter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import torch
from transformers import BertForSequenceClassification, BertTokenizer

REPOS = [
    ("qiskit-machine-learning", "0.9.1"),
    ("qiskit-nature", "0.8"),
    ("qiskit-algorithms", "0.4.0"),
]
CLEAN_MODE = "current_only"

CKPT_DIR = os.path.join(PROJECT_ROOT, "models_checkpoints")
QR_DIR = os.path.join(CKPT_DIR, "quantum_related")
QC_DIR = os.path.join(CKPT_DIR, "quantum_category")
DI_DIR = os.path.join(CKPT_DIR, "developer_intent")

INTENT_MAPPING = {0: "What", 1: "How-to-use", 2: "How-it-is-done",
                  3: "Property", 4: "Why", 5: "Others"}
CATEGORY_MAPPING = {0: "Mathematics for quantum information", 1: "Quantum algorithms",
                    2: "Quantum circuit model", 3: "Quantum hardware",
                    4: "Quantum software framework", 5: "Others"}

BATCH_SIZE = 32
MAX_LENGTH = 512


def get_device():
    # CC4Q_DEVICE overrides auto-detection (e.g. CC4Q_DEVICE=cpu).
    # Note: the MPS path hung on this machine (torch 2.14.0), so default to CPU.
    forced = os.environ.get("CC4Q_DEVICE")
    if forced:
        return forced
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_model(model_dir, device):
    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BertForSequenceClassification.from_pretrained(model_dir)
    model.to(device)
    model.eval()
    return tokenizer, model


def predict(model, tokenizer, texts, device, batch_size=BATCH_SIZE):
    all_preds = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        inputs = tokenizer(batch_texts, return_tensors="pt", padding=True,
                           truncation=True, max_length=MAX_LENGTH)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.inference_mode():
            logits = model(**inputs).logits
        all_preds.extend(logits.argmax(dim=1).cpu().tolist())
    return all_preds


def timed_inference(model_dir, items, device, label_key, mapping=None):
    """Run one classifier over items; returns (elapsed_predict_seconds, preds)."""
    t0 = time.perf_counter()
    tokenizer, model = load_model(model_dir, device)
    load_s = time.perf_counter() - t0
    texts = [it["comment_text"] for it in items]
    t1 = time.perf_counter()
    preds = predict(model, tokenizer, texts, device)
    infer_s = time.perf_counter() - t1
    del model
    if device == "mps":
        torch.mps.empty_cache()
    labels = [mapping[p] if mapping else p for p in preds]
    for it, lab in zip(items, labels):
        it[label_key] = lab
    return {"load_s": round(load_s, 2), "infer_s": round(infer_s, 2)}, labels


def main():
    device = get_device()
    print(f"device: {device}")
    summary = {"device": device, "batch_size": BATCH_SIZE, "repos": {}}

    for project, version in REPOS:
        seg_file = os.path.join(
            PROJECT_ROOT, "data", "output", project, "segmented",
            f"comment_pairs_{CLEAN_MODE}_segmented.json")
        with open(seg_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        n_total = len(items)
        print(f"\n=== {project} {version}: {n_total} SCCUs")

        timings = {}

        # Axis 1: quantum-related (binary), all SCCUs
        t, qr_labels = timed_inference(QR_DIR, items, device, "quantum_related")
        timings["quantum_related"] = t
        quantum_items = [it for it in items if it["quantum_related"] == 1]
        n_quantum = len(quantum_items)
        print(f"  quantum_related: {n_quantum}/{n_total} "
              f"({100.0 * n_quantum / n_total:.1f}%) infer={t['infer_s']}s")

        # Axis 2: quantum-category (6 classes), quantum SCCUs only
        t, _ = timed_inference(QC_DIR, quantum_items, device,
                               "quantum_category", CATEGORY_MAPPING)
        timings["quantum_category"] = t
        print(f"  quantum_category: {len(quantum_items)} items infer={t['infer_s']}s")

        # Axis 3: developer-intent (6 classes), all SCCUs
        t, _ = timed_inference(DI_DIR, items, device,
                               "developer_intent", INTENT_MAPPING)
        timings["developer_intent"] = t
        print(f"  developer_intent: {n_total} items infer={t['infer_s']}s")

        labeled_dir = os.path.join(PROJECT_ROOT, "data", "output", project, "labeled")
        os.makedirs(labeled_dir, exist_ok=True)
        with open(os.path.join(labeled_dir, "sccus_labeled.json"), "w",
                  encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

        intent_counts = Counter(it["developer_intent"] for it in items)
        category_counts = Counter(it.get("quantum_category") for it in quantum_items)
        summary["repos"][project] = {
            "version": version,
            "sccus": n_total,
            "quantum_sccus": n_quantum,
            "quantum_proportion": round(n_quantum / n_total, 4),
            "intent_counts": dict(intent_counts),
            "category_counts": dict(category_counts),
            "timings": timings,
        }

    out_path = os.path.join(PROJECT_ROOT, "exp", "labeling_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nsummary written to {out_path}")


if __name__ == "__main__":
    main()
