"""Fine-tune the CC4Q quantum classifiers (wraps Hugging Face Trainer).

Primary Quantum-Specific Tasks:
    quantum_related    {"comment": str, "label": 0|1, ...}
    quantum_category   {"text": str, "label": 0..5, ...}
"""

import json
import os

TASKS = {
    "quantum_related": {"text_column": "comment", "num_labels": 2},
    "quantum_category": {"text_column": "text", "num_labels": 6},
}

CATEGORY_ORDER = [
    "Mathematics for quantum information",
    "Quantum algorithms",
    "Quantum circuit model",
    "Quantum hardware",
    "Quantum software framework",
    "Others",
]

CATEGORY_ALIASES = {
    "mathematics-for-quantum": 0,
    "mathematics for quantum information": 0,
    "mathematics": 0,
    "math": 0,
    "quantum-algorithm": 1,
    "quantum algorithms": 1,
    "algorithms": 1,
    "algorithm": 1,
    "quantum-circuit-model": 2,
    "quantum circuit model": 2,
    "circuit model": 2,
    "circuit": 2,
    "quantum-hardware": 3,
    "quantum hardware": 3,
    "hardware": 3,
    "quantum-software-stack": 4,
    "quantum software framework": 4,
    "software framework": 4,
    "software stack": 4,
    "quantum-others": 5,
    "others": 5,
    "other": 5,
}


def normalize_training_records(rows, task):
    """Convert flexible annotation/corpus rows into canonical training dicts.

    Accepts rows with ``comment`` / ``text`` / ``comment_text`` and label fields
    in ``label`` / ``human_label`` / ``quantum_related`` / ``quantum_category``.
    Returns a list of ``{text_col: str, "label": int}`` records.
    """
    if task not in TASKS:
        raise ValueError(f"Unknown task {task!r}; expected one of {sorted(TASKS)}")
    spec = TASKS[task]
    text_col = spec["text_column"]
    num_labels = spec["num_labels"]
    out = []

    for i, r in enumerate(rows, 1):
        text = (
            r.get(text_col)
            or r.get("comment_text")
            or r.get("comment")
            or r.get("text")
        )
        if not isinstance(text, str) or not text.strip():
            continue

        raw_label = r.get("label")
        if raw_label is None:
            if task == "quantum_related":
                raw_label = (
                    r.get("human_quantum_related")
                    if "human_quantum_related" in r
                    else r.get("human_label", r.get("quantum_related"))
                )
            elif task == "quantum_category":
                raw_label = (
                    r.get("human_quantum_category")
                    if "human_quantum_category" in r
                    else r.get("human_label", r.get("quantum_category"))
                )

        if raw_label is None:
            continue

        label_int = None
        if task == "quantum_related":
            if isinstance(raw_label, bool):
                label_int = 1 if raw_label else 0
            elif isinstance(raw_label, int) and raw_label in (0, 1):
                label_int = raw_label
            elif isinstance(raw_label, str):
                low = raw_label.strip().lower()
                if low in ("1", "true", "quantum", "quantum-specific", "yes"):
                    label_int = 1
                elif low in ("0", "false", "non-quantum", "not-quantum", "no"):
                    label_int = 0
        elif task == "quantum_category":
            if isinstance(raw_label, int) and not isinstance(raw_label, bool):
                if 0 <= raw_label < num_labels:
                    label_int = raw_label
            elif isinstance(raw_label, str):
                low = raw_label.strip().lower()
                if low.isdigit() and 0 <= int(low) < num_labels:
                    label_int = int(low)
                elif low in CATEGORY_ALIASES:
                    label_int = CATEGORY_ALIASES[low]
                elif raw_label in CATEGORY_ORDER:
                    label_int = CATEGORY_ORDER.index(raw_label)
        else:
            if isinstance(raw_label, int) and not isinstance(raw_label, bool):
                if 0 <= raw_label < num_labels:
                    label_int = raw_label

        if label_int is not None and 0 <= label_int < num_labels:
            out.append({text_col: text.strip(), "label": int(label_int)})

    if not out:
        raise ValueError(
            f"No valid training rows could be extracted for task '{task}'."
        )
    return out


