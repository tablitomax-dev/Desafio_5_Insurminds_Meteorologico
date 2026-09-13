# -*- coding: utf-8 -*-
"""Gera o relatório técnico em PDF (entregável do curso — Desafio 5 I2A2).

Uso:  .venv\\Scripts\\python docs\\entregaveis\\gerar_relatorio.py
Saída: docs/entregaveis/relatorio-tecnico-desafio5-i2a2.pdf
"""

from __future__ import annotations

import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "relatorio-tecnico-desafio5-i2a2.pdf")

AZUL = colors.HexColor("#1F3864")
AZUL_MEDIO = colors.HexColor("#2E74B5")
AZUL_CLARO = colors.HexColor("#D9E2F3")
CINZA = colors.HexColor("#666666")
LINHA = colors.HexColor("#BFBFBF")
FUNDO_CODE = colors.HexColor("#F2F2F2")
FUNDO_QUOTE = colors.HexColor("#EEF3FA")

# ---------------------------------------------------------------- estilos

ss = getSampleStyleSheet()

BODY = ParagraphStyle(
    "Body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.8,
    leading=14, alignment=TA_JUSTIFY, spaceAfter=6, textColor=colors.black,
)
LEAD = ParagraphStyle(
    "Lead", parent=BODY, fontSize=10.5, leading=15, textColor=colors.HexColor("#333333"),
)
H1 = ParagraphStyle(
    "H1", fontName="Helvetica-Bold", fontSize=15, leading=19,
    textColor=AZUL, spaceBefore=16, spaceAfter=8, keepWithNext=1,
)
H2 = ParagraphStyle(
    "H2", fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=AZUL_MEDIO, spaceBefore=12, spaceAfter=5, keepWithNext=1,
)
BULLET = ParagraphStyle(
    "Bullet", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=3,
)
QUOTE = ParagraphStyle(
    "Quote", parent=BODY, fontName="Helvetica-Oblique", fontSize=9.2,
    leading=13, backColor=FUNDO_QUOTE, borderPadding=6, leftIndent=6,
    rightIndent=6, spaceBefore=4, spaceAfter=8, alignment=TA_LEFT,
)
CODE = ParagraphStyle(
    "Code", parent=BODY, fontName="Courier", fontSize=8.2, leading=11,
    backColor=FUNDO_CODE, borderPadding=5, alignment=TA_LEFT, spaceAfter=8,
)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.6, leading=11.5,
                      alignment=TA_LEFT, spaceAfter=0)
CELL_B = ParagraphStyle("CellB", parent=CELL, fontName="Helvetica-Bold")
CELL_H = ParagraphStyle("CellH", parent=CELL_B, textColor=colors.white)
TITLE = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=26,
                       leading=32, textColor=AZUL, alignment=TA_CENTER)
SUBTITLE = ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=15,
                          leading=20, textColor=AZUL_MEDIO, alignment=TA_CENTER)
CAPA_META = ParagraphStyle("CapaMeta", fontName="Helvetica", fontSize=11,
                           leading=16, textColor=CINZA, alignment=TA_CENTER)

# ---------------------------------------------------------------- helpers

def p(text, style=BODY):
    return Paragraph(text, style)

def bullets(items):
    return [Paragraph(f"<bullet>&bull;</bullet> {t}", BULLET) for t in items]

def table(headers, rows, widths, zebra=True):
    data = [[Paragraph(h, CELL_H) for h in headers]]
    for r in rows:
        data.append([Paragraph(c, CELL) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_MEDIO),
        ("GRID", (0, 0), (-1, -1), 0.5, LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F4F7FB")))
    t.setStyle(TableStyle(style))
    return t

def fit(text):
    """Colunas fixas de tabelas (evita estourar largura útil ~17 cm)."""
    return text


# ---------------------------------------------------------------- doc template

class RelDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            text = flowable.getPlainText()
            level = 0 if flowable.style.name == "H1" else 1
            key = "k" + re.sub(r"\W+", "-", text)[:60]
            self.canv.bookmarkPage(key)
            self.notify("TOCEntry", (level, text, self.page))
            self.canv.addOutlineEntry(text, key, level=level, closed=False)


def rodape(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(LINHA)
    canvas.setLineWidth(0.5)
    canvas.line(2.2 * cm, 1.6 * cm, w - 2.2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 7.8)
    canvas.setFillColor(CINZA)
    canvas.drawString(2.2 * cm, 1.15 * cm,
                      "Relatório Técnico — Desafio 5 I2A2 · Insurminds · Comunicação Proativa com o Segurado")
    canvas.drawRightString(w - 2.2 * cm, 1.15 * cm, f"Página {doc.page}")
    canvas.restoreState()


def capa(canvas, doc):
    pass  # capa sem rodapé


doc = RelDoc(
    OUT,
    pagesize=A4,
    leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    topMargin=2.0 * cm, bottomMargin=2.2 * cm,
    title="Relatório Técnico — Desafio 5 I2A2: Comunicação Proativa com o Segurado",
    author="Grupo Insurminds",
)
w, h = A4
util = w - 4.4 * cm

frame_cover = Frame(2.2 * cm, 2.2 * cm, util, h - 4.4 * cm, id="cover")
frame_body = Frame(2.2 * cm, 2.2 * cm, util, h - 4.2 * cm, id="body")
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[frame_cover], onPage=capa),
    PageTemplate(id="body", frames=[frame_body], onPage=rodape),
])

# ---------------------------------------------------------------- story

S = []
A = S.append

