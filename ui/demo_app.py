"""Demo visual (Streamlit) — intents 003, 004 e 006.

Shell fino de apresentação + BANCADA DE SIMULAÇÃO da banca: nenhuma
regra de negócio aqui. Monta a rodada via `app.composition` (o MESMO
composition root da CLI) e apresenta o relatório — KPIs, tabela de
segurados monitorados (bairro/cidade, coordenadas, tempo, alerta),
mensagens com o modo exercitado sempre reportado.

Bancada editável (dados fictícios): nome, telefone, CEP, seguros e
cidade por segurado — sempre; e o TEMPO simulado
(weathercode/precipitação/vento/temperatura) no modo offline. O alerta
é gerado AUTOMATICAMENTE pelas regras do domínio analisando o tempo
informado (o mesmo RiskEngine da CLI).

CEP → coordenadas: BrasilAPI CEP v2 (`app.adapters.brasil_api`) com
degradação graciosa — CEP sem coordenadas ou falha de rede NÃO quebra a
rodada: usa as coordenadas dos seeds e lista os avisos. A banca NÃO
edita latitude/longitude diretamente (pedido do dono, 2026-09-06).
Ao digitar um CEP válido, o geocode é AUTOMÁTICO: bairro/cidade e o
clima da região aparecem na hora (pedido do dono, 2026-09-06). O perfil
de litoral NÃO é editável (vem dos seeds — regra do vento).

Envio (intents 004/006): SOMENTE Telegram real (o seletor de SMS foi
removido a pedido do dono). O `TelegramSender` resolve o chat_id por
TELEFONE no repositório de vínculos SQLite (`data/telegram_links.db` —
fora do Git; ADR-010): a bancada NÃO tem coluna de chat_id. O token vem
do campo secreto da sidebar (não persiste) ou de TELEGRAM_BOT_TOKEN.
Linking: segurado manda /start no bot → "Vincular contatos" grava no
SQL quem compartilhou o contato e envia o teclado "Compartilhar meu
contato" (`request_contact`) para quem só deu /start — ao tocar no
botão, o próximo clique vincula. Sem token/vínculo o envio vira
"skipped" — nunca quebra a rodada.

Nota de implementação: `data_editor` NÃO aceita valor setado via
`st.session_state` (política do Streamlit); edições ficam no estado do
widget e os dados correntes num df separado (`bancada_*_df`), com keys
dinâmicas por versão — o refresh pós-geocode recria o editor com o df
atualizado, preservando as edições da banca.

Como rodar (na raiz do repo):
    .venv\\Scripts\\streamlit run ui/demo_app.py

O arquivo se chama `demo_app.py` (e não `app.py`) para não sombrear o
pacote `app` do produto no `sys.path`. A demo precisa de `streamlit`
instalado (requirements-ui.txt); o produto (`app/`) segue stdlib-only e
o CI não executa este arquivo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
# streamlit insere o dir do script no sys.path; a raiz precisa vir ANTES
# para o `import app` resolver o pacote do produto (e não algo de ui/).
sys.path.insert(0, str(ROOT))

from app.adapters.brasil_api import BrasilApiGeocoder  # noqa: E402
from app.adapters.catalog import load_policy_holders  # noqa: E402
from app.adapters.llm_messages import DEFAULT_MODEL  # noqa: E402
from app.adapters.open_meteo import OpenMeteoProvider  # noqa: E402
from app.adapters.telegram_api import (  # noqa: E402
    TelegramApiError,
    fetch_recent_contacts,
    send_contact_request,
)
from app.adapters.telegram_links_sqlite import (  # noqa: E402
    SqliteTelegramLinkRepository,
)
from app.composition import run_proactive_round  # noqa: E402
from app.domain.holders import InsuranceType, PolicyHolder  # noqa: E402
from app.domain.ports import GeocodingError, WeatherProviderError  # noqa: E402
from app.domain.weather import GeoLocation, classify_weathercode  # noqa: E402
from app.pipeline import format_report  # noqa: E402

# Defaults da banca (pedido do dono): Online primeiro; LLM primeiro.
FONTE_ONLINE, FONTE_OFFLINE = "Online (Open-Meteo)", "Offline (fixtures)"
FONTES = (FONTE_ONLINE, FONTE_OFFLINE)
MODO_LLM, MODO_TEMPLATE = "LLM (reescrita)", "Template (determinístico)"
MODOS = (MODO_LLM, MODO_TEMPLATE)
EVENT_LABELS = {
    "heavy_rain": "chuva intensa",
    "hail": "granizo",
    "strong_wind": "vento forte",
    # V2 (intent 005).
    "heat": "calor intenso",
    "heat_wave": "onda de calor",
    "extreme_cold": "frio intenso",
    "fog": "neblina",
    "storm": "tempestade",
    "rough_sea": "ressaca",
    "multiple_risks": "múltiplos riscos",
}
CONDITION_LABELS = {
    "clear": "céu limpo",
    "cloudy": "parcialmente nublado",
    "fog": "neblina",
    "drizzle": "garoa",
    "rain": "chuva",
    "heavy_rain": "chuva forte",
    "snow": "neve",
    "hail": "granizo",
    "thunderstorm": "trovoada",
}
SEVERITY_COLOR = {
    "low": "green",
    "medium": "orange",
    "high": "red",
    "very_high": "red",
}

DATA_DIR = Path("data")


def _fixture_key(latitude: float, longitude: float) -> str:
    """Mesma regra de chave do adapter de fixtures (2 casas)."""
    return f"{round(latitude, 2)}|{round(longitude, 2)}"


def _seguros_parse(valor: str) -> frozenset[InsuranceType]:
    tipos: set[InsuranceType] = set()
    for parte in str(valor).replace(";", ",").split(","):
        texto = parte.strip().lower()
        if not texto:
            continue
        try:
            tipos.add(InsuranceType(texto))
        except ValueError:
            continue  # valor inválido digitado pela banca: ignora
    return frozenset(tipos)


def _holders_iniciais() -> pd.DataFrame:
    holders = load_policy_holders(DATA_DIR / "policy_holders.json")
    return pd.DataFrame(
        [
            {
                "id": h.id,
                "nome": h.name,
                "telefone": h.phone,
                "cep": h.cep,
                "seguros": ", ".join(sorted(t.value for t in h.insurance_types)),
                "cidade": h.city,
            }
            for h in holders
        ]
    )


def _tempo_inicial() -> pd.DataFrame:
    """Tempo inicial da bancada: fixtures por segurado (coords dos seeds)."""
    fixtures = json.loads(
        (DATA_DIR / "weather_fixtures.json").read_text(encoding="utf-8")
    )
    rows = []
    for h in load_policy_holders(DATA_DIR / "policy_holders.json"):
        snap = fixtures.get(
            _fixture_key(h.location.latitude, h.location.longitude), {}
        )
        rows.append(
            {
                "id": h.id,
                "weathercode": int(snap.get("weathercode", 0)),
                "precipitacao": float(snap.get("precipitation_mm_h", 0.0)),
                "vento": float(snap.get("wind_kmh", 0.0)),
                "temperatura": float(snap.get("temperature_c", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def _tempo_desc(weathercode: int, precip: float, vento: float, temp: float) -> str:
    cond = classify_weathercode(weathercode)
    label = CONDITION_LABELS.get(cond.value, cond.value)
    return (
        f"{label} · {precip:.1f} mm/h · {temp:.0f} °C · vento {vento:.0f} km/h"
    )


def _vincular_contatos(token: str, links: SqliteTelegramLinkRepository) -> None:
    """Linking telefone → chat_id gravado no SQL (intents 004/006).

    `fetch_recent_contacts` lê o `getUpdates`; quem compartilhou o
    contato é gravado no repositório (upsert por telefone). Quem só
    mandou /start recebe o teclado "Compartilhar meu contato"
    (`request_contact`) — ao tocar, o próximo clique vincula. O
    resultado fica em session_state e é exibido no corpo após o rerun.
    """
    try:
        contatos = fetch_recent_contacts(token)
    except TelegramApiError as exc:
        st.session_state["telegram_linking"] = ("erro", str(exc), [], [])
        st.rerun()
        return
    vinculados: list[str] = []
    pedidos: list[str] = []
    erros: list[str] = []
    for contato in contatos:
        if contato.is_contact_shared:
            links.upsert_link(contato.phone, contato.chat_id, contato.first_name)
            vinculados.append(
                f"{contato.first_name or 'sem nome'}"
                f" (telefone {contato.phone}) → chat {contato.chat_id}"
            )
            continue
        # /start sem contato: pede o contato via teclado do bot.
        try:
            send_contact_request(token, contato.chat_id)
            pedidos.append(
                f"{contato.first_name or 'sem nome'} — chat {contato.chat_id}"
            )
        except TelegramApiError as exc:
            erros.append(f"chat {contato.chat_id}: {exc}")
    st.session_state["telegram_linking"] = ("ok", vinculados, pedidos, erros)
    st.rerun()


st.set_page_config(page_title="Comunicação proativa com o segurado")

st.session_state.setdefault("round_result", None)
st.session_state.setdefault("bancada_reset", 0)
# Dados correntes da bancada (df separado do key do widget — data_editor
# NÃO aceita set via session_state na própria key).
st.session_state.setdefault("bancada_holders_df", _holders_iniciais())
st.session_state.setdefault("bancada_holders_version", 0)
st.session_state.setdefault("bancada_tempo_df", _tempo_inicial())
st.session_state.setdefault("bancada_tempo_version", 0)
# Cache de geocoding CEP → CepLocation|None (None = falhou; degrada).
st.session_state.setdefault("cep_cache", {})
# Preview de clima por segurado (online: Open-Meteo nas coords do CEP).
st.session_state.setdefault("clima_preview", {})
# Resultado do linking Telegram: ("erro", motivo, [], []) ou
# ("ok", vinculados, pedidos_de_contato, erros).
st.session_state.setdefault("telegram_linking", None)

with st.sidebar:
    st.header("Rodada")
    fonte = st.segmented_control(
        "Fonte meteorológica", FONTES, default=FONTE_ONLINE, key="fonte"
    )
    modo = st.segmented_control(
        "Mensagem", MODOS, default=MODO_LLM, key="modo"
    )
    modelo = st.text_input(
        "Modelo pydantic-ai",
        value=DEFAULT_MODEL,
        key="llm_model",
        disabled=(modo != MODO_LLM),
    )
    if modo == MODO_LLM:
        st.caption(
            "Requer OPENROUTER_API_KEY no ambiente. Sem chave, sem rede ou com"
            " erro de API: fallback silencioso para template — o modo"
            " exercitado é sempre reportado."
        )
    st.subheader("Telegram")
    telegram_token = st.text_input(
        "Token do bot (Telegram)",
        type="password",
        key="telegram_token",
        help="Criado no @BotFather (/newbot). Não é persistido — vive"
        " só nesta sessão. Alternativa: env TELEGRAM_BOT_TOKEN.",
    )
    st.caption(
        "O destino é resolvido por TELEFONE no banco de vínculos"
        " (data/telegram_links.db). Peça ao segurado mandar /start no bot;"
        " quem não compartilhar o contato recebe o botão do próprio bot."
    )
    if st.button(
        "Vincular contatos",
        icon=":material/link:",
        width="stretch",
        disabled=not telegram_token,
    ):
        _vincular_contatos(
            telegram_token, SqliteTelegramLinkRepository(DATA_DIR / "telegram_links.db")
        )
    if st.button(
        "Restaurar dados originais",
        icon=":material/restart_alt:",
        width="stretch",
    ):
        # Counter → keys novas → widgets recriados com dados originais.
        st.session_state["bancada_reset"] += 1
        st.session_state["bancada_holders_df"] = _holders_iniciais()
        st.session_state["bancada_tempo_df"] = _tempo_inicial()
        st.session_state["cep_cache"] = {}
        st.session_state["clima_preview"] = {}
        st.session_state["round_result"] = None
        st.rerun()
    rodar = st.button(
        "Disparar Alertas",
        type="primary",
        icon=":material/notifications_active:",
        width="stretch",
    )

st.title("Comunicação proativa com o segurado")
st.caption(
    "Monitoramento meteorológico público → detecção de risco por perfil de"
    " seguro → mensagem preventiva personalizada → envio real via Telegram"
    " (destino resolvido por telefone no banco de vínculos)."
)

# Resultado do linking Telegram — exibido no corpo, após o rerun
# disparado pelo botão da sidebar.
linking = st.session_state.get("telegram_linking")
if linking:
    if linking[0] == "erro":
        st.warning(
            f"Linking Telegram falhou (a bancada segue normalmente):"
            f" {linking[1]}"
        )
    else:
        vinculados, pedidos, erros = linking[1], linking[2], linking[3]
        if vinculados:
            st.success("Vínculos gravados no banco: " + "; ".join(vinculados))
        if pedidos:
            st.info(
                "Pedido de contato enviado pelo bot (toquem no botão"
                " “Compartilhar meu contato” no Telegram e clique em"
                " “Vincular contatos” de novo): " + "; ".join(pedidos)
            )
        if erros:
            st.warning("Falhas ao pedir contato: " + "; ".join(erros))
        if not vinculados and not pedidos and not erros:
            st.info(
                "Nenhum update novo no bot — peça ao segurado mandar /start"
                " no bot e clique novamente."
            )

# --- Bancada de simulação (dados fictícios editáveis pela banca) ---
st.subheader("Bancada de simulação")
st.caption(
    "Edite os segurados (nome, telefone, CEP, seguros) — ao digitar um CEP"
    " válido, o bairro/cidade e o clima da região são trazidos"
    " automaticamente (BrasilAPI + Open-Meteo; requer internet; sem"
    " resolução, usa as coordenadas dos seeds). "
    + (
        "No offline o TEMPO também é editável — o alerta é gerado"
        " automaticamente pelas regras (ex.: weathercode 96 → granizo;"
        " precipitação ≥ 10 mm/h → chuva; vento ≥ 60 km/h no litoral)."
        if fonte == FONTE_OFFLINE
        else "No online o tempo é REAL da Open-Meteo nas coordenadas"
        " resolvidas pelo CEP (sem alerta se o tempo estiver bom)."
    )
)
bancada_holders = st.data_editor(
    st.session_state["bancada_holders_df"],
    key=f"bancada_holders_{st.session_state['bancada_holders_version']}",
    num_rows="fixed",
    width="stretch",
    column_config={
        "id": st.column_config.TextColumn("Id", disabled=True),
        "nome": st.column_config.TextColumn("Nome", required=True),
        "telefone": st.column_config.TextColumn("Telefone"),
        "cep": st.column_config.TextColumn("CEP (00000-000)"),
        "seguros": st.column_config.TextColumn("Seguros (residential/auto)"),
        "cidade": st.column_config.TextColumn("Bairro/cidade"),
    },
    hide_index=True,
)
st.session_state["bancada_holders_df"] = bancada_holders

# --- Geocoding AUTOMÁTICO ao digitar CEP válido (pedido do dono) ---
rows = bancada_holders.to_dict("records")
cache = st.session_state["cep_cache"]
geocoder = BrasilApiGeocoder()
mudou_cidade = False
avisos_geocode: list[str] = []
for row in rows:
    cep_digitos = "".join(ch for ch in str(row["cep"]) if ch.isdigit())
    if len(cep_digitos) != 8 or cep_digitos in cache:
        continue
    try:
        cache[cep_digitos] = geocoder.geocode(cep_digitos)
    except GeocodingError as exc:
        cache[cep_digitos] = None
        avisos_geocode.append(
            f"{row['id']} (CEP {row['cep']}): {exc} — mantendo dados dos seeds"
        )
        continue
    resolved = cache[cep_digitos]
    if resolved.location is None:
        avisos_geocode.append(
            f"{row['id']} (CEP {row['cep']}): BrasilAPI sem coordenadas —"
            " mantendo dados dos seeds"
        )
        continue
    nova_cidade = (
        f"{resolved.bairro}, {resolved.cidade}/{resolved.uf}"
        if resolved.bairro
        else f"{resolved.cidade}/{resolved.uf}"
    )
    if nova_cidade != row["cidade"]:
        row["cidade"] = nova_cidade
        mudou_cidade = True

if mudou_cidade:
    # Recria o editor com o df atualizado (edições da banca preservadas).
    st.session_state["bancada_holders_df"] = pd.DataFrame(rows)
    st.session_state["bancada_holders_version"] += 1
    st.rerun()

if avisos_geocode:
    st.warning(
        "Degradção do geocoding de CEP (a bancada segue normalmente):\n"
        + "\n".join(f"- {a}" for a in avisos_geocode)
    )

# --- Preview do clima da região do CEP (automático, por segurado) ---
weather_snapshots: dict[str, dict[str, float]] | None = None
if fonte == FONTE_OFFLINE:
    bancada_tempo = st.data_editor(
        st.session_state["bancada_tempo_df"],
        key=f"bancada_tempo_{st.session_state['bancada_tempo_version']}",
        num_rows="fixed",
        width="stretch",
        column_config={
            "id": st.column_config.TextColumn("Segurado", disabled=True),
            "weathercode": st.column_config.NumberColumn(
                "Weathercode WMO", min_value=0, max_value=99, step=1
            ),
            "precipitacao": st.column_config.NumberColumn(
                "Precipitação (mm/h)", min_value=0.0, format="%.1f"
            ),
            "vento": st.column_config.NumberColumn(
                "Vento (km/h)", min_value=0.0, format="%.1f"
            ),
            "temperatura": st.column_config.NumberColumn(
                "Temperatura (°C)", format="%.1f"
            ),
        },
        hide_index=True,
    )
    st.session_state["bancada_tempo_df"] = bancada_tempo
    tempo_por_id = {
        row["id"]: row for row in bancada_tempo.to_dict("records")
    }
    preview_rows = [
        {
            "Segurado": row["id"],
            "Tempo da região (offline — editável acima)": _tempo_desc(
                int(row["weathercode"]),
                float(row["precipitacao"]),
                float(row["vento"]),
                float(row["temperatura"]),
            ),
        }
        for row in bancada_tempo.to_dict("records")
    ]
else:
    # Online: clima REAL nas coords de cada CEP resolvido (1 chamada por
    # CEP novo; preview persiste na sessão).
    preview_rows = []
    provider = OpenMeteoProvider()
    for row in rows:
        cep_digitos = "".join(ch for ch in str(row["cep"]) if ch.isdigit())
        resolved = cache.get(cep_digitos)
        if resolved is None or resolved.location is None:
            continue
        location = resolved.location
        desc = st.session_state["clima_preview"].get(row["id"])
        if desc is None:
            try:
                snap = provider.current(location)
            except WeatherProviderError:
                desc = "sem dados do Open-Meteo agora"
            else:
                desc = _tempo_desc(
                    snap.weathercode,
                    snap.precipitation_mm_h,
                    snap.wind_kmh,
                    snap.temperature_c,
                )
            st.session_state["clima_preview"][row["id"]] = desc
        preview_rows.append(
            {
                "Segurado": row["id"],
                "Tempo da região (online — Open-Meteo)": desc,
            }
        )

if preview_rows:
    with st.expander("Clima da região do CEP (preview)", expanded=True):
        st.dataframe(preview_rows, hide_index=True)

if rodar:
    seeds = {h.id: h for h in load_policy_holders(DATA_DIR / "policy_holders.json")}
    holders_editados: list[PolicyHolder] = []
    for row in bancada_holders.to_dict("records"):
        seed = seeds.get(str(row["id"]))
        cep_digitos = "".join(ch for ch in str(row["cep"]) if ch.isdigit())
        location = seed.location if seed is not None else GeoLocation(0.0, 0.0)
        if cep_digitos:
            resolved = cache.get(cep_digitos)
            if resolved is not None and resolved.location is not None:
                location = resolved.location
        holders_editados.append(
            PolicyHolder(
                id=str(row["id"]),
                name=str(row["nome"]),
                phone=str(row["telefone"]),
                location=location,
                insurance_types=_seguros_parse(row["seguros"]),
                is_coastal=(seed.is_coastal if seed is not None else False),
                city=str(row["cidade"]),
            )
        )

    if fonte == FONTE_OFFLINE:
        weather_snapshots = {
            _fixture_key(h.location.latitude, h.location.longitude): {
                "weathercode": float(tempo_por_id[h.id]["weathercode"]),
                "precipitation_mm_h": float(tempo_por_id[h.id]["precipitacao"]),
                "wind_kmh": float(tempo_por_id[h.id]["vento"]),
                "temperature_c": float(tempo_por_id[h.id]["temperatura"]),
            }
            for h in holders_editados
            if h.id in tempo_por_id
        }

    with st.spinner("Disparando alertas..."):
        report, mode = run_proactive_round(
            offline=(fonte == FONTE_OFFLINE),
            llm_model=(modelo if modo == MODO_LLM else None),
            llm_provider=("llm" if modo == MODO_LLM else "template"),
            holders=holders_editados,
            weather_snapshots=weather_snapshots,
            delivery="telegram",
            telegram_token=(telegram_token or None),
            link_repository=SqliteTelegramLinkRepository(
                DATA_DIR / "telegram_links.db"
            ),
        )
    st.session_state.round_result = {
        "report": report,
        "mode": mode,
        "fonte": fonte,
        "holders": {h.id: h for h in holders_editados},
    }

result = st.session_state.round_result
if result is None:
    st.info("Edite a bancada acima (se quiser) e clique em “Disparar Alertas”.")
else:
    report = result["report"]
    mode = result["mode"]
    holders = result["holders"]

    with st.container(horizontal=True):
        st.metric("Segurados consultados", report.holders_consulted, border=True)
        st.metric("Eventos detectados", len(report.alerts), border=True)
        st.metric("Mensagens geradas", len(report.messages), border=True)
        st.metric("Envios despachados", len(report.sends), border=True)
    st.caption(
        f"Fonte: {result['fonte']} — modo de mensagem exercitado: {mode}"
        " — envio: Telegram (real, destino por telefone no banco de vínculos)"
    )

    if report.failures:
        motivos = "\n".join(
            f"- {f.holder_id}: {f.reason}" for f in report.failures
        )
        st.warning(f"Falhas de coleta (a rodada segue com os demais):\n{motivos}")

    alerts_by_holder: dict[str, list] = {}
    for alert in report.alerts:
        alerts_by_holder.setdefault(alert.holder_id, []).append(alert)

    st.subheader("Segurados monitorados")
    rows = []
    for holder_id, snapshot in report.snapshots:
        holder = holders.get(holder_id)
        name = holder.name if holder is not None else holder_id
        city = holder.city if holder is not None else ""
        phone = holder.phone if holder is not None else "—"
        cond = CONDITION_LABELS.get(snapshot.condition.value, snapshot.condition.value)
        tempo = (
            f"{cond} · {snapshot.precipitation_mm_h:.1f} mm/h · "
            f"{snapshot.temperature_c:.0f} °C · vento {snapshot.wind_kmh:.0f} km/h"
        )
        alerta = ", ".join(
            f"{EVENT_LABELS.get(a.kind.value, a.kind.value)} ({a.severity.value})"
            for a in alerts_by_holder.get(holder_id, [])
        )
        rows.append(
            {
                "Segurado": f"{name} ({holder_id})",
                "Telefone": phone,
                "Bairro/cidade": city,
                "Coordenadas": (
                    f"{snapshot.location.latitude:.4f}, "
                    f"{snapshot.location.longitude:.4f}"
                ),
                "Tempo agora": tempo,
                "Alerta gerado": alerta or "— (sem risco)",
            }
        )
    st.dataframe(rows, hide_index=True)

    st.subheader("Alertas de risco")
    if not report.alerts:
        st.info(
            "Nenhum evento de risco nesta rodada — tempo tranquilo para os"
            " segurados consultados."
        )
    else:
        rows = [
            {
                "Segurado": alert.holder_id,
                "Evento": EVENT_LABELS.get(alert.kind.value, alert.kind.value),
                "Severidade": alert.severity.value,
                "Motivo": alert.reason,
            }
            for alert in report.alerts
        ]
        st.dataframe(rows, hide_index=True)

    st.subheader("Mensagens preventivas")
    for alert, message, send in zip(
        report.alerts, report.messages, report.sends, strict=True
    ):
        holder = holders.get(message.holder_id)
        name = holder.name if holder is not None else message.holder_id
        phone = holder.phone if holder is not None else "—"
        cor = SEVERITY_COLOR.get(alert.severity.value, "gray")
        with st.container(border=True):
            st.markdown(
                f"**{name}** ({message.holder_id}) · 📞 {phone} · "
                f"{EVENT_LABELS.get(message.alert_kind.value, message.alert_kind.value)}"
                f" · :{cor}[{alert.severity.value}]"
            )
            with st.chat_message("assistant"):
                st.markdown(message.text)
            caption = (
                f"Envio via {send.channel} (telefone {phone}) — status:"
                f" {send.status}"
            )
            if send.detail:
                caption += f" | {send.detail}"
            st.caption(f"{caption} | {len(message.text)} caracteres")

    with st.expander("Relatório textual (idêntico ao da CLI)"):
        st.code(format_report(report, generator_name=mode), language=None)
