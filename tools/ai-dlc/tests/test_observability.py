"""Testes de observabilidade (fase 2): auditoria JSONL + dashboard Flask."""

from __future__ import annotations

import json
from pathlib import Path

from ai_dlc_orchestrator import TaskContext, append_run_jsonl, run_loop
from dashboard import create_app, load_runs

CTX = TaskContext(
    task_id="obs-1",
    objective="objetivo do run",
    acceptance_criteria=["criterio A"],
)


class TestAppendRunJsonl:
    def test_cria_arquivo_com_uma_linha_json_valida(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        result = run_loop(CTX)
        append_run_jsonl(target, result)

        lines = target.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["status"] == result.status
        assert payload["iterations"] == result.iterations
        assert payload["profile"] == result.profile

    def test_dois_runs_duas_linhas(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX))
        append_run_jsonl(target, run_loop(CTX))
        assert len(target.read_text(encoding="utf-8").strip().splitlines()) == 2

    def test_cria_diretorio_pai_quando_ausente(self, tmp_path: Path):
        target = tmp_path / "sub" / "pasta" / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX))
        assert target.exists()


class TestRunLoopAuditPath:
    def test_run_loop_persiste_no_audit_path(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        result = run_loop(CTX, audit_path=target)
        lines = target.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["status"] == result.status

    def test_run_loop_sem_audit_path_nao_cria_arquivo(self, tmp_path: Path):
        run_loop(CTX)
        assert not (tmp_path / "runs.jsonl").exists()


class TestLoadRuns:
    def test_carrega_e_ignora_linhas_corrompidas(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX))
        with target.open("a", encoding="utf-8") as fh:
            fh.write("linha corrompida sem json\n")

        runs = load_runs(target)
        assert len(runs) == 1
        assert runs[0]["task_id"] == "obs-1"

    def test_arquivo_ausente_retorna_lista_vazia(self, tmp_path: Path):
        assert load_runs(tmp_path / "nada.jsonl") == []


class TestDashboard:
    def test_rota_raiz_lista_runs(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX, audit_path=target))
        client = create_app(target).test_client()

        response = client.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "success" in html  # status do run stub (2ª iteração → success)
        assert "obs-1" in html

    def test_rota_raiz_sem_runs(self, tmp_path: Path):
        client = create_app(tmp_path / "vazio.jsonl").test_client()
        response = client.get("/")
        assert response.status_code == 200
        assert "Nenhum run" in response.get_data(as_text=True)

    def test_detalhe_do_run(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX, audit_path=target))
        client = create_app(target).test_client()

        response = client.get("/runs/1")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "code_fast" in html  # perfil do run N1
        assert "criterio A" in html or "stub" in html

    def test_detalhe_de_run_inexistente_e_404(self, tmp_path: Path):
        client = create_app(tmp_path / "vazio.jsonl").test_client()
        assert client.get("/runs/999").status_code == 404

    def test_rota_cost_report(self, tmp_path: Path):
        target = tmp_path / "runs.jsonl"
        append_run_jsonl(target, run_loop(CTX, audit_path=target))
        client = create_app(target).test_client()

        response = client.get("/cost-report")
        assert response.status_code == 200
        assert "TOTAL" in response.get_data(as_text=True)