# ============ CAPA ============
A(Spacer(1, 3.2 * cm))
A(p("Desafio 5 — I2A2", ParagraphStyle("pre", parent=CAPA_META, fontSize=13,
     textColor=AZUL_MEDIO, spaceAfter=10)))
A(p("Ferramenta Inteligente para<br/>Comunicação Proativa com o Segurado", TITLE))
A(Spacer(1, 0.8 * cm))
A(p("Relatório Técnico — Entregável do Curso", SUBTITLE))
A(Spacer(1, 1.2 * cm))
A(p("Grupo Insurminds", CAPA_META))
A(p("Setembro de 2026 · Versão 1.0", CAPA_META))
A(Spacer(1, 1.6 * cm))
A(p(
    "Monitoramento meteorológico público, detecção de risco por perfil de seguro, "
    "mensagem preventiva personalizada (template determinístico ou agente LLM) e "
    "entrega real via Telegram, com relatório auditável de cada rodada.",
    ParagraphStyle("capaLead", parent=LEAD, alignment=TA_CENTER, backColor=FUNDO_QUOTE,
                   borderPadding=8, leftIndent=10, rightIndent=10),
))
A(NextPageTemplate("body"))
A(PageBreak())

# ============ SUMÁRIO ============
A(p("Sumário", H1))
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=10.5, leading=16,
                   textColor=AZUL, leftIndent=0),
    ParagraphStyle("toc2", fontName="Helvetica", fontSize=9.5, leading=14,
                   textColor=colors.HexColor("#333333"), leftIndent=14),
]
A(toc)
A(PageBreak())

# ============ 1. SUMÁRIO EXECUTIVO ============
A(p("1. Sumário Executivo", H1))
A(p(
    "A comunicação seguradora–segurado é historicamente <b>reativa</b>: o contato "
    "acontece depois do sinistro. Este projeto inverte a lógica. A ferramenta "
    "consulta continuamente uma fonte meteorológica pública (Open-Meteo, sem custo "
    "nem chave de API), cruza o clima previsto com o perfil de cada segurado "
    "(ramos residencial e/ou auto, região litorânea, coordenadas geocodificadas a "
    "partir do CEP) e <b>antecipa o aviso antes do sinistro</b>, com instruções "
    "práticas e personalizadas — entregues de verdade no Telegram do segurado.",
    LEAD,
))
A(p("Destaques da solução:"))
S.extend(bullets([
    "<b>Pipeline em cinco estágios especializados</b> (coleta, detecção, composição, "
    "vinculação, entrega), cada um isolado por uma port do domínio (arquitetura "
    "Ports &amp; Adapters / DDD), com o <b>agente LLM</b> como compositor das mensagens.",
    "<b>Bateria preventiva</b> Risco × Ramo × Fase (Antes/Durante) derivada de "
    "tabela de negócio aprovada pelo dono, com severidade mapeada nos níveis "
    "INMET/Defesa Civil (amarelo -> preto) e telefones de emergência 199/193/192.",
    "<b>Agente LLM opcional</b> (Pydantic AI + OpenRouter, modelo GLM 5.3 Flash) "
    "que reescreve as mensagens em tom claro, empático e acionável — com fallback "
    "silencioso para template determinístico: sem chave, sem rede ou com a LLM "
    "instável, a demo <b>nunca quebra</b>.",
    "<b>Entrega real via Telegram</b>: vínculo telefone -> chat_id persistido em "
    "SQLite, nascido do consentimento do segurado (compartilhamento de contato no bot).",
    "<b>Qualidade de engenharia</b>: TDD vermelho-verde, 209 testes do produto, "
    "lint (ruff) e tipagem estática (mypy) limpos, CI obrigatório em todo PR, e "
    "documentação viva por AI-DLC (8 intents, 7 ADRs, memory-bank auditável).",
]))
A(p(
    "Toda rodada termina com um <b>relatório em 5 seções</b> (segurados consultados, "
    "eventos detectados, alertas por regra, mensagens geradas com o modo exercitado e "
    "envios despachados), que serve tanto para a banca avaliadora quanto para "
    "operação futura da seguradora.", BODY))

# ============ 2. ARQUITETURA ============
A(p("2. Arquitetura da Solução", H1))
A(p("2.1 Estilo arquitetural", H2))
A(p(
    "A solução é um <b>monolito modular</b> organizado em <b>Ports &amp; Adapters "
    "(arquitetura hexagonal)</b>, com modelagem orientada a <b>DDD</b>. O núcleo "
    "do sistema — regras de risco, entidades e contratos — vive em <b>app/domain</b> "
    "e é <b>100% puro</b>: sem I/O, sem framework, sem dependência externa. Todo "
    "acesso a mundo real (API meteorológica, geocoding, Telegram, LLM, banco de "
    "vínculos) é uma <b>port</b> (interface Python via <i>typing.Protocol</i>) "
    "implementada por um <b>adapter</b> plugável em <b>app/adapters</b>.",
))
A(p(
    "Essa decisão atende diretamente aos critérios de avaliação: permite testar "
    "<b>todas</b> as regras de negócio sem rede (209 testes), substituir fontes e "
    "canais (Open-Meteo real vs. fixtures offline; Telegram real vs. simulação) e "
    "documentar cada fronteira com clareza.",
))
A(p("2.2 Visão geral dos componentes", H2))
A(XPreformatted(
    "Open-Meteo   ----> adapters/open_meteo ---+\n"
    "data/*.json ----> adapters/catalog      ---+-->  pipeline.py (orquestrador da rodada)\n"
    "fixtures  ------> adapters/fixtures      ---+             |\n"
    "                                                          +--> domain/risk      (regras puras)\n"
    "                                                          +--> domain/messages  (template | LLM)\n"
    "                                                          +--> domain/notify    (simulado | Telegram)\n"
    "\n"
    "cli.py (composition root) -------> monta o grafo ports->adapters e executa a rodada\n"
    "ui/demo_app.py (Streamlit) -------> reusa o MESMO composition root",
    CODE,
))

