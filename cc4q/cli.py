"""cc4q command line interface.

Standalone-first: every subcommand works on its own (``cc4q <cmd> --help``)
and mirrors the Python API 1:1.
"""

import json
import os
import subprocess
import sys

import typer

app = typer.Typer(name="cc4q",
                  help="Build, inspect, and profile labeled comment corpora "
                       "for Python-based quantum SDKs.",
                  add_completion=False, context_settings={
                      "help_option_names": ["-h", "--help"]})


def _repo_root():
    from cc4q.pipeline.paths import REPO_ROOT
    return REPO_ROOT

def _read_records(path):
    """JSONL or pretty-printed JSON array -> list of records."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text.lstrip().startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@app.command("download-models")
def download_models(check: bool = typer.Option(
        False, "--check", help="verify only; exit 1 if incomplete")):
    """Download/verify the three classifier checkpoints (SHA256-verified)."""
    from cc4q.models.hub import ensure_checkpoints, missing_checkpoints
    if check:
        missing = missing_checkpoints()
        if missing:
            typer.echo(f"MISSING: {', '.join(missing)}")
            raise typer.Exit(1)
        typer.echo("OK: all model checkpoints present.")
        return
    still = ensure_checkpoints()
    if still:
        typer.echo(f"FAILED: still missing {', '.join(still)}")
        raise typer.Exit(1)
    typer.echo("Done — all model checkpoints present.")


@app.command()
def build(repo: str = typer.Option(..., "--repo", help="GitHub URL to clone"),
          ref: str = typer.Option(None, "--ref", help="tag/branch/commit"),
          include_dir: list[str] = typer.Option(
              None, "--include-dir", help="source subdir (repeatable); "
              "default: whole repo"),
          output_dir: str = typer.Option(
              ..., "--output-dir", help="where to put the corpus"),
          clean_mode: str = typer.Option(
              "current_only", "--clean-mode",
              help="current_only / full / none")):
    """Clone a repository and build its labeled comment corpus
    (clone -> extract CCPs -> segment SCCUs)."""
    import shutil
    import tempfile

    from cc4q.pipeline.download import clone_repo
    from cc4q.pipeline.extract import python_extract_comment_pairs
    from cc4q.pipeline.ids import id_generator
    from cc4q.pipeline.segment_pairs import segment_comment_pairs

    workdir = tempfile.mkdtemp(prefix="cc4q_build_")
    try:
        if os.path.isdir(repo):
            # local source directory: no clone needed
            src = os.path.abspath(repo)
            name = os.path.basename(src.rstrip(os.sep))
        else:
            entry = {"url": repo, "ref": ref} if ref else repo
            if not clone_repo(entry, workdir):
                raise typer.Exit(1)
            name = repo.strip().split("/")[-1].replace(".git", "")
            src = os.path.join(workdir, name)

        from cc4q.pipeline.files import get_files_from_dir
        files = get_files_from_dir(src, include_dir or None)
        if not files:
            typer.echo(f"[✗] no .py files found under {src}", err=True)
            raise typer.Exit(1)
        records = []
        id_gen = id_generator()
        for path in files:
            with open(path, encoding="utf-8") as f:
                src_text = f.read()
            records.extend(python_extract_comment_pairs(
                source_code=src_text,
                rel_path=os.path.relpath(path, src), sdk=name,
                id_gen=id_gen, version=ref or "latest",
                host_language="python", clean_mode=clean_mode))
        os.makedirs(output_dir, exist_ok=True)
        pairs_path = os.path.join(output_dir, "comment_pairs.json")
        with open(pairs_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        n = segment_comment_pairs(
            pairs_path, os.path.join(output_dir, "sccus_segmented.json"))
        typer.echo(f"[build] {len(records)} CCPs -> {n} SCCUs in {output_dir}")
        if n <= 0:
            raise typer.Exit(1)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@app.command()
def predict(input_path: str = typer.Option(..., "--input"),
            output_path: str = typer.Option(..., "--output"),
            models_dir: str = typer.Option(None, "--models-dir"),
            device: str = typer.Option(None, "--device"),
            batch: int = typer.Option(32, "--batch")):
    """Label SCCUs (JSONL with comment_text) on the three axes."""
    from cc4q.models.hub import load_models
    from cc4q.predict import predict_corpus

    records = _read_records(input_path)
    models = load_models(model_dir=models_dir, device=device)
    labeled = predict_corpus(records, models=models, batch=batch)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in labeled:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n_q = sum(1 for r in labeled if r["quantum_related"] == 1)
    typer.echo(f"[predict] {len(labeled)} SCCUs labeled, {n_q} quantum")


@app.command()
def sample(input_path: str = typer.Option(..., "--input"),
           output_path: str = typer.Option(..., "--output"),
           by: list[str] = typer.Option(None, "--by",
                                        help="stratify columns (repeatable)"),
           n: int = typer.Option(None, "--n"),
           frac: float = typer.Option(None, "--frac"),
           quotas: str = typer.Option(
               None, "--quotas", help='JSON dict, e.g. {"qiskit": 100}'),
           seed: int = typer.Option(42, "--seed")):
    """Random / stratified / quota sampling over any JSONL."""
    from cc4q.sample import sample as cc4q_sample

    records = _read_records(input_path)
    quota_map = json.loads(quotas) if quotas else None
    drawn = cc4q_sample(records, by=by or None, n=n, frac=frac,
                        quotas=quota_map, seed=seed)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in drawn:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    typer.echo(f"[sample] {len(drawn)} of {len(records)} records")


@app.command()
def annotate(data: str = typer.Option(..., "--data"),
             output_dir: str = typer.Option(..., "--output-dir"),
             schema: str = typer.Option(None, "--schema",
                                        help="YAML/JSON schema file"),
             labels: str = typer.Option("quantum,non-quantum", "--labels"),
             text_column: str = typer.Option("comment_text", "--text-column"),
             id_column: str = typer.Option("id", "--id-column"),
             mode: str = typer.Option("blind", "--mode",
                                      help="blind / adjudicate"),
             predictions: str = typer.Option(
                 None, "--predictions",
                 help="model labels JSONL (adjudicate mode)"),
             dry_run: bool = typer.Option(
                 False, "--dry-run",
                 help="validate inputs and print the plan, do not launch")):
    """Launch the interactive annotation UI (schema-driven, resumable)."""
    import cc4q.annotate as ann

    schema_spec = schema or {"text_column": text_column,
                             "id_column": id_column,
                             "labels": labels.split(",")}
    if dry_run:
        config_path = ann.prepare(data, schema=schema_spec, mode=mode,
                                  model_predictions=predictions,
                                  output_dir=output_dir)
        typer.echo(f"[annotate] dry-run OK; session config: {config_path}")
        return
    ann.annotate(data, schema=schema_spec, mode=mode,
                 model_predictions=predictions, output_dir=output_dir)


@app.command()
def train(task: str = typer.Option(..., "--task",
                                   help="quantum_related / "
                                        "quantum_category / developer_intent"),
          data: str = typer.Option(..., "--data", help="annotated JSONL"),
          output_dir: str = typer.Option(..., "--output-dir"),
          base_model: str = typer.Option("bert-base-uncased", "--base-model"),
          batch_size: int = typer.Option(32, "--batch-size"),
          epochs: int = typer.Option(30, "--epochs"),
          dry_run: bool = typer.Option(
              False, "--dry-run",
              help="validate the data contract only, do not train")):
    """Fine-tune a CC4Q classifier (HF Trainer)."""
    from cc4q import train as cc4q_train

    if dry_run:
        from cc4q.train import TASKS, _validate
        spec = TASKS.get(task)
        if spec is None:
            typer.echo(f"[✗] unknown task {task!r}", err=True)
            raise typer.Exit(1)
        _validate(task, data, spec["text_column"], spec["num_labels"])
        typer.echo(f"[train] dry-run OK: {task} data honors the contract")
        return
    cc4q_train(task, data, output_dir, base_model=base_model,
               batch_size=batch_size, epochs=epochs)
    typer.echo(f"[train] done -> {output_dir}")


@app.command()
def evaluate(annotations: str = typer.Option(..., "--annotations"),
             key: str = typer.Option(..., "--key"),
             id_join: str = typer.Option("no", "--id-join"),
             contaminated: str = typer.Option(
                 None, "--contaminated", help="comma-separated ids to skip")):
    """Human-vs-model agreement (precision/recall/Wilson 95% CI)."""
    from cc4q.evaluate import evaluate_files

    cont = set(contaminated.split(",")) if contaminated else None
    res = evaluate_files(csv_path=annotations,
                         jsonl_path=(None if annotations.endswith(".csv")
                                     else annotations),
                         key_path=key, id_join=id_join, contaminated=cont)
    typer.echo(f"n={res['n']} agreement={100 * res['agreement']:.1f}% "
               f"(95% CI {100 * res['wilson95'][0]:.1f}-"
               f"{100 * res['wilson95'][1]:.1f}) "
               f"precision={100 * res['precision']:.1f}% "
               f"recall={100 * res['recall']:.1f}%")
    for repo, r in res.get("by_repo", {}).items():
        typer.echo(f"  {repo}: n={r['n']} "
                   f"agreement={100 * r['agreement']:.1f}%")


@app.command()
def demo(port: int = typer.Option(8501, "--port")):
    """Launch the CC4Q Workbench Streamlit demo."""
    try:
        from cc4q.app import MAIN_PATH
    except ImportError:
        typer.echo("[✗] the demo needs the app extras: "
                   "pip install 'cc4q[app]'", err=True)
        raise typer.Exit(1)
    raise typer.Exit(subprocess.call(
        [sys.executable, "-m", "streamlit", "run", MAIN_PATH,
         "--server.port", str(port)]))


@app.command()
def serve(host: str = typer.Option("0.0.0.0", "--host"),
          port: int = typer.Option(8501, "--port"),
          headless: bool = typer.Option(True, "--headless/--no-headless")):
    """Serve the demo app like a deployment (headless, bound to host)."""
    from cc4q.app import MAIN_PATH
    cmd = [sys.executable, "-m", "streamlit", "run", MAIN_PATH,
           "--server.address", host, "--server.port", str(port)]
    if headless:
        cmd.append("--server.headless")
        cmd.append("true")
    raise typer.Exit(subprocess.call(cmd))


def main():
    app()


if __name__ == "__main__":
    main()
