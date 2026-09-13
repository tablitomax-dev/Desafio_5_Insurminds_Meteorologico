"""Bateria de alertas preventivos — Risco × Ramo × Fase (intent 008).

Fonte de negócio: `memory-bank/standards/tabela-alertas-preventiva.md`
(bateria Risco × Ramo com fases ANTES/DURANTE e severidade INMET/Defesa
Civil). Estrutura consumida pelo `TemplateGenerator` e pelo prompt da
LLM — a mesma célula alimenta os dois caminhos (consistência entre
template e reescrita).

Regras transversais do arquivo aplicadas aqui:
1. Só as células dos ramos CONTRATADOS pelo segurado;
2. Severidade mapeada nos níveis INMET (amarelo/laranja/vermelho/preto)
   — o tom e a urgência seguem o nível (e a janela temporal orienta a
   LLM: monitorar ≤5 dias, prevenir ≤3 dias, agir hoje ≤24h, imediato);
3. Telefones de emergência (199/193/192) apenas em laranja ou superior;
4. Fase: nível amarelo → só "Antes"; laranja+ → "Antes + Durante";
5. Escopo PREVENTIVO: nenhuma instrução pós-sinistro (documentação de
   danos, vistoria, acionamento do seguro) — a LLM recebe a proibição
   explícita no prompt;
6. Perfis vulneráveis: reforço quando houver dados de moradores/animais
   (hoje o domínio não tem esse campo — diretriz condicional).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.holders import InsuranceType
from app.domain.risk import RiskKind, Severity

# ---------------------------------------------------------------- rótulos

BRANCH_LABELS: dict[InsuranceType, str] = {
    InsuranceType.RESIDENTIAL: "Casa",
    InsuranceType.AUTO: "Carro",
}

@dataclass(frozen=True)
class InmetLevel:
    """Nível INMET/Defesa Civil (regras transversais 2 e 3)."""

    label: str  # amarelo / laranja / vermelho / preto
    action: str  # monitorar / prevenir / agir hoje / agir imediatamente
    window: str  # janela temporal esperada para o nível
    phones: bool = False  # telefones de emergência (regra 3: laranja+)

INMET_LEVELS: dict[Severity, InmetLevel] = {
    Severity.LOW: InmetLevel(
        label="amarelo", action="monitorar", window="janela de até 5 dias"
    ),
    Severity.MEDIUM: InmetLevel(
        label="laranja",
        action="prevenir",
        window="janela de até 3 dias",
        phones=True,
    ),
    Severity.HIGH: InmetLevel(
        label="vermelho", action="agir hoje", window="próximas 24h",
        phones=True,
    ),
    Severity.VERY_HIGH: InmetLevel(
        label="preto",
        action="agir imediatamente",
        window="risco iminente",
        phones=True,
    ),
}

EMERGENCY_PHONES: str = "Defesa Civil 199 · Bombeiros 193 · SAMU 192."

# ---------------------------------------------------------------- células

@dataclass(frozen=True)
class BatteryCell:
    """Célula da bateria para um (risco, ramo): impacto material do
    evento e ações preventivas por fase (ANTES / DURANTE — nada de
    pós-sinistro, regra 5)."""

    impacts: tuple[str, ...]
    before: tuple[str, ...]
    during: tuple[str, ...]


RISK_BATTERY: dict[RiskKind, dict[InsuranceType, BatteryCell]] = {
    RiskKind.HEAVY_RAIN: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=(
                "alagamento de áreas baixas",
                "infiltração em telhado e paredes",
            ),
            before=(
                "Limpe calhas, ralos e bueiros",
                "Guarde documentos em local elevado",
                "Prepare kit de emergência (lanterna, remédios)",
            ),
            during=(
                "Eleve móveis e eletrodomésticos do piso",
                "Desligue a energia e feche água e gás",
                "Acompanhe o nível da água; observe rachaduras nas paredes",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("áreas alagadas, aquaplanagem e garagens baixas",),
            before=(
                "Retire o veículo de garagens subterrâneas e vias de baixada",
                "Confira pneus e palhetas",
            ),
            during=(
                "Nunca atravesse vias alagadas",
                "Estacione em local alto e aguarde passar",
                "Reduza a velocidade para evitar aquaplanagem",
            ),
        ),
    },
    RiskKind.HAIL: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("telhado, janelas, vidros e placas solares",),
            before=(
                "Feche toldos, janelas e persianas",
                "Verifique fixação de placas solares e cobertura",
            ),
            during=("Fique longe de janelas e vidraças",),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("lataria e vidros",),
            before=("Estacione em local coberto ou vaga interna",),
            during=(
                "Fique dentro do veículo, longe dos vidros",
                "Não saia para proteger o carro durante a queda",
            ),
        ),
    },
    RiskKind.STRONG_WIND: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("telhado, toldos, antenas e objetos soltos",),
            before=(
                "Recolha móveis de jardim, vasos e lonas",
                "Fixe toldos e pode galhos próximos à edificação",
            ),
            during=(
                "Feche portas e janelas e evite áreas externas",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("galhos, placas e projeção de objetos",),
            before=(
                "Evite estacionar sob árvores, placas e estruturas provisórias",
            ),
            during=("Reduza a velocidade e firme o volante nas rajadas",),
        ),
    },
    RiskKind.HEAT: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("sobrecarga elétrica e desconforto térmico",),
            before=(
                "Evite sobrecarga elétrica do ar-condicionado",
                "Hidrate-se bem",
            ),
            during=(
                "Hidrate idosos e crianças; ventile os ambientes",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("superaquecimento, pneus e itens expostos ao sol",),
            before=(
                "Confira o líquido de arrefecimento e a calibragem dos pneus",
            ),
            during=(
                "Nunca deixe crianças, idosos e animais no veículo",
                "Não deixe garrafas e aerossóis expostos ao sol",
            ),
        ),
    },
    RiskKind.HEAT_WAVE: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("sobrecarga elétrica prolongada e calor extremo",),
            before=("Reforce a climatização e evite sobrecarga elétrica",),
            during=(
                "Hidrate idosos e crianças; evite o sol entre 10h e 16h",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("superaquecimento do veículo e conteúdo exposto",),
            before=("Confira arrefecimento, pneus e bateria",),
            during=(
                "Nunca deixe crianças, idosos e animais no veículo",
                "Estacione na sombra sempre que possível",
            ),
        ),
    },
    RiskKind.EXTREME_COLD: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("aquecedores a gás (gás tóxico) e tubulações",),
            before=(
                "Cheque aquecedores a gás; isole tubulações expostas",
            ),
            during=(
                "Ventile o ambiente sempre que usar aquecedor",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("bateria, partida e para-brisa congelado",),
            before=(
                "Teste a bateria e complete o aditivo do arrefecimento",
            ),
            during=(
                "Nunca use água quente no para-brisa congelado",
                "Cuidado com gelo fino em pontes e sombras",
            ),
        ),
    },
    RiskKind.FOG: {
        InsuranceType.AUTO: BatteryCell(
            impacts=("visibilidade reduzida e colisões",),
            before=(
                "Confira faróis e luzes de neblina; saia com folga de tempo",
            ),
            during=(
                "Use farol baixo; reduza a velocidade e guarde distância",
                "Nunca pare na pista",
            ),
        ),
    },
    RiskKind.STORM: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("raios, janelas e alagamento",),
            before=("Use proteção contra surtos; confira o para-raios",),
            during=(
                "Desconecte aparelhos da tomada",
                "Fique longe de janelas, torneiras e chuveiro",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("raios, queda de galhos e alagamento",),
            before=("Planeje estacionamento em trechos cobertos",),
            during=(
                "Fique dentro do carro com janelas fechadas",
                "Não pare sob árvores, postes e torres",
            ),
        ),
    },
    RiskKind.ROUGH_SEA: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("maré alta, invasão de água e erosão",),
            before=(
                "Reforce a vedação de portas e janelas voltadas ao mar",
                "Eleve equipamentos e móveis do térreo",
            ),
            during=(
                "Feche as aberturas voltadas ao mar se a água chegar",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("ondas, sal e detritos na orla",),
            before=(
                "Nunca estacione na orla ou em estacionamentos baixos",
            ),
            during=("Não circule pela orla",),
        ),
    },
    RiskKind.LOW_HUMIDITY: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("ar seco, vias respiratórias e focos de incêndio",),
            before=(
                "Deixe água e panos úmidos nos ambientes",
                "Umidifique quartos de crianças e idosos",
            ),
            during=(
                "Beba líquidos e evite exercícios entre 10h e 16h",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("poeira e vias respiratórias dos ocupantes",),
            before=("Confira o ar-condicionado e o filtro do veículo",),
            during=(
                "Mantenha garrafa de água no carro",
                "Evite trechos com focos de incêndio",
            ),
        ),
    },
    RiskKind.FROST: {
        InsuranceType.RESIDENTIAL: BatteryCell(
            impacts=("tubulações e registros externos",),
            before=("Proteja tubulações e registros externos",),
            during=(
                "Feche o registro geral em caso de rompimento",
                "Redobre o cuidado com aquecedores",
            ),
        ),
        InsuranceType.AUTO: BatteryCell(
            impacts=("gelo, vidros e frenagem",),
            before=("Calibre pneus; confira bateria e aditivo",),
            during=(
                "Gelo fino em pontes e sombras: reduza muito",
                "Evite frenagens bruscas",
            ),
        ),
    },
    # MULTIPLE_RISKS não tem células: a mensagem consolidada usa as dos
    # eventos individuais (recomendações genéricas viriam duplicadas).
}

# ---------------------------------------------------------------- helpers

def level_for(severity: Severity) -> InmetLevel:
    """Nível INMET correspondente ao severity do alerta (regra 2)."""
    return INMET_LEVELS[severity]


def phases_for(severity: Severity) -> tuple[str, ...]:
    """Fases da mensagem (regra 4): amarelo → só ANTES; laranja+ →
    ANTES + DURANTE."""
    return ("before",) if severity is Severity.LOW else ("before", "during")


def cells_for(
    kind: RiskKind, insurance_types: frozenset[InsuranceType]
) -> dict[InsuranceType, BatteryCell]:
    """Células do risco PARA OS RAMOS CONTRATADOS (regra 1)."""
    branch_cells: Mapping[InsuranceType, BatteryCell] = RISK_BATTERY.get(
        kind, {}
    )
    return {
        branch: cell
        for branch, cell in branch_cells.items()
        if branch in insurance_types
    }


def recommendations_for(
    kind: RiskKind,
    insurance_types: frozenset[InsuranceType],
    *,
    severity: Severity,
) -> tuple[tuple[InsuranceType, str], ...]:
    """Recomendações das fases da severidade (regra 4) para os ramos
    contratados, agrupadas por ramo e em ordem (Antes → Durante)."""
    out: list[tuple[InsuranceType, str]] = []
    fases = phases_for(severity)
    for branch, cell in cells_for(kind, insurance_types).items():
        for fase in fases:
            out.extend(
                (branch, rec) for rec in getattr(cell, fase)
            )
    return tuple(out)


def impacts_for(
    kind: RiskKind, insurance_types: frozenset[InsuranceType]
) -> tuple[str, ...]:
    """Impactos materiais das células dos ramos contratados."""
    return tuple(
        impact
        for cell in cells_for(kind, insurance_types).values()
        for impact in cell.impacts
    )
