"""Testes do repositório SQLite de vínculos Telegram — intent 006.

Contrato da port `TelegramLinkRepository` (ADR-010): upsert
idempotente, consulta por telefone normalizado (só dígitos) e None
quando não há vínculo. Banco criado em tmp_path (sem rede, sem
arquivo real do repo).
"""

from app.adapters.telegram_links_sqlite import SqliteTelegramLinkRepository


def test_upsert_e_get_retorna_chat_id(tmp_path):
    """Given vínculo gravado, when consulta pelo telefone, then o
    chat_id gravado."""
    repo = SqliteTelegramLinkRepository(tmp_path / "links.db")
    repo.upsert_link("5511987650001", "5704429924", "Pablo")

    assert repo.get_chat_id_by_phone("5511987650001") == "5704429924"


def test_sem_vinculo_retorna_none(tmp_path):
    """Given telefone sem vínculo, when consulta, then None (envio
    vira skipped no sender)."""
    repo = SqliteTelegramLinkRepository(tmp_path / "links.db")

    assert repo.get_chat_id_by_phone("5511999999999") is None


def test_telefone_formatado_e_normalizado_para_digitos(tmp_path):
    """Given gravação com E.164 e consulta com formatação livre (ou
    vice-versa), when consulta, then o match é pelos dígitos."""
    repo = SqliteTelegramLinkRepository(tmp_path / "links.db")
    repo.upsert_link("+5511960628711", "5704429924")

    assert (
        repo.get_chat_id_by_phone("+55 (11) 96062-8711") == "5704429924"
    )


def test_upsert_atualiza_vinculo_existente(tmp_path):
    """Given novo contato para o MESMO telefone, when upsert, then o
    chat_id antigo é substituído (idempotente)."""
    repo = SqliteTelegramLinkRepository(tmp_path / "links.db")
    repo.upsert_link("5511987650001", "111")
    repo.upsert_link("5511987650001", "222", "Maria")

    assert repo.get_chat_id_by_phone("5511987650001") == "222"


def test_upsert_sem_dados_e_ignorado(tmp_path):
    """Given upsert com telefone ou chat_id vazio, when chamado, then
    nada é gravado (defensivo)."""
    repo = SqliteTelegramLinkRepository(tmp_path / "links.db")
    repo.upsert_link("", "42")
    repo.upsert_link("5511987650001", "")

    assert repo.get_chat_id_by_phone("5511987650001") is None


def test_banco_e_criado_no_path_informado(tmp_path):
    """Given path em diretório novo, when constrói o repo, then o
    arquivo SQLite existe (dir criado)."""
    path = tmp_path / "sub" / "links.db"
    SqliteTelegramLinkRepository(path)

    assert path.exists()