A(p("2.3 Módulos e responsabilidades", H2))
A(table(
    ["Módulo", "Responsabilidade"],
    [
        ["<b>app/domain/</b>", "Núcleo puro e sem I/O: entidades (PolicyHolder, WeatherSnapshot, RiskAlert, "
         "GeneratedMessage, NotificationRecord), 10 regras de risco declarativas, bateria preventiva, "
         "ports (WeatherProvider, PolicyHolderRepository, MessageGenerator, NotificationSender, "
         "TelegramLinkRepository, CepGeocoder, RiskRule) e o motor RiskEngine."],
        ["<b>app/adapters/</b>", "Implementações de mundo real, todas stdlib-only em HTTP: Open-Meteo, "
         "BrasilAPI (CEP -> coordenadas), catálogo em memória com seeds JSON, fixtures offline, "
         "Telegram Bot API + vínculos SQLite, e LlmGenerator (Pydantic AI, import lazy)."],
        ["<b>app/pipeline.py</b>", "Orquestração da rodada em 3 fases (coleta/detecção -> geração paralela -> "
         "envio), com RoundReport e format_report (relatório em 5 seções). Recebe ports prontas — "
         "sem I/O próprio e sem regra de negócio."],
        ["<b>app/composition.py</b>", "Composition root único, compartilhado por CLI e UI: monta o grafo "
         "ports->adapters de cada rodada (fonte meteorológica, gerador de mensagens, canal de envio)."],
        ["<b>app/cli.py</b>", "Interface de linha de comando (modo offline/online, contratos de env)."],
        ["<b>ui/demo_app.py</b>", "Demo visual Streamlit (shell fino): KPIs, tabela de segurados, bancada "
         "de simulação editável e disparo real de alertas. Nenhuma regra de negócio na UI."],
    ],
    [3.4 * cm, util - 3.4 * cm],
))
A(p("2.4 Ports e adapters (seam de substituição)", H2))
A(table(
    ["Port (domínio)", "Implementações (adapters)"],
    [
        ["WeatherProvider", "OpenMeteoProvider (API real) · FixtureWeatherProvider (demo offline determinística)"],
        ["PolicyHolderRepository", "InMemoryPolicyHolderRepository (seeds JSON; bancada editável na UI)"],
        ["CepGeocoder", "BrasilApiGeocoder (CEP v2 -> bairro/cidade/coordenadas, com degradação graciosa)"],
        ["MessageGenerator", "TemplateGenerator (determinístico) · LlmGenerator (Pydantic AI + fallback para o template)"],
        ["NotificationSender", "SimulatedSender (SMS fake da CLI) · TelegramSender (entrega real)"],
        ["TelegramLinkRepository", "SqliteTelegramLinkRepository (vínculo telefone -> chat_id; fora do Git)"],
        ["RiskRule", "10 regras declarativas (HeavyRainRule, HailRule, StrongWindRule, HeatRule, "
         "ExtremeColdRule, FogRule, StormRule, RoughSeaRule, LowHumidityRule, FrostRule)"],
    ],
    [4.6 * cm, util - 4.6 * cm],
))
A(p("2.5 Por que essa arquitetura", H2))
S.extend(bullets([
    "<b>Testabilidade total</b>: o domínio puro permite cobrir regras e entidades sem rede; os adapters "
    "têm dependências HTTP injetáveis (fetch/post falsos), testados com pytest sem chamadas externas.",
    "<b>Substituibilidade</b>: trocar Open-Meteo por outro provedor, Telegram por outro canal ou a LLM "
    "por outro modelo não altera uma linha do domínio — basta outro adapter.",
    "<b>Robustez por design</b>: cada fronteira externa tem timeout, retry e erro de domínio "
    "(WeatherProviderError, GeocodingError, TelegramApiError); falha de entrega nunca quebra a rodada "
    "(degradação graciosa).",
    "<b>Composição explícita</b>: CLI e UI compartilham o mesmo composition root — o comportamento da "
    "demonstração visual é idêntico ao da linha de comando, sem lógica duplicada.",
]))

# ============ 3. AGENTES ============
A(p("3. Agentes Desenvolvidos", H1))
A(p(
    "Em sentido estrito, um <b>agente</b> é um sistema com <b>autonomia de decisão</b>: percebe o contexto, decide como agir (reatividade e proatividade) e coordena-se por mensagens (Wooldridge &amp; Jennings). Sob esse critério, a solução tem <b>um agente</b> — o <b>agente LLM (IA generativa)</b> — coordenado por um <b>orquestrador de pipeline</b> e apoiado por <b>cinco serviços especializados</b>. Cada componente é encapsulado por uma port do domínio, tem responsabilidade única e falha degradada (nunca derruba a rodada).", LEAD))
