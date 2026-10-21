import pytest
import math
import numpy as np
import json
from cep_capacidade import (
    formatar_numero_br,
    extrair_medicoes,
    calcular_classes_histograma,
    calcular_curva_normal,
    avaliar_limites_especificacao,
    calcular_estatisticas_capacidade,
    obter_passo_redondo,
    obter_passo_inteiro_y,
    plotar_capacidade
)


def test_formatar_numero_br():
    assert formatar_numero_br(4.9612, 4) == "4,9612"
    assert formatar_numero_br(19.27, 2) == "19,27"
    assert formatar_numero_br(5.0, 4) == "5,0000"
    assert formatar_numero_br(None) == "—"
    assert formatar_numero_br(float('nan')) == "—"
    assert formatar_numero_br(float('inf')) == "—"


def test_calcular_classes_histograma_exemplo():
    with open("exemplos/dados_simulado_prova_1_0226.json", "r", encoding="utf-8-sig") as f:
        dados = json.load(f)
    
    medicoes = extrair_medicoes(dados["Data"])
    assert len(medicoes) == 100
    
    k, w, edges, counts, midpoints = calcular_classes_histograma(medicoes)
    # Regra de Sturges: ceil(log2(100)) + 1 = 7 + 1 = 8
    assert k == 8
    assert len(counts) == 8
    # Frequências esperadas na referência visual
    assert counts.tolist() == [4, 5, 6, 18, 18, 21, 20, 8]
    assert min(medicoes) == 4.927
    assert max(medicoes) == 4.984
    assert round(w, 6) == round((4.984 - 4.927) / 8, 6)


def test_calcular_classes_histograma_casos_borda():
    # Lista vazia
    k0, w0, edges0, counts0, _ = calcular_classes_histograma([])
    assert k0 == 0
    assert len(counts0) == 0

    # 1 valor
    k1, w1, edges1, counts1, _ = calcular_classes_histograma([5.0])
    assert k1 == 1
    assert counts1.tolist() == [1]

    # Todos iguais
    k_eq, w_eq, edges_eq, counts_eq, _ = calcular_classes_histograma([5.0, 5.0, 5.0])
    assert k_eq == 1
    assert counts_eq.tolist() == [3]


def test_calcular_curva_normal():
    n = 100
    w = (4.984 - 4.927) / 8  # 0.007125
    mu = 4.961235
    sigma_curto = 0.008649
    
    # Pico da curva normal em x = mu
    y_pico = calcular_curva_normal(np.array([mu]), n, w, mu, sigma_curto)[0]
    # Na imagem o pico fica em ≈ 33 (32.86)
    assert 32.5 <= y_pico <= 33.2
    
    # Em x distante, a cauda deve tender a 0
    y_cauda = calcular_curva_normal(np.array([mu + 5 * sigma_curto]), n, w, mu, sigma_curto)[0]
    assert y_cauda < 0.01

    # Caso inválido: sigma <= 0
    y_invalido = calcular_curva_normal(np.array([mu]), n, w, mu, 0.0)
    assert y_invalido[0] == 0.0


def test_avaliar_limites_especificacao():
    mu = 4.9612
    sigma_global = 0.011176
    # 6 * sigma_global ≈ 0.067056
    # LIE = 4.0 -> distância = |4.0 - 4.9612| = 0.9612 > 0.067056 -> Fora da escala
    # LSE = 5.0 -> distância = |5.0 - 4.9612| = 0.0388 < 0.067056 -> Visível
    
    vis, fora, nota = avaliar_limites_especificacao(mu, sigma_global, lie=4.0, lse=5.0)
    assert len(vis) == 1
    assert vis[0] == ("LSE", 5.0)
    assert len(fora) == 1
    assert fora[0] == ("LIE", 4.0)
    assert nota == "LIE = 4,0000 fora da escala"

    # Ambos fora da escala
    vis_ambos, fora_ambos, nota_ambos = avaliar_limites_especificacao(mu, sigma_global, lie=4.0, lse=6.0)
    assert len(vis_ambos) == 0
    assert len(fora_ambos) == 2
    assert nota_ambos == "LIE = 4,0000 e LSE = 6,0000 fora da escala"

    # Ambos visíveis
    vis_dentro, fora_dentro, nota_dentro = avaliar_limites_especificacao(mu, sigma_global, lie=4.94, lse=4.98)
    assert len(vis_dentro) == 2
    assert len(fora_dentro) == 0
    assert nota_dentro is None


def test_calcular_indices_capacidade_exemplo():
    with open("exemplos/dados_simulado_prova_1_0226.json", "r", encoding="utf-8-sig") as f:
        dados = json.load(f)
    medicoes = extrair_medicoes(dados["Data"])
    
    from cep_core import processar_cep
    ret = processar_cep(dados)
    cap = ret["capacidade"]
    
    stats = calcular_estatisticas_capacidade(medicoes, lie=4.0, lse=5.0, cap_existente=cap)
    assert stats["valido"] is True
    assert round(stats["mu"], 4) == 4.9612
    assert round(stats["rcp"], 2) == 19.27
    assert round(stats["rcpk"], 2) == 1.49
    assert stats["status_rcpk"] == "(capaz)"
    assert round(stats["ppk"], 2) == 1.16


def test_calcular_indices_unilaterais_e_status():
    medicoes = [10.0, 10.2, 10.1, 10.3, 9.9, 10.1]
    
    # Apenas LSE
    stats_lse = calcular_estatisticas_capacidade(medicoes, lse=10.5, lie=None)
    assert stats_lse["rcp"] is None  # Unilateral: RCP omitido
    assert stats_lse["rcpk"] is not None
    assert stats_lse["ppk"] is not None

    # Status de RCPk
    # >= 1.33: (capaz)
    stats_capaz = calcular_estatisticas_capacidade(medicoes, lse=11.0, lie=9.0)
    assert stats_capaz["status_rcpk"] == "(capaz)"

    # Marginal: 1.00 <= RCPk < 1.33
    # mu = 10.1, 3*sigma_curto ≈ 0.585 -> com LSE = 10.77, RCPk ≈ 1.15
    stats_marginal = calcular_estatisticas_capacidade(medicoes, lse=10.77, lie=9.43)
    assert stats_marginal["status_rcpk"] == "(marginal)"

    # Não capaz: RCPk < 1.00
    stats_nao_capaz = calcular_estatisticas_capacidade(medicoes, lse=10.5, lie=9.7)
    assert stats_nao_capaz["status_rcpk"] == "(não capaz)"


def test_passos_eixos():
    # Eixo X
    passo_x = obter_passo_redondo(0.073, alvo_ticks=7)
    assert passo_x == 0.010

    # Eixo Y
    passo_y = obter_passo_inteiro_y(38.45)
    assert passo_y == 4


def test_plotar_capacidade_geracao_figura():
    with open("exemplos/dados_simulado_prova_1_0226.json", "r", encoding="utf-8-sig") as f:
        dados = json.load(f)
    medicoes = extrair_medicoes(dados["Data"])
    
    # Com dados válidos
    fig = plotar_capacidade(medicoes, lie=4.0, lse=5.0, unidade="mm")
    assert fig is not None
    assert len(fig.axes) == 1
    
    # Caso de borda: dados insuficientes (n < 2)
    fig_insuf = plotar_capacidade([4.95], lie=4.0, lse=5.0)
    assert fig_insuf is not None
    assert len(fig_insuf.axes) == 1
