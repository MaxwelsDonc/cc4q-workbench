"""Fine-tune the CC4Q classifiers (wraps the HF Trainer logic from
model/<task>/src/01_build_model.py into one entry point).

Data contract (JSONL, one record per line):

    quantum_related    {"comment": str, "label": 0|1, ...}
    quantum_category   {"text": str, "label": 0..5, ...}
    developer_intent   {"text": str, "label": 0..5, ...}
"""

import json
import os

TASKS = {
    "quantum_related": {"text_column": "comment", "num_labels": 2},
    "quantum_category": {"text_column": "text", "num_labels": 6},
    "developer_intent": {"text_column": "text", "num_labels": 6},
}


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
            labels, preds, average=average)
        return {"accuracy": accuracy, "precision": precision,
                "recall": recall, "f1": f1}
    return fn


def train(task, data, output_dir, base_model="bert-base-uncased",
          batch_size=32, epochs=30, max_length=512, test_size=0.2,
          val_size=0.1, seed=42):
    """Fine-tune one CC4Q classifier.

    ``task`` is one of quantum_related / quantum_category /
    developer_intent; ``data`` is a JSONL training file honoring the task
    contract (validated up front with example rows on violation). Splits
    into train/val/test (80/10/10 by default), trains with the HF Trainer
    (best checkpoint by f1), evaluates on the held-out test split, saves the
    final model + tokenizer to ``output_dir``, and returns
    {"trainer": ..., "test_results": {...}, "output_dir": ...}.
    """
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

    tokenizer = BertTokenizer.from_pretrained(base_model)
    model = BertForSequenceClassification.from_pretrained(
        base_model, num_labels=num_labels)

    dataset = load_dataset("json", data_files={"data": data})
    split_dataset = dataset["data"].train_test_split(
        test_size=test_size, seed=seed)
    train_val = split_dataset["train"].train_test_split(
        test_size=val_size, seed=seed)

    def preprocess(examples):
        return tokenizer(examples[text_column], padding="max_length",
                         truncation=True, max_length=max_length)

    tokenized_train = train_val["train"].map(preprocess, batched=True)
    tokenized_val = train_val["test"].map(preprocess, batched=True)
    tokenized_test = split_dataset["test"].map(preprocess, batched=True)

    average = "binary" if num_labels == 2 else "macro"
    training_args = TrainingArguments(
        output_dir=output_dir, eval_strategy="epoch", save_strategy="epoch",
        learning_rate=2e-05, per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size, num_train_epochs=epochs,
        weight_decay=0.01, logging_dir=output_dir, logging_steps=10,
        load_best_model_at_end=True, metric_for_best_model="f1",
        save_total_limit=2, seed=seed)
    trainer = Trainer(model=model, args=training_args,
                      train_dataset=tokenized_train,
                      eval_dataset=tokenized_val,
                      compute_metrics=_compute_metrics(average))
    trainer.train()
    test_results = trainer.evaluate(tokenized_test)
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)
    return {"trainer": trainer, "test_results": test_results,
            "output_dir": output_dir}
