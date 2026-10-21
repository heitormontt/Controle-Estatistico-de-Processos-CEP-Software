# Software de Controle Estatístico de Processo (CEP)

Software em Python para **Controle Estatístico de Processo (CEP / SPC)** com **Interface Web (Streamlit)** e **Linha de Comando (CLI)**. Realiza cálculos para cartas de controle por variáveis e atributos, avalia regras de sensibilidade (Western Electric), capacidade do processo ($C_p, C_{pk}$) e sensibilidade a deslocamentos ($\text{ARL}$ e Poder).

---

## 📌 O que o software faz?

- **Cartas Suportadas:**
  - $\bar{X} - R$ (Média e Amplitude) e $I - MR$ (Valores Individuais e Amplitude Móvel).
  - $p$ (Fração de não conformes) e $c$ (Contagem de não conformidades).
- **Regras de Sensibilidade:** $R1$ (fora de $3\sigma$), $R2$ (2 de 3 além de $2\sigma$), $R3$ (4 de 5 além de $1\sigma$) e $R4$ (8 pontos do mesmo lado da linha média).
- **Capacidade do Processo:** $C_p$, $C_{pk}$, $P_p$, $P_{pk}$ e PPM (teórico e observado).
- **Análise de Deslocamento:** Curvas de operação ($\beta$, Poder e $\text{ARL}_1$) para deslocamentos de média de $0$ a $3\sigma$.
- **Relatórios:** Gráficos em `.png`, resumo em `.json` e relatório técnico completo em `.pdf`.

---

## 🧠 Ciclo CEP: Fase I vs. Fase II

| Característica | **Fase I — Calibração** (`Goal: "Calibrar"`) | **Fase II — Acompanhamento** (`Goal: "Acompanhar"`) |
| :--- | :--- | :--- |
| **Objetivo** | Estabilizar o processo e calcular limites naturais com dados históricos. | Monitorar a produção contínua em tempo real. |
| **Limites** | Calculados e refinados iterativamente pelo software. | **Fixos e congelados** (vindos do `calibracao.json`). |
| **Pontos fora** | **Removidos** (causas especiais expurgadas para limpar os limites). | **Sinalizados** (nenhum ponto é removido; gera alarmes na linha). |
| **Saída** | Gera automaticamente o arquivo `calibracao.json` para a Fase II. | Gera os gráficos e relatório da produção monitorada. |

---

## 💻 Instalação

```bash
pip install -r requirements.txt
```

---

## 🚀 Como Usar

### 1. Interface Web (Frontend com Streamlit)
Inicie a aplicação uma única vez:
```bash
streamlit run app.py
```
Todo o fluxo de trabalho pode ser feito **100% pela tela** no navegador:

- **Passo 1 — Calibração (Fase I):**
  1. No menu lateral, carregue seu arquivo de dados brutos (ex: `dados_simulado_prova_1_0226.json`).
  2. O sistema calcula os limites naturais, remove causas especiais e plota as cartas.
  3. Na aba **Exportação**, clique em **"Baixar calibracao.json"** (que já vem pronto para a Fase II) e em **"Baixar Relatório PDF"**.

- **Passo 2 — Acompanhamento (Fase II):**
  1. Carregue o arquivo `calibracao.json` baixado direto no menu lateral (com as novas medições no campo `Data`).
  2. O front detecta automaticamente o modo `Acompanhar`, congela os limites e destaca em vermelho/laranja qualquer desvio da linha de produção em tempo real.

---

### 2. Linha de Comando (CLI — Opcional)
Para automações ou processamento em lote via terminal, sem abrir o navegador:

1. **Coloque o seu arquivo JSON de entrada dentro da pasta `exemplos/` do software.**
2. **Execute a calibração no terminal (Passo 1):**
```bash
python cep.py exemplos/<nome_do_arquivo>.json --saida resultados/
```
3. **Para o acompanhamento (Passo 2), entre na pasta `resultados/` do software onde o arquivo `calibracao.json` foi gerado e execute:**
```bash
python cep.py resultados/calibracao.json --saida resultados_fase2/
```

**Arquivos gerados na pasta de saída (`resultados/`):**
- `calibracao.json`: arquivo de limites gerado na calibração, pronto para a Fase II.
- `cartas.png`: cartas de controle plotadas em alta resolução.
- `relatorio_cep.pdf`: relatório técnico profissional em PDF.
- `relatorio.json`: resumo dos parâmetros calculados e capacidade.

---

## 📄 Modelos de Arquivos JSON

### Modelo para Calibração (Fase I)
*Exatamente como em `exemplos/dados_simulado_prova_1_0226.json`:*

```json
{
  "Unit": "mm",
  "Label": "Diâmetro externo",
  "Measured_at": "2026-10-09 12:00:00",
  "Created_by": "Henrique",
  "Type": "X",
  "Goal": "Calibrar",
  "LSE": 5.0,
  "LIE": 4.0,
  "Data": [
    [4.960, 4.946, 4.950, 4.956, 4.958],
    [4.958, 4.927, 4.935, 4.940, 4.950],
    [4.971, 4.929, 4.965, 4.952, 4.938],
    [4.940, 4.982, 4.970, 4.953, 4.960]
  ]
}
```

### Modelo para Acompanhamento (Fase II)
*Gerado automaticamente na exportação (`calibracao.json`):*

```json
{
  "Type": "X",
  "Goal": "Acompanhar",
  "Label": "Diâmetro externo",
  "Unit": "mm",
  "LSE": 5.0,
  "LIE": 4.0,
  "LSC": {
    "X": 4.9728,
    "R": 0.0425
  },
  "LIC": {
    "X": 4.9496,
    "R": 0.0
  },
  "LC": {
    "X": 4.9612
  },
  "Calibration": {
    "Data_is_original": true,
    "Removed_subgroups": [2, 9, 17]
  },
  "Data": [
    [4.962, 4.959, 4.965, 4.961, 4.960],
    [4.965, 4.960, 4.958, 4.963, 4.962]
  ]
}
```
*(Para monitorar novos lotes, basta substituir o `"Data"` pelas novas amostras coletadas).*

---

## 🧪 Testes Automatizados

```bash
python -m pytest tests/ -v
```