A(table(
    ["Componente", "Papel no pipeline", "Entrada / Saída"],
    [
        ["<b>Serviço 1. Coletor meteorológico</b><br/>(OpenMeteoProvider / FixtureWeatherProvider)",
         "Consulta o clima atual de cada segurado (lat/lon a 4 casas) na API Open-Meteo; "
         "no modo offline usa fixtures versionadas. Timeout 10 s + 2 retries; erro vira "
         "WeatherProviderError e o segurado é registrado como falha de coleta sem interromper os demais.",
         "GeoLocation -> WeatherSnapshot (weathercode WMO, precipitação mm/h, vento km/h, temperatura °C, umidade %)"],
        ["<b>Serviço 2. Motor de detecção de risco</b><br/>(RiskEngine + 10 regras)",
         "Avalia o snapshot contra o perfil do segurado (ramos contratados; "
         "litoral só para ressaca). "
         "Regras puras e declarativas, com limiares escalonáveis e dedup por (segurado, risco); "
         "com 2+ riscos simultâneos emite um resumo MULTIPLE_RISKS (severidade máxima).",
         "WeatherSnapshot + PolicyHolder -> list[RiskAlert] (tipo, severidade, motivo)"],
        ["<b>Serviço 3. Compositor de mensagens</b><br/>(TemplateGenerator / LlmGenerator)",
         "Transforma os alertas em aviso preventivo personalizado, alimentado pela bateria "
         "Risco × Ramo × Fase: nível INMET na abertura, precauções só dos ramos contratados, "
         "fases pela severidade, telefones em laranja+, limite de 600 caracteres.",
         "PolicyHolder + RiskAlert(s) -> GeneratedMessage (texto pronto para envio)"],
        ["<b>Serviço 4. Despachante de comunicação</b><br/>(TelegramSender / SimulatedSender)",
         "Entrega a mensagem no canal escolhido. Telegram real resolve o chat_id por telefone "
         "no repositório de vínculos; sem token ou sem vínculo o envio vira “skipped” com o "
         "motivo — e a rodada segue intacta.",
         "PolicyHolder + GeneratedMessage -> NotificationRecord (sent/failed/skipped + detalhe)"],
        ["<b>Serviço 5. Gestor de vínculos</b><br/>(SqliteTelegramLinkRepository + linking)",
         "Mantém o vínculo consentido telefone -> chat_id em SQLite: lê contatos recentes do bot "
         "(getUpdates), envia o teclado “Compartilhar meu contato” (request_contact) para quem "
         "só deu /start e persiste o vínculo (FORA do Git, ADR-010).",
         "getUpdates -> TelegramContact; telefone -> chat_id"],
        ["<b>Agente LLM (IA generativa)</b><br/>(LlmGenerator + Pydantic AI)",
         "Reescreve o aviso do template em linguagem natural de alta qualidade. Detalhado na "
         "seção 3.1 — inclusive as salvaguardas que impedem a LLM de violar as regras de negócio.",
         "prompt estruturado -> texto final (<= 600 caracteres)"],
    ],
    [4.4 * cm, 7.2 * cm, util - 11.6 * cm],
))
A(p("3.1 O agente LLM em detalhe", H2))
A(p(
    "O compositor tem duas implementações intercambiáveis. O <b>TemplateGenerator</b> "
    "é determinístico (f-strings, CPU puro, milissegundos) e garante o piso de qualidade. "
    "O <b>LlmGenerator</b> eleva a naturalidade: monta um <b>prompt estruturado</b> com "
    "(a) regras de tom (claro, empático, acionável, pronto para SMS/push), (b) as 6 regras "
    "transversais do negócio, (c) as células da bateria do risco para os ramos contratados "
    "(impactos + precauções por fase), (d) o nível INMET com ação e janela temporal e "
    "(e) os telefones de emergência quando o nível permite. A LLM recebe exatamente as "
    "mesmas células que o template usa — <b>consistência garantida entre os dois caminhos</b>.",
))
A(p("Salvaguardas do agente LLM:"))
S.extend(bullets([
    "<b>Autonomia (por que é um agente)</b>: dado o prompt, o agente LLM decide a "
    "forma final do texto por raciocínio próprio — não é um transformador "
    "determinístico; o loop de tentativas e o fallback dão o controle agêntico.",
    "<b>Fallback silencioso</b>: env ausente, SDK ausente, erro de API ou resposta vazia -> "
    "o TemplateGenerator assume e a mensagem sai do mesmo jeito; o modo exercitado "
    "(template / llm / híbrido) é sempre reportado.",
    "<b>Timeout curto (12 s)</b> no cliente HTTP do modelo (default do SDK seria 600 s por "
    "tentativa, o que pendurava a rodada) + <b>3 tentativas</b> com backoff para falhas transitórias (429/5xx).",
    "<b>Limite rígido de 600 caracteres</b>: instruído no prompt e reforçado por truncamento "
    "seguro no código, com salvaguarda de encaixe em degraus (telefones preservados até o fim).",
    "<b>Regra 5 no prompt</b>: é proibido incluir instruções pós-sinistro (documentação de danos, "
    "vistoria, acionamento do seguro) — o alerta é 100% preventivo.",
    "<b>Paralelização</b>: as gerações da rodada rodam em um pool de 3 threads "
    "(ThreadPoolExecutor), com ordem do relatório preservada; latência = máximo das chamadas, "
    "não a soma.",
    "<b>Model-agnostic</b>: Pydantic AI + OpenRouter (GLM 5.3 Flash por default); trocar de "
    "modelo é trocar uma variável de ambiente (LLM_MODEL).",
]))

