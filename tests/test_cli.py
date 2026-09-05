"""Testes da CLI — story 07: `python -m app run [--offline]`."""

import json
from pathlib import Path

from app.cli import main

_SP = {"weathercode": 96, "precipitation_mm_h": 1.0, "wind_kmh": 10.0,
       "temperature_c": 22.0}


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output


class _FakeAgent:
    def __init__(self, output: str, error: Exception | None = None) -> None:
        self._output = output
        self._error = error
        self.prompts: list[str] = []

    def run_sync(self, prompt: str, **kwargs: object):  # noqa: ANN201
        self.prompts.append(prompt)
        if self._error is not None:
            raise self._error
        return _FakeResult(self._output)


def _write_data_dir(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "policy_holders.json").write_text(
        json.dumps(
            [
                {
                    "id": "H001",
                    "name": "Maria Silva",
                    "phone": "+5511999990001",
                    "latitude": -23.55,
                    "longitude": -46.63,
                    "insurance_types": ["auto"],
                    "is_coastal": False,
                }
            ]
        ),
        encoding="utf-8",
    )
    (data / "weather_fixtures.json").write_text(
        json.dumps({"-23.55|-46.63": _SP}), encoding="utf-8"
    )
    return data


def test_run_offline_imprime_relatorio_da_rodada(tmp_path, capsys):
    """Given seeds + fixtures em --data, when `run --offline`, then exit 0
    e relatório com 5 seções e envio [SIMULADO]."""
    data = _write_data_dir(tmp_path)

    exit_code = main(["run", "--offline", "--data", str(data)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Segurados consultados" in out
    assert "Eventos detectados" in out
    assert "Alertas por regra" in out
    assert "Mensagens geradas" in out
    assert "Envios simulados" in out
    assert "[SIMULADO]" in out
    assert "H001" in out


def test_run_offline_e_deterministico(tmp_path, capsys):
    """Given a mesma data dir, when duas rodadas offline, then saída
    idêntica (banca vê sempre a mesma demo)."""
    data = _write_data_dir(tmp_path)

    main(["run", "--offline", "--data", str(data)])
    first = capsys.readouterr().out
    main(["run", "--offline", "--data", str(data)])
    second = capsys.readouterr().out

    assert first == second


def test_fixture_versionada_existe_no_repo():
    """Given demo offline da banca, when checa `data/`, then seeds +
    fixtures versionados existem."""
    root = Path(__file__).parent.parent
    assert (root / "data" / "policy_holders.json").exists()
    assert (root / "data" / "weather_fixtures.json").exists()


def test_llm_model_setado_relatorio_reporta_modo_llm(
    tmp_path, capsys, monkeypatch
):
    """Given LLM_MODEL setada (story 06), when rodada offline, then
    mensagem vem do LlmGenerator e o relatório reporta `modo llm`."""
    from app.adapters import llm_messages

    data = _write_data_dir(tmp_path)
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    fake = _FakeAgent("Ola Maria! Granizo previsto. Cubra o carro, por favor.")
    monkeypatch.setattr(
        llm_messages.LlmGenerator, "_create_agent", lambda self: fake
    )

    exit_code = main(["run", "--offline", "--data", str(data)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "(modo llm)" in out
    assert "Granizo previsto. Cubra o carro" in out


def test_llm_provider_template_forca_template_no_relatorio(
    tmp_path, capsys, monkeypatch
):
    """Given LLM_PROVIDER=template, then o relatório fica `modo template`
    mesmo com LLM_MODEL setada."""
    data = _write_data_dir(tmp_path)
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    monkeypatch.setenv("LLM_PROVIDER", "template")

    exit_code = main(["run", "--offline", "--data", str(data)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "(modo template)" in out


def test_llm_erros_caim_em_fallback_e_relatorio_reporta(
    tmp_path, capsys, monkeypatch
):
    """Given LLM quebrada (erro de API), when rodada, then demo segue com
    template (fallback silencioso) e relatório reporta o fallback."""
    from app.adapters import llm_messages

    data = _write_data_dir(tmp_path)
    monkeypatch.setenv("LLM_MODEL", "openrouter:z-ai/glm-5.3-flash")
    monkeypatch.setattr(llm_messages, "RETRY_ATTEMPTS", 2)
    monkeypatch.setattr(llm_messages, "RETRY_DELAY_S", 0.0)
    fake = _FakeAgent("", error=RuntimeError("sem chave"))
    monkeypatch.setattr(
        llm_messages.LlmGenerator, "_create_agent", lambda self: fake
    )

    exit_code = main(["run", "--offline", "--data", str(data)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "fallback: LLM indisponível" in out
    assert "[SIMULADO]" in out  # demo segue até o fim
