"""Testes da CLI — story 07: `python -m app run [--offline]`."""

import json
from pathlib import Path

from app.cli import main

_SP = {"weathercode": 96, "precipitation_mm_h": 1.0, "wind_kmh": 10.0,
       "temperature_c": 22.0}


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