# ============ 4. TECNOLOGIAS ============
A(p("4. Tecnologias Utilizadas", H1))
A(table(
    ["Categoria", "Tecnologia", "Papel / justificativa"],
    [
        ["Linguagem", "Python 3.12+", "Ecossistema maduro para agentes de IA e DDD; tipagem forte (PEP 695/dataclasses/Protocol)."],
        ["Domínio", "dataclasses frozen, Enum, typing.Protocol", "Entidades imutáveis e ports sem herança — domínio puro e testável."],
        ["HTTP dos adapters", "urllib (stdlib)", "Zero dependências para Open-Meteo, BrasilAPI e Telegram; fetch/post injetáveis para testes."],
        ["IA generativa", "Pydantic AI 1.x + OpenRouter + GLM 5.3 Flash + httpx", "Agente LLM model-agnostic; provider OpenRouter com httpx.AsyncClient de timeout 12 s."],
        ["UI da demonstração", "Streamlit 1.63", "Demo interativa para a banca: fonte, modo de mensagem, bancada editável e disparo real."],
        ["Persistência leve", "SQLite (stdlib) + JSON", "Vínculos telefone -> chat_id (SQLite, fora do Git) e seeds/fixtures versionados (JSON)."],
        ["Testes", "pytest (209 testes do produto + 122 da suíte AI-DLC)", "TDD vermelho-verde; barreira de threads prova o paralelismo; fixtures sem rede."],
        ["Estático e lint", "ruff + mypy", "Lint e tipagem estática limpos em todo o app (21 arquivos checados)."],
        ["CI/CD", "GitHub Actions", "Gates obrigatórios em todo PR/push: ruff check . + mypy app + pytest; squash-only."],
        ["Governança", "AI-DLC (memory-bank, ADRs, intents, bolts)", "Requisitos, decisões e execução auditáveis; orquestrador próprio em tools/ai-dlc."],
    ],
    [3.0 * cm, 5.4 * cm, util - 8.4 * cm],
))
A(p("Serviços externos integrados: Open-Meteo Forecast API, BrasilAPI CEP v2, "
    "OpenStreetMap/Nominatim (validação de bairros), Telegram Bot API e OpenRouter (LLM). "
    "Nenhuma exigência de chave para os dados meteorológicos — o desafio roda até offline, "
    "com fixtures determinísticas.", BODY))

# ============ 5. FLUXO ============
A(p("5. Fluxo de Processamento", H1))
A(p(
    "A unidade de trabalho é a <b>rodada</b> (run_round): para todos os segurados do "
    "catálogo, o sistema percorre o ciclo coletar -> detectar -> compor -> entregar -> "
    "reportar. O pipeline é dividido em <b>três fases</b> que equilibram correção e "
    "desempenho:", BODY))
A(table(
    ["Fase", "O que acontece", "Estratégia"],
    [
        ["<b>1. Coleta + detecção</b><br/>(sequencial)",
         "Para cada segurado: consulta de clima, snapshot registrado e avaliação pelas 10 regras. "
         "Falha de coleta é registrada (CollectionFailure) e a rodada continua com os demais.",
         "Ordem determinística; degradação graciosa"],
        ["<b>2. Geração de mensagens</b><br/>(paralela)",
         "Um alerta individual -> mensagem individual; 2+ alertas -> UMA mensagem consolidada "
         "(intent 007), do evento mais severo ao menos, com dedup de recomendações repetidas.",
         "ThreadPoolExecutor com 3 workers; ordem preservada (pool.map)"],
        ["<b>3. Entrega</b><br/>(sequencial)",
         "Envio na mesma ordem do relatório: Telegram real (chat_id resolvido por telefone) ou "
         "simulação; resultado vira NotificationRecord com sent/failed/skipped + motivo.",
         "zip(strict=True) garante alinhamento mensagem↔segurado"],
    ],
    [3.6 * cm, util - 8.6 * cm, 5.0 * cm],
))
A(p("5.1 Relatório da rodada (5 seções)", H2))
A(p("Toda rodada termina com o relatório consolidado — abaixo, saída real do modo offline "
    "(8 segurados de seeds, fixtures de tempestade):", BODY))
A(p(
    "=== Relatório da rodada — comunicação proativa com o segurado ===<br/>"
    "1. Segurados consultados: 8 (falhas de coleta: 0)<br/>"
    "2. Eventos detectados: 5<br/>"
    "&nbsp;&nbsp;&nbsp;- hail: 1<br/>"
    "&nbsp;&nbsp;&nbsp;- heavy_rain: 2<br/>"
    "&nbsp;&nbsp;&nbsp;- strong_wind: 2<br/>"
    "3. Alertas por regra:<br/>"
    "&nbsp;&nbsp;&nbsp;- [H001] heavy_rain (medium): precipitação de 12.0 mm/h (limiar 10.0 mm/h)<br/>"
    "&nbsp;&nbsp;&nbsp;- [H002] hail (high): granizo previsto (weathercode 96)<br/>"
    "&nbsp;&nbsp;&nbsp;- [H003] strong_wind (medium): ventos de 72 km/h na região costeira<br/>"
    "&nbsp;&nbsp;&nbsp;- [H005] heavy_rain (medium): precipitação de 10.0 mm/h (limiar 10.0 mm/h)<br/>"
    "&nbsp;&nbsp;&nbsp;- [H006] strong_wind (medium): ventos de 65 km/h na região costeira<br/>"
    "4. Mensagens geradas: 5 (modo template)<br/>"
    "5. Envios simulados: 5",
    CODE,
))
A(p("5.2 Interfaces de execução", H2))
S.extend(bullets([
    "<b>CLI</b> (<i>python -m app run</i>): modo offline (fixtures) ou online (Open-Meteo real), "
    "com contratos de env (LLM_MODEL / LLM_PROVIDER) para o modo de mensagem.",
    "<b>Demo visual</b> (Streamlit): sidebar escolhe fonte (real/offline) e modo (LLM com fallback "
    "ou template); a bancada edita segurados (nome, telefone, CEP com geocoding BrasilAPI, perfil "
    "de seguros, litoral) e simula o tempo — o alerta nasce das MESMAS regras do domínio; botão "
    "“Disparar Alertas” entrega no Telegram real.",
    "<b>Envio real</b>: token do bot no campo secreto da UI (ou env TELEGRAM_BOT_TOKEN); o segurado "
    "consente com /start + compartilhamento de contato; sem vínculo, o envio vira “skipped” com motivo.",
]))

