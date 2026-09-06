# ADR-007: BrasilAPI CEP v2 como geocoder da bancada (intent 003)

- **Status**: accepted
- **Date**: 2026-09-06
- **Supersedes**: nenhum
- **Intent**: 003-streamlit-ui (ampliação aprovada pelo dono: a banca edita
  CEP, não latitude/longitude)

## Contexto

A bancada de simulação da demo visual deixou de expor latitude/longitude
editáveis (pedido do dono): a banca informa o **CEP** do bairro e o sistema
resolve as coordenadas automaticamente. A Open-Meteo NÃO resolve CEP nem
endereço (só busca por nome de cidade, sem CEPs); o Nominatim/OSM não
indexa CEPs brasileiros com confiabilidade.

## Decisão

1. **Geocoder: BrasilAPI CEP v2** (`https://brasilapi.com.br/api/cep/v2/{cep}`)
   — uma única chamada retorna bairro/cidade/UF **e** coordenadas
   (base open-cep/OSM), sem API key, sem custo.
2. **Cliente HTTP stdlib** (`urllib.request`), mesmo padrão do ADR-005:
   zero dependências, fetch injetável para testes, timeout + retry.
   `User-Agent` próprio é OBRIGATÓRIO — a BrasilAPI responde 403 ao
   User-Agent default do urllib (detectado em smoke da demo).
3. **Port/adapter**: `CepGeocoder` (Protocol) + `GeocodingError` no
   domínio (`app/domain/ports.py`); `CepLocation` (coords opcionais) em
   `app/domain/weather.py`; adapter `BrasilApiGeocoder` em
   `app/adapters/brasil_api.py`.
4. **Degradacao graciosa** (decisão do dono):
   - CEP sem coordenadas na base (ex.: CEP municipal 11740-000, bairro
     null) → `CepLocation(location=None)` — a rodada usa as coordenadas
     dos seeds e a UI lista o aviso;
   - falha de rede → retry e `GeocodingError` — mesmo tratamento;
   - CEP inválido/não encontrado (404) → `GeocodingError` imediato, sem
     retry (erro definitivo).
5. **Cache por sessão** (`st.session_state.cep_cache`): cada CEP é
   resolvido uma vez; "Restaurar dados originais" limpa o cache.
6. **Seeds**: cada segurado ganhou CEP real compatível com o bairro
   validado via Nominatim (H001 01016-020 … H008 12210-060).

## Consequências

- Resolver CEP novo exige internet (BrasilAPI): no modo offline sem rede,
  a bancada degrada para as coordenadas dos seeds (o tempo segue
  editável por segurado, independente de rede).
- A rodada nunca depende de geocoding bem-sucedido para existir —
  falha degrada, nunca interrompe (mesmo espírito da story 01).
- Trocar de provedor de geocoding exige só um novo adapter (port
  `CepGeocoder`).
