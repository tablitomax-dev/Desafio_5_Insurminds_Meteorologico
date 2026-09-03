"""Dashboard Flask (fase 2): runs do audit JSONL + cost report.

Uso:
    python dashboard.py [caminho/para/runs.jsonl]
    → http://127.0.0.1:5001

O audit JSONL é gerado por run_loop(audit_path=...) /
append_run_jsonl(). Linhas corrompidas são ignoradas (load_runs).
O arquivo de audit é artefato local — não versionado (.gitignore).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Flask, abort, render_template_string

from contracts import LoopResult
from cost_report import generate_cost_report, report_markdown

DEFAULT_AUDIT_PATH = Path(__file__).resolve().parent / "runs.jsonl"
DEFAULT_PORT = 5001

_LIST_TMPL = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>AI-DLC — runs</title>
<style>body{font-family:system-ui;margin:2rem}table{border-collapse:collapse}
td,th{border:1px solid #ccc;padding:.4rem .8rem;text-align:left}a{color:#0366d6}
code{background:#f5f5f5;padding:.1rem .3rem}</style></head>
<body><h1>AI-DLC — runs</h1>
{% if runs %}
<table><tr><th>#</th><th>task</th><th>status</th><th>nível</th><th>perfil</th><th>iterações</th><th></th></tr>
{% for run in runs %}
<tr><td>{{ loop.index }}</td><td><code>{{ run.task_id or '—' }}</code></td>
<td>{{ run.status }}</td><td>N{{ run.level }}</td><td>{{ run.profile }}</td>
<td>{{ run.iterations }}</td><td><a href="/runs/{{ loop.index }}">detalhe</a></td></tr>
{% endfor %}</table>
{% else %}
<p>Nenhum run registrado no audit ainda.</p>
{% endif %}
<p><a href="/cost-report">Relatório de custo</a></p></body></html>"""

_DETAIL_TMPL = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Run #{{ run_id }}</title>
<style>body{font-family:system-ui;margin:2rem}table{border-collapse:collapse}
td,th{border:1px solid #ccc;padding:.4rem .8rem;text-align:left}a{color:#0366d6}</style></head>
<body><h1>Run #{{ run_id }} — {{ run.task_id or 'sem task_id' }}</h1>
<p>status={{ run.status }} · nível=N{{ run.level }} · perfil={{ run.profile }} ·
iterações={{ run.iterations }} · blocker={{ run.blocker_type or 'none' }}</p>
<table><tr><th>it</th><th>perfil</th><th>resultado</th><th>executor (summary)</th><th>crítico</th><th>bloqueio</th><th>tokens (exec+crítico)</th></tr>
{% for r in run.records %}
<tr><td>{{ r.iteration }}</td><td>{{ r.profile }}</td><td>{{ r.outcome }}</td>
<td>{{ (r.executor.summary or '—')[:120] if r.executor else '—' }}</td>
<td>{{ r.critic.verdict if r.critic else '—' }}</td>
<td>{{ r.capacity.blocker_type if r.capacity and r.capacity.blocker_type else '—' }}</td>
<td>{{ (r.executor.usage.total_tokens if r.executor and r.executor.usage else 0) }}+{{ (r.critic.usage.total_tokens if r.critic and r.critic.usage else 0) }}</td>
</tr>{% endfor %}</table>
<p><a href="/">voltar</a></p></body></html>"""

_COST_TMPL = """<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Relatório de custo</title>
<style>body{font-family:system-ui;margin:2rem}pre{line-height:1.4}a{color:#0366d6}</style></head>
<body><h1>Relatório de custo</h1>
<pre>{{ report }}</pre>
<p><a href="/">voltar</a></p></body></html>"""


def load_runs(path: "str | Path") -> list[dict]:
    """Lê o JSONL de audit ignorando linhas em branco/corrompidas."""
    target = Path(path)
    if not target.exists():
        return []
    runs: list[dict] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # linha corrompida: pula (audit tolerante)
    return runs


def _validated(results: list[dict]) -> list[LoopResult]:
    """Reidrata dicts do JSONL em LoopResult (validação Pydantic)."""
    validated = []
    for item in results:
        try:
            validated.append(LoopResult.model_validate(item))
        except Exception:  # noqa: BLE001 — registro inválido não derruba o dashboard
            continue
    return validated


def create_app(audit_path: "str | Path | None" = None) -> Flask:
    """App factory — usada também nos testes (Flask test_client)."""
    audit = Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH
    app = Flask(__name__)
    app.config["AUDIT_PATH"] = str(audit)

    @app.get("/")
    def index() -> str:
        return render_template_string(_LIST_TMPL, runs=load_runs(audit))

    @app.get("/runs/<int:run_id>")
    def detail(run_id: int) -> str:
        runs = load_runs(audit)
        if run_id < 1 or run_id > len(runs):
            abort(404)
        return render_template_string(_DETAIL_TMPL, run=runs[run_id - 1], run_id=run_id)

    @app.get("/cost-report")
    def cost_report_view() -> str:
        report = generate_cost_report(_validated(load_runs(audit)))
        return render_template_string(_COST_TMPL, report=report_markdown(report))

    return app


if __name__ == "__main__":
    audit = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_AUDIT_PATH)
    application = create_app(audit)
    print(f"audit: {audit}")
    print(f"dashboard: http://127.0.0.1:{DEFAULT_PORT}")
    application.run(host="127.0.0.1", port=DEFAULT_PORT, debug=False)