# ============ 6. FONTES EXTERNAS ============
A(p("6. Integração com Fontes Externas de Dados", H1))
A(table(
    ["Fonte", "Endpoint / mecanismo", "Uso na solução", "Tratamento de falha"],
    [
        ["<b>Open-Meteo</b><br/>(Forecast API)",
         "api.open-meteo.com/v1/forecast<br/>(lat/lon a 4 casas ~11 m; current: "
         "weather_code, temperatura, precipitação, vento, umidade; vento em km/h; precipitação em mm)",
         "Clima atual de cada segurado por rodada — sem chave de API, sem custo (ADR-005).",
         "Timeout 10 s + 2 retries; erro vira WeatherProviderError (domínio); segurado entra como "
         "falha de coleta e a rodada segue."],
        ["<b>BrasilAPI</b><br/>(CEP v2)",
         "brasilapi.com.br/api/cep/v2/{cep}",
         "Geocoding do CEP informado na bancada: bairro/cidade/UF e coordenadas (ADR-007).",
         "CEP sem coordenadas -> resultado vazio SEM exceção (UI usa seeds e avisa); 404/inválido -> "
         "GeocodingError imediato; rede -> retry e degradação."],
        ["<b>OpenStreetMap</b><br/>(Nominatim)",
         "Consulta de bairros reais",
         "Validação dos bairros dos seeds (rotulagem da UI da banca).",
         "Uso pontual de preparação — não está no caminho da rodada."],
        ["<b>Telegram Bot API</b>",
         "sendMessage · getUpdates · teclado request_contact",
         "Entrega real por chat_id (nunca por telefone) e linking consentido telefone -> chat_id "
         "(ADRs 008 e 010).",
         "4xx sem retry (401/400 determinísticos); rede com retry; qualquer falha vira "
         "failed/skipped com motivo — nunca quebra a rodada."],
        ["<b>OpenRouter</b><br/>(LLM)",
         "Chat completions via Pydantic AI (modelo GLM 5.3 Flash)",
         "Reescrita natural das mensagens preventivas (story 06 / intent 008).",
         "Timeout 12 s + 3 tentativas + fallback silencioso para o template; modo sempre reportado."],
    ],
    [2.9 * cm, 4.6 * cm, 4.4 * cm, util - 11.9 * cm],
))
A(p(
    "Princípio transversal: <b>toda integração externa tem a mesma disciplina</b> — User-Agent "
    "próprio, timeout curto, retry só para erro transitório de rede, erros 4xx tratados como "
    "definitivos e, acima de tudo, <b>erro traduzido para o domínio</b> para que a rodada "
    "degrade com elegância em vez de quebrar.", BODY))

# ============ 7. REGRAS DE NEGÓCIO ============
A(p("7. Regras de Negócio", H1))
A(p(
    "As regras de detecção derivam da <b>bateria de alertas preventivos</b> aprovada pelo "
    "dono do produto (memory-bank/standards/tabela-alertas-preventiva.md) e foram "
    "operacionalizadas no domínio pelo ADR-011. Cada regra dispara apenas para os ramos "
    "com <b>exposição material</b> ao risco e para o contexto do segurado (ex.: vento forte "
    "e ressaca exigem região litorânea).", BODY))
