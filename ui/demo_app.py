"""Demo visual (Streamlit) — intents 003, 004 e 006.

Shell fino de apresentação + BANCADA DE SIMULAÇÃO da banca: nenhuma
regra de negócio aqui. Monta a rodada via `app.composition` (o MESMO
composition root da CLI) e apresenta o relatório — KPIs, tabela de
segurados monitorados (bairro/cidade, coordenadas, tempo, alerta),
mensagens com o modo exercitado sempre reportado.

Bancada editável (dados fictícios): nome, telefone, CEP, seguros e
cidade por segurado — sempre (ramos exibidos como “residencial”/“auto”
— rótulo de UI; o valor canônico do domínio permanece “residential” —
SEGURO_LABELS/SEGURO_ALIASES); e o TEMPO simulado
(weathercode/precipitação/vento/temperatura/umidade) no modo offline,
com dicionário WMO embutido (expander "Dicionário de weathercodes WMO",
pedido do dono, 2026-09-13 — a banca entende qual código digitar). Umidade
opcional: vazia = desconhecida e as regras que dependem dela (neblina,
tempo seco) pulam, igual ao online. Célula climática vazia assume valor
NEUTRO (weathercode 0, precipitação/vento 0, temperatura 21 °C — nunca
0 °C, que dispararia geada) e linha de segurado sem NOME é excluída da
rodada: a bancada limpa nunca quebra o app (pedido do dono, 2026-09-13).
O alerta é gerado AUTOMATICAMENTE
pelas regras do domínio analisando o tempo informado (o mesmo RiskEngine
da CLI).

CEP → coordenadas: BrasilAPI CEP v2 (`app.adapters.brasil_api`) com
degradação graciosa — CEP sem coordenadas ou falha de rede NÃO quebra a
rodada: usa as coordenadas dos seeds e lista os avisos. A banca NÃO
edita latitude/longitude diretamente (pedido do dono, 2026-09-06).
Ao digitar um CEP válido, o geocode é AUTOMÁTICO: bairro/cidade e o
clima da região aparecem na hora (pedido do dono, 2026-09-06). No
OFFLINE o CEP é apenas RÓTULO (bairro/cidade): a simulação usa sempre
as coordenadas dos seeds, onde as fixtures existem — nunca falha por
CEP novo (pedido do dono, 2026-09-13). O perfil
de litoral NÃO é editável (vem dos seeds — regra da ressaca).

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
from app.domain.weather import (  # noqa: E402
    WMO_SUPPORTED_CODES,
    GeoLocation,
    classify_weathercode,
)
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
    # Bateria preventiva (intent 008).
    "low_humidity": "tempo seco",
    "frost": "geada",
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

# Rótulos de ramo na UI (pedido do dono, 2026-09-13: "residencial" em
# vez de "residential" para a banca). O valor canônico do domínio
# (InsuranceType RESIDENTIAL = "residential") só vive fora da tela.
SEGURO_LABELS: dict[InsuranceType, str] = {
    InsuranceType.RESIDENTIAL: "residencial",
    InsuranceType.AUTO: "auto",
}
# Parse do campo "Seguros": aceita os rótulos da UI e o valor canônico.
SEGURO_ALIASES: dict[str, InsuranceType] = {
    "residencial": InsuranceType.RESIDENTIAL,
    "residential": InsuranceType.RESIDENTIAL,
    "auto": InsuranceType.AUTO,
}

# Dicionário WMO da bancada (pedido do dono, 2026-09-13): derivado do
# domain (`WMO_SUPPORTED_CODES` + `classify_weathercode`) — nenhuma
# classificação duplicada aqui.
WMO_DICT_ROWS = [
    {
        "Código": code,
        "Condição reconhecida": CONDITION_LABELS[
            classify_weathercode(code).value
        ],
    }
    for code in WMO_SUPPORTED_CODES
]

# Receitas de simulação: qual CAMPO dispara qual evento (as regras usam
# as métricas; o weathercode só dispara granizo diretamente).
RECEITA_ROWS = [
    {"Para simular": "Granizo", "Digite": "weathercode 96 ou 99"},
    {
        "Para simular": "Chuva intensa",
        "Digite": "precipitação 10 mm/h (20 = alta, 35 = muito alta)",
    },
    {
        "Para simular": "Tempestade",
        "Digite": "chuva ≥ 30 mm/h + vento ≥ 60 km/h",
    },
    {
        "Para simular": "Vento forte",
        "Digite": "vento ≥ 60 km/h (≥ 80 = muito alta; qualquer região)",
    },
    {
        "Para simular": "Ressaca (litoral)",
        "Digite": "vento ≥ 80 km/h + chuva ≥ 30 mm/h",
    },
    {
        "Para simular": "Calor / onda de calor",
        "Digite": "temperatura 35 °C (38 = onda)",
    },
    {
        "Para simular": "Frio intenso",
        "Digite": "temperatura 10 °C (5 = muito alta)",
    },
    {
        "Para simular": "Geada",
        "Digite": "temperatura 0 °C (−2 = muito alta; neve 71–86 NÃO dispara)",
    },
    {
        "Para simular": "Neblina",
        "Digite": "umidade ≥ 95% + vento ≤ 15 km/h + chuva ≤ 10 mm/h",
    },
    {
        "Para simular": "Tempo seco",
        "Digite": "umidade < 30% (< 20% = moderada)",
    },
]

DATA_DIR = Path("data")

# Valores neutros para células limpas da bancada (célula vazia NUNCA
# quebra a rodada — pedido do dono, 2026-09-13). Temperatura neutra
# escolhida fora dos limiares: nem calor (>=35), nem frio (<=10), nem
# geada (<=0) — 0 °C dispararia geada para todos.
WEATHERCODE_VAZIO = 0.0  # céu limpo
PRECIPITACAO_VAZIA = 0.0  # sem chuva
VENTO_VAZIO = 0.0  # calmaria
TEMPERATURA_VAZIA = 21.0  # neutra (nenhuma regra de temperatura dispara)


def _fixture_key(latitude: float, longitude: float) -> str:
    """Mesma regra de chave do adapter de fixtures (2 casas)."""
    return f"{round(latitude, 2)}|{round(longitude, 2)}"


def _seguros_parse(valor: str) -> frozenset[InsuranceType]:
    """Parse do campo "Seguros" da bancada: rótulos da UI (residencial/
    auto) ou o valor canônico do domínio (residential/auto)."""
    tipos: set[InsuranceType] = set()
    for parte in str(valor).replace(";", ",").split(","):
        tipo = SEGURO_ALIASES.get(parte.strip().lower())
        if tipo is not None:
            tipos.add(tipo)
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
                "seguros": ", ".join(
                    sorted(SEGURO_LABELS[t] for t in h.insurance_types)
                ),
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
                "umidade": snap.get("humidity_pct"),
            }
        )
    return pd.DataFrame(rows)


def _num_or(valor, default: float) -> float:
    """Número da bancada → float; NaN/vazio vira o default neutro do
    campo (célula limpa nunca quebra a rodada nem o preview)."""
    if valor is None or pd.isna(valor):
        return default
    return float(valor)


def _umidade_or_none(valor) -> float | None:
    """Umidade da bancada → float|None (NaN/vazio = desconhecida; as
    regras que dependem dela pulam, mesma degradação do online)."""
    if valor is None or pd.isna(valor):
        return None
    return float(valor)


def _tempo_desc(
    weathercode: int,
    precip: float,
    vento: float,
    temp: float,
    umidade: float | None,
) -> str:
    cond = classify_weathercode(weathercode)
    label = CONDITION_LABELS.get(cond.value, cond.value)
    umid = "umidade n/d" if umidade is None else f"umidade {umidade:.0f}%"
    return (
        f"{label} · {precip:.1f} mm/h · {temp:.0f} °C ·"
        f" vento {vento:.0f} km/h · {umid}"
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
# Assinatura da última rodada disparada (guard de duplo disparo).
st.session_state.setdefault("last_run_signature", None)

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
        help="Criado no @BotFather (/newbot); formato 123456789:ABC..."
        " (sem espaços). Não é persistido — vive só nesta sessão."
        " Alternativa: env TELEGRAM_BOT_TOKEN.",
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
            "Linking Telegram não executado (a bancada segue"
            f" normalmente): {linking[1]} — verifique o token no campo"
            " da sidebar (formato do BotFather: 123456789:ABC...)."
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
        "No offline o TEMPO também é editável — weathercode (dicionário"
        " no expander abaixo), precipitação, vento, temperatura e umidade;"
        " o alerta é gerado automaticamente pelas regras (ex.: weathercode"
        " 96 → granizo; precipitação ≥ 10 mm/h → chuva; vento ≥ 60 km/h)."
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
        "seguros": st.column_config.TextColumn("Seguros (residencial/auto)"),
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
    # Se o usuário acabou de clicar em "Disparar Alertas", NÃO aborta com
    # st.rerun(): o clique seria consumido e a rodada não executaria
    # (bug do "clicou e nada aconteceu", 2026-09-13) — a rodada roda
    # neste ciclo e o editor re-renderiza no próximo ciclo natural.
    st.session_state["bancada_holders_df"] = pd.DataFrame(rows)
    st.session_state["bancada_holders_version"] += 1
    if not rodar:
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
                "Weathercode WMO",
                min_value=0,
                max_value=99,
                step=1,
                help="Código WMO da Open-Meteo. Veja o dicionário "
                "(expander abaixo) — 96/99 = granizo; os demais eventos "
                "usam as colunas ao lado.",
            ),
            "precipitacao": st.column_config.NumberColumn(
                "Precipitação (mm/h)",
                min_value=0.0,
                format="%.1f",
                help="≥ 10 → chuva intensa; ≥ 30 com vento ≥ 60 → tempestade.",
            ),
            "vento": st.column_config.NumberColumn(
                "Vento (km/h)",
                min_value=0.0,
                format="%.1f",
                help="≥ 60 km/h → vento forte (≥ 80 → muito alta; "
                "qualquer região). Ressaca segue só no litoral.",
            ),
            "temperatura": st.column_config.NumberColumn(
                "Temperatura (°C)",
                format="%.1f",
                help="≥ 35 → calor; ≤ 10 → frio; ≤ 0 → geada.",
            ),
            "umidade": st.column_config.NumberColumn(
                "Umidade (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.0f",
                help="Vazio = desconhecida (neblina e tempo seco pulam). "
                "≥ 95% + vento ≤ 15 km/h → neblina; < 30% → tempo seco.",
            ),
        },
        hide_index=True,
    )
    st.session_state["bancada_tempo_df"] = bancada_tempo
    with st.expander(
        "Dicionário de weathercodes WMO (como digitar a simulação)"
    ):
        st.dataframe(WMO_DICT_ROWS, hide_index=True, width="stretch")
        st.caption(
            "Código fora da tabela é classificado como “parcialmente nublado”"
            " (neutro — nenhum alerta). Os demais eventos usam as MÉTRICAS"
            " ao lado do código, não o código em si:"
        )
        st.dataframe(RECEITA_ROWS, hide_index=True, width="stretch")
    tempo_por_id = {
        row["id"]: row for row in bancada_tempo.to_dict("records")
    }
    preview_rows = [
        {
            "Segurado": row["id"],
            "Tempo da região (offline — editável acima)": _tempo_desc(
                int(_num_or(row["weathercode"], WEATHERCODE_VAZIO)),
                _num_or(row["precipitacao"], PRECIPITACAO_VAZIA),
                _num_or(row["vento"], VENTO_VAZIO),
                _num_or(row["temperatura"], TEMPERATURA_VAZIA),
                _umidade_or_none(row["umidade"]),
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
                    snap.humidity_pct,
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

# Guard de duplo disparo (pedido do dono, 2026-09-13): 2 cliques com a
# bancada idêntica NÃO reenviam — o 1º clique executa a rodada (Telegram
# entregue) e o 2º apenas mantém o resultado (antes: 2 rodadas = 2
# mensagens idênticas no Telegram).
rodar_bloqueado = False
if rodar:
    assinatura = repr((
        fonte,
        modo,
        modelo,
        telegram_token or "",
        bancada_holders.to_dict("records"),
        bancada_tempo.to_dict("records") if fonte == FONTE_OFFLINE else None,
    ))
    if assinatura == st.session_state.get("last_run_signature"):
        rodar_bloqueado = True
        st.info(
            "Rodada idêntica à última disparada — nada foi reenviado e o"
            " resultado anterior é mantido abaixo. Edite a bancada (ou o"
            " tempo simulado) para disparar uma nova rodada."
        )
    else:
        st.session_state["last_run_signature"] = assinatura

if rodar and not rodar_bloqueado:
    seeds = {h.id: h for h in load_policy_holders(DATA_DIR / "policy_holders.json")}
    holders_editados: list[PolicyHolder] = []
    for row in bancada_holders.to_dict("records"):
        nome = row["nome"]
        if nome is None or pd.isna(nome) or not str(nome).strip():
            continue  # linha sem nome não é segurado (banca limpou a linha)
        seed = seeds.get(str(row["id"]))
        cep_digitos = "".join(ch for ch in str(row["cep"]) if ch.isdigit())
        location = seed.location if seed is not None else GeoLocation(0.0, 0.0)
        if fonte == FONTE_ONLINE and cep_digitos:
            # No ONLINE a simulação usa as coordenadas do CEP geocodificado.
            # No OFFLINE mantém as dos SEEDS (onde as fixtures existem): o
            # CEP editado serve só ao rótulo do bairro/cidade — mudar o CEP
            # não afeta nem quebra a simulação (pedido do dono, 2026-09-13).
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
                "weathercode": int(
                    _num_or(tempo_por_id[h.id]["weathercode"], WEATHERCODE_VAZIO)
                ),
                "precipitation_mm_h": _num_or(
                    tempo_por_id[h.id]["precipitacao"], PRECIPITACAO_VAZIA
                ),
                "wind_kmh": _num_or(tempo_por_id[h.id]["vento"], VENTO_VAZIO),
                "temperature_c": _num_or(
                    tempo_por_id[h.id]["temperatura"], TEMPERATURA_VAZIA
                ),
                "humidity_pct":
                    _umidade_or_none(tempo_por_id[h.id]["umidade"]),
            }
            for h in holders_editados
            if h.id in tempo_por_id
        }

    with st.spinner(
        "Disparando alertas... (modo LLM: cada mensagem depende do"
        " provedor de IA — pode levar até ~90 s por mensagem quando o"
        " provedor está lento)"
    ):
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
        tempo = _tempo_desc(
            snapshot.weathercode,
            snapshot.precipitation_mm_h,
            snapshot.wind_kmh,
            snapshot.temperature_c,
            snapshot.humidity_pct,
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
    # intent 007: 1 mensagem/envio por segurado (≥2 riscos → consolidada).
    # A severidade do card vem do alerta correspondente no relatório
    # (individual ou resumo MULTIPLE_RISKS, que tem a severidade máxima).
    alert_by_key = {(a.holder_id, a.kind): a for a in report.alerts}
    for message, send in zip(report.messages, report.sends, strict=True):
        alert = alert_by_key[(message.holder_id, message.alert_kind)]
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
