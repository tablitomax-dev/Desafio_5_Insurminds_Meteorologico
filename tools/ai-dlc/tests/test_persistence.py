"""TDD — persistência real de auditoria (append em arquivo)."""

from __future__ import annotations

import json
from pathlib import Path

from ai_dlc_orchestrator import run_loop, write_maintenance_entry
from contracts import TaskContext


def _ctx() -> TaskContext:
    return TaskContext(task_id="t1", objective="x", acceptance_criteria=["c1"])


class TestWriteMaintenanceEntry:
    def test_cria_arquivo_com_entrada(self, tmp_path: Path) -> None:
        target = tmp_path / "maintenance-log.md"
        result = run_loop(_ctx(), log_sink=[])
        write_maintenance_entry(target, result)

        text = target.read_text(encoding="utf-8")
        assert "ai-dlc run" in text
        assert "t1" in text
        assert "success" in text

    def test_append_preserva_conteudo_existente(self, tmp_path: Path) -> None:
        target = tmp_path / "maintenance-log.md"
        target.write_text("# Cabeçalho\n", encoding="utf-8")
        result = run_loop(_ctx(), log_sink=[])
        write_maintenance_entry(target, result)
        write_maintenance_entry(target, result)

        text = target.read_text(encoding="utf-8")
        assert text.startswith("# Cabeçalho\n")
        assert text.count("ai-dlc run") == 2

    def test_entrada_registra_iteracoes_e_outcomes(self, tmp_path: Path) -> None:
        target = tmp_path / "maintenance-log.md"
        result = run_loop(_ctx(), log_sink=[])
        write_maintenance_entry(target, result)

        text = target.read_text(encoding="utf-8")
        assert "iterations=3" in text
        assert '"iteration": 3' in text  # records em JSON
        json.loads(text.split("```json\n", 1)[1].split("```", 1)[0])  # JSON válido

    def test_aceita_objeto_path_ou_str(self, tmp_path: Path) -> None:
        result = run_loop(_ctx(), log_sink=[])
        write_maintenance_entry(str(tmp_path / "log.md"), result)
        write_maintenance_entry(tmp_path / "log2.md", result)

    def test_run_com_log_path_persiste(self, tmp_path: Path) -> None:
        target = tmp_path / "maintenance-log.md"
        result = run_loop(_ctx(), log_path=target)
        assert result.status == "success"
        assert "ai-dlc run" in target.read_text(encoding="utf-8")

    def test_erro_de_diretorio_inexistente_propagado(self, tmp_path: Path) -> None:
        import pytest

        result = run_loop(_ctx(), log_sink=[])
        with pytest.raises(OSError):
            write_maintenance_entry(tmp_path / "no-dir" / "log.md", result)