A(p("7.1 Gatilhos de detecção e severidades", H2))
A(table(
    ["Evento", "Gatilho", "Casa (residencial)", "Carro (auto)", "Severidade"],
    [
        ["Chuva intensa", "precipitação >= 10 mm/h (>= 20 / >= 35)", "alagamento, infiltração", "vias alagadas, garagem baixa", "medium -> very_high"],
        ["Granizo", "weathercode WMO", "telhado, vidros, placas solares", "lataria, vidros", "high"],
        ["Vento forte", "vento >= 60 km/h (>= 80)", "cobertura, objetos soltos", "galhos, projeções", "medium -> very_high"],
        ["Calor / onda de calor", ">= 35 °C / >= 38 °C", "carga elétrica, hidratação", "superaquecimento", "high -> very_high"],
        ["Frio intenso", "<= 10 °C (<= 5)", "aquecedores (CO), tubulações", "bateria, partida", "high -> very_high"],
        ["Neblina", "umidade >= 95% + vento <= 15 km/h + chuva <= 10 mm/h", "—", "visibilidade", "medium -> high"],
        ["Tempestade", "chuva >= 30 + vento >= 60 km/h (35/80)", "raios, alagamento", "veículo coberto", "high -> very_high"],
        ["Ressaca (litoral)", "vento >= 80 km/h + chuva >= 30 mm/h", "maré, vedação", "orla, estacionamento baixo", "very_high"],
        ["Tempo seco", "umidade &lt; 30% (&lt; 20%)", "respiratório, incêndio", "filtro, água", "low -> medium"],
        ["Geada", "<= 0 °C (<= -2)", "tubulações", "gelo, vidros", "high -> very_high"],
        ["Múltiplos riscos", ">= 2 riscos simultâneos", "UM único aviso consolidado", "UM único aviso consolidado", "severidade máxima"],
    ],
    [2.7 * cm, 3.9 * cm, 3.6 * cm, 3.4 * cm, util - 13.6 * cm],
))
A(p("7.2 Nível INMET/Defesa Civil (tom e urgência da mensagem)", H2))
A(table(
    ["Severidade", "Nível", "Ação esperada", "Janela", "Telefones de emergência"],
    [
        ["low", "amarelo", "monitorar", "até 5 dias", "não incluir"],
        ["medium", "laranja", "prevenir", "até 3 dias", "199 · 193 · 192"],
        ["high", "vermelho", "agir hoje", "próximas 24h", "199 · 193 · 192"],
        ["very_high", "preto", "agir imediatamente", "risco iminente", "199 · 193 · 192"],
    ],
    [2.6 * cm, 2.4 * cm, 4.2 * cm, 3.4 * cm, util - 12.6 * cm],
))
A(p("7.3 As 6 regras transversais (aplicadas ao template E ao prompt da LLM)", H2))
S.extend(bullets([
    "<b>Ramos contratados</b>: só emitir células dos ramos que o segurado contratou — quem só "
    "tem auto nunca recebe instrução residencial (e vice-versa).",
    "<b>Severidade -> nível INMET</b>: o tom e a urgência seguem o nível (amarelo monitorar -> "
    "preto agir imediatamente), com a janela temporal explícita na abertura.",
    "<b>Telefones de emergência</b> (Defesa Civil 199, Bombeiros 193, SAMU 192) somente em "
    "laranja ou superior.",
    "<b>Fases</b>: nível amarelo usa só as diretrizes “Antes”; laranja ou superior usa "
    "“Antes + Durante”.",
    "<b>Escopo preventivo</b>: NUNCA incluir instruções pós-sinistro (documentação de danos, "
    "vistoria, acionamento do seguro), mesmo com o evento em andamento.",
    "<b>Perfis vulneráveis</b>: idosos, crianças e animais reforçam as diretrizes "
    "correspondentes (hidratação no calor, aquecimento seguro no frio, nunca deixar no veículo).",
]))
A(p(
    "Além disso, com <b>2+ riscos simultâneos</b> o segurado recebe <b>UMA única mensagem "
    "consolidada</b> (do evento mais severo ao menos, com dedup de recomendações repetidas) "
    "em vez de um enxame de avisos — decisão de UX registrada na intent 007.", BODY))

# ============ 8. MENSAGENS ============
A(p("8. Qualidade das Mensagens Produzidas", H1))
A(p(
    "A mensagem é o produto final do sistema e recebe tratamento de primeiro cidadão. Sua "
    "anatomia é fixa e auditável:", BODY))
S.extend(bullets([
    "<b>Abertura personalizada</b> com nome do segurado, evento previsto e nível INMET "
    "(rótulo + ação + janela temporal).",
    "<b>Blocos por ramo contratado</b> (“Casa:”, “Carro:”) com as precauções da bateria nas "
    "fases da severidade — nunca de ramo não contratado.",
    "<b>Telefones de emergência</b> quando o nível permite (laranja+), posicionados com "
    "prioridade no encaixe.",
    "<b>Limite de 600 caracteres</b> respeitado por encaixe em degraus no template "
    "(telefones preservados até o último degrau) e por truncamento seguro no LLM.",
]))
A(p("8.1 Exemplos reais (modo template — rodada offline)", H2))
A(p("Segurada residencial com chuva intensa (nível laranja):", CELL_B))
A(p("“Olá, Maria Silva! chuva intensa prevista para a sua região — nível laranja "
    "(prevenir, janela de até 3 dias). Casa: Limpe calhas, ralos e bueiros. Guarde documentos "
    "em local elevado. Prepare kit de emergência (lanterna, remédios). Defesa Civil 199 · "
    "Bombeiros 193 · SAMU 192.”", QUOTE))
A(p("Segurado só-auto com granizo (nível vermelho):", CELL_B))
A(p("“Olá, João Souza! granizo previsto para a sua região — nível vermelho "
    "(agir hoje, próximas 24h). Carro: Estacione em local coberto ou vaga interna. Fique dentro "
    "do veículo, longe dos vidros. Não saia para proteger o carro durante a queda. Defesa Civil "
    "199 · Bombeiros 193 · SAMU 192.”", QUOTE))
A(p(
    "No modo <b>LLM</b>, o mesmo contexto é reescrito com mais naturalidade — sempre com as "
    "mesmas células da bateria, as 6 regras transversais e o limite de 600 caracteres "
    "reforçado por truncamento. O modo exercitado (template, llm ou híbrido) aparece no "
    "relatório de cada rodada: <b>a banca sempre sabe quem escreveu cada mensagem</b>.", BODY))