def _validate(task, data_path, text_column, num_labels, preview=5):
    rows = []
    with open(data_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"{data_path}: line {i + 1} is not valid JSON: {e}"
                ) from e
            if len(rows) >= preview:
                break
    if not rows:
        raise ValueError(f"{data_path}: no records found (empty file?)")

    problems = []
    for j, row in enumerate(rows, 1):
        if text_column not in row or not isinstance(row[text_column], str):
            problems.append(f"row {j}: missing string column '{text_column}'")
        label = row.get("label")
        if not isinstance(label, int) or isinstance(label, bool) \
                or not (0 <= label < num_labels):
            problems.append(
                f"row {j}: 'label' must be an int in [0, {num_labels - 1}], "
                f"got {label!r}")
    if problems:
        example = json.dumps(rows[0], ensure_ascii=False)[:300]
        raise ValueError(
            f"Data contract violation for task '{task}' "
            f"(expected '{text_column}' text + int 'label' 0..{num_labels - 1}):\n"
            + "\n".join(f"  - {p}" for p in problems[:5])
            + f"\nExample row: {example}")
    return True


def _compute_metrics(average):
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    def fn(p):
        preds, labels = p
        preds = preds.argmax(axis=1)
        accuracy = accuracy_score(labels, preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average=average, zero_division=0)
        return {"accuracy": float(accuracy), "precision": float(precision),
                "recall": float(recall), "f1": float(f1)}
    return fn


def resolve_base_model(base_model, task):
    """Resolve 'released' alias to the local released checkpoint if available."""
    if base_model in ("released", "cc4q-released", "released-checkpoint"):
        from cc4q.models.hub import checkpoint_complete, default_model_dir
        mdir = default_model_dir()
        if checkpoint_complete(mdir, task):
            return os.path.join(mdir, task)
        return "bert-base-uncased"
    return base_model


def train(task, data, output_dir, base_model="bert-base-uncased",
          batch_size=32, epochs=30, learning_rate=2e-5, max_length=256,
          test_size=0.2, val_size=0.1, seed=42, max_samples=None,
          callbacks=None):
    """Fine-tune one CC4Q classifier (`quantum_related` or `quantum_category`)."""
    if task not in TASKS:
        raise ValueError(
            f"Unknown task {task!r}; expected one of {sorted(TASKS)}")
    spec = TASKS[task]
    text_column = spec["text_column"]
    num_labels = spec["num_labels"]
    _validate(task, data, text_column, num_labels)

    from datasets import load_dataset
    from transformers import (BertForSequenceClassification, BertTokenizer,
                              Trainer, TrainingArguments)

    resolved_base = resolve_base_model(base_model, task)
    tokenizer = BertTokenizer.from_pretrained(resolved_base)
    model = BertForSequenceClassification.from_pretrained(
        resolved_base, num_labels=num_labels, ignore_mismatched_sizes=True)

    dataset = load_dataset("json", data_files={"data": data})["data"]
    if max_samples and len(dataset) > int(max_samples):
        dataset = dataset.shuffle(seed=seed).select(range(int(max_samples)))

    split_dataset = dataset.train_test_split(test_size=test_size, seed=seed)
    train_val = split_dataset["train"].train_test_split(
        test_size=val_size, seed=seed)

    def preprocess(examples):
        return tokenizer(examples[text_column], padding="max_length",
                         truncation=True, max_length=max_length)

    tokenized_train = train_val["train"].map(preprocess, batched=True)
    tokenized_val = train_val["test"].map(preprocess, batched=True)
    tokenized_test = split_dataset["test"].map(preprocess, batched=True)

    average = "binary" if num_labels == 2 else "macro"
    trainer_callbacks = list(callbacks or [])
    training_args = TrainingArguments(
        output_dir=output_dir, eval_strategy="epoch", save_strategy="epoch",
        learning_rate=float(learning_rate),
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        num_train_epochs=epochs,
        weight_decay=0.01, logging_dir=output_dir, logging_steps=2,
        load_best_model_at_end=True, metric_for_best_model="f1",
        save_total_limit=1, seed=seed, report_to="none")
    trainer = Trainer(model=model, args=training_args,
                      train_dataset=tokenized_train,
                      eval_dataset=tokenized_val,
                      compute_metrics=_compute_metrics(average),
                      callbacks=trainer_callbacks or None)
    trainer.train()
    test_results = trainer.evaluate(tokenized_test)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    return {"trainer": trainer, "test_results": test_results,
            "output_dir": output_dir,
            "train_rows": len(tokenized_train),
            "val_rows": len(tokenized_val),
            "test_rows": len(tokenized_test)}