# ============ 9. QUALIDADE E DOCUMENTAÇÃO ============
A(p("9. Qualidade da Arquitetura e da Documentação", H1))
A(p("9.1 Engenharia de qualidade", H2))
S.extend(bullets([
    "<b>TDD vermelho-verde</b> em todas as units: os testes existem antes do código e "
    "documentam o comportamento esperado (209 testes do produto + 122 da suíte de governança).",
    "<b>Gates obrigatórios</b> em todo PR e push: ruff check . + mypy app + pytest "
    "(GitHub Actions), com política squash-only e 1 branch por intent.",
    "<b>Testes de fronteira sem rede</b>: HTTP injetável nos adapters; paralelismo da rodada "
    "provado por teste com threading.Barrier (se a geração rodar em série, o teste falha).",
    "<b>Segurança</b>: token do bot só em campo secreto da UI ou variável de ambiente (nunca "
    "no repositório); banco de vínculos fora do Git (ADR-010); nenhuma regra de negócio na UI.",
]))
A(p("9.2 Documentação viva (AI-DLC)", H2))
A(p(
    "O projeto é desenvolvido com o ciclo AI-DLC: cada entrega é uma <b>intent</b> com "
    "critérios de aceite, desdobrada em stories/units e executada em <b>bolts</b> com "
    "log de execução; decisões de arquitetura viram <b>ADRs</b>. Tudo auditável no "
    "memory-bank:", BODY))
A(table(
    ["Documento", "Conteúdo"],
    [
        ["Intents 001–008", "001 fundação de qualidade/CI · 002 comunicação proativa (pipeline completo) · "
         "003 demo Streamlit · 004 entrega Telegram · 005 risk engine V2 · 006 vínculos SQL · "
         "007 mensagens consolidadas · 008 bateria preventiva"],
        ["ADRs 005–011", "005 Open-Meteo como fonte · 006 orquestrador AI-DLC · 007 BrasilAPI CEP · "
         "008 Telegram Bot API · 009 risk engine V2 (superseded) · 010 vínculos SQLite · "
         "011 bateria Risco × Ramo × Fase"],
        ["Standards", "Tabela de alertas preventivos (fonte de negócio), stack, arquitetura, "
         "padrões de código e de Git"],
    ],
    [3.6 * cm, util - 3.6 * cm],
))

# ============ 10. CRIATIVIDADE ============
A(p("10. Criatividade na Solução Proposta", H1))
S.extend(bullets([
    "<b>Inversão do modelo de comunicação</b>: de reativo (pós-sinistro) para proativo "
    "(antes do sinistro) — o diferencial conceitual do desafio, operacionalizado de ponta a ponta.",
    "<b>Bateria preventiva Risco × Ramo × Fase</b>: conteúdo de especialista de seguros/Defesa "
    "Civil (fases Antes/Durante, níveis INMET) transformado em dados do domínio que alimentam "
    "template e LLM com consistência garantida — regra de negócio vira código auditável.",
    "<b>UM aviso consolidado</b> para múltiplos riscos simultâneos, com dedup — anti-enxame de "
    "notificações pensado do ponto de vista do segurado.",
    "<b>Vinculação sem PII no domínio</b>: o chat_id nasce do consentimento do segurado no bot "
    "e vive fora do Git; o domínio nunca carrega dados sensíveis de canal.",
    "<b>Bancada de simulação</b> para a banca: edita segurados e o tempo simulado, com "
    "geocoding real de CEP — o alerta nasce das mesmas regras do domínio, tornando a "
    "demonstração reproduzível e honesta.",
    "<b>Resiliência como feature</b>: modo 100% offline determinístico (banca sem internet), "
    "fallback silencioso da LLM, degradação graciosa em todas as fronteiras — “a demo nunca "
    "quebra” é um critério de aceite, não um desejo.",
    "<b>Governança com orquestrador agêntico</b>: o próprio desenvolvimento usou um orquestrador AI-DLC "
    "(tools/ai-dlc) com gates de qualidade — agentes LLM construindo e auditando o sistema.",
]))

# ============ 11. LIMITAÇÕES ============
A(p("11. Limitações e Evoluções Futuras", H1))
S.extend(bullets([
    "<b>Fumaça de queimadas</b>: previsto no backlog — exige a Air Quality API do Open-Meteo "
    "(a bateria de negócio já tem as células Antes/Durante preparadas).",
    "<b>Detecção de evento em andamento</b>: hoje a rodada usa clima atual; forecast/histórico "
    "permitiria acionar a fase “Durante” automaticamente.",
    "<b>Perfis vulneráveis</b>: as diretrizes existem na bateria e no prompt, mas o domínio "
    "ainda não tem campo estruturado de moradores/animais.",
    "<b>Agendamento</b>: a rodada é disparada manualmente (CLI/UI); um scheduler com "
    "persistência de histórico de rodadas é a evolução natural para operação real.",
]))

# ============ 12. COMO EXECUTAR ============
A(p("12. Como Executar a Demonstração", H1))
A(p("Requisitos: Python 3.12+. O modo template não exige instalar dependências.", BODY))
A(p(
    "# 1) Demo determinística offline (banca sem internet)<br/>"
    "python -m app run --offline<br/><br/>"
    "# 2) Demo online (Open-Meteo real, sem API key)<br/>"
    "python -m app run<br/><br/>"
    "# 3) Demo com agente LLM reescrevendo as mensagens<br/>"
    "export OPENROUTER_API_KEY=sua-chave<br/>"
    "export LLM_MODEL=openrouter:z-ai/glm-5.3-flash<br/>"
    "python -m app run --offline<br/><br/>"
    "# Demo visual (Streamlit)<br/>"
    "pip install -r requirements-ui.txt<br/>"
    "streamlit run ui/demo_app.py",
    CODE,
))
A(p(
    "Para o envio real via Telegram: criar o bot no @BotFather, colar o token no campo secreto "
    "da sidebar, pedir ao segurado para dar /start e compartilhar o contato, clicar em "
    "“Vincular contatos” e então em “Disparar Alertas”.", BODY))

# ---------------------------------------------------------------- build
doc.multiBuild(S)
print("PDF gerado em:", OUT)
