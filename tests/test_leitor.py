import json
import math
import pytest
from pathlib import Path
from datetime import datetime
from software_cep.cep_leitor import ler_arquivo, FamiliaCarta

@pytest.fixture
def criador_json(tmp_path):
    """Fixture que cria um JSON temporário e devolve o caminho."""
    def _criar(nome_arquivo, conteudo_dict):
        caminho = tmp_path / nome_arquivo
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(conteudo_dict, f)
        return caminho
    return _criar

def test_leitura_arquivo_prova_1_xr(criador_json):
    """Teste para o dados_prova_1_0226_1.json (Carta X/R)."""
    dados_xr = [
        [4.957, 4.947, 4.951, 4.958, 4.960],
        [4.947, 4.972, 4.936, 4.943, 4.953],
        # Simulando os 17 do meio omitidos, geraremos uma matriz de 20x5 com um valor max/min
        *[[4.961]*5 for _ in range(17)],
        [4.978, 4.965, 4.966, 4.974, 4.973]
    ]
    # Inserindo o min e max conhecidos na matriz simulada
    dados_xr[2][0] = 4.926
    dados_xr[2][1] = 4.984

    conteudo = {
        "Type": ["X", "R"], "Unit": "mm", "Measured_at": "2026-10-09 12:00:00",
        "Created_by": "Henrique", "Goal": "Calibrar",
        "LSE": 5.02, "LIE": 4.91, "Data": dados_xr
    }
    caminho = criador_json("dados_prova_1_0226_1.json", conteudo)
    
    resultado = ler_arquivo(caminho)
    
    assert not resultado.erros
    assert resultado.dados is not None
    assert resultado.dados.familia == FamiliaCarta.XBAR_R
    assert resultado.dados.tamanho_subgrupo == 5
    assert len(resultado.dados.subgrupos) == 20
    assert isinstance(resultado.dados.medido_em, datetime)
    
    # Checagens matemáticas pedidas
    achatados = [v for sub in resultado.dados.subgrupos for v in sub]
    assert len(achatados) == 100
    assert math.isclose(min(achatados), 4.926)
    assert math.isclose(max(achatados), 4.984)

def test_leitura_arquivo_prova_2_p(criador_json):
    """Teste para o dados_prova_1_0226_2.json (Carta P)."""
    d_vals = [7, 9, 6, 11, 8, 10, 5, 9, 12, 7, 8, 6, 10, 9, 7, 11, 8, 6, 10, 9]
    dados_p = [[100.0, float(d)] for d in d_vals] # Testando a aceitação do float n.0
    
    conteudo = {
        "Type": ["P"], "Unit": "unidades", "Measured_at": "2026-10-21 12:00:00",
        "Created_by": "Henrique", "Goal": "Monitorar proporção de defeituosos",
        "Data": dados_p
    }
    caminho = criador_json("dados_prova_1_0226_2.json", conteudo)
    
    resultado = ler_arquivo(caminho)
    
    assert not resultado.erros
    assert resultado.dados.familia == FamiliaCarta.P
    assert sum(resultado.dados.tamanhos_amostra) == 2000
    assert sum(resultado.dados.defeituosos) == 168
    proporcao_media = sum(resultado.dados.defeituosos) / sum(resultado.dados.tamanhos_amostra)
    assert math.isclose(proporcao_media, 0.084)

def test_leitura_arquivo_prova_3_imr(criador_json):
    """Teste para o dados_prova_1_0226_3.json (Carta I/MR)."""
    dados_xr = [4.957, 4.947, 4.951, 4.958, 4.960, 4.978, 4.965, 4.966, 4.974, 4.973]
    # Preechendo até 20 para evitar o aviso de < 20 linhas (usando 20 linhas de 1 valor)
    dados_imr = [[x] for x in dados_xr] + [[4.961] for _ in range(10)]
    
    conteudo = {
        "Type": ["I", "MR"], "Data": dados_imr, "LSE": 5.02, "LIE": 4.91
    }
    caminho = criador_json("dados_prova_1_0226_3.json", conteudo)
    resultado = ler_arquivo(caminho)
    
    assert not resultado.erros
    # Verificar se as chaves esperadas faltantes geraram avisos
    assert any("Unit" in a for a in resultado.avisos)
    assert resultado.dados.familia == FamiliaCarta.I_MR
    assert len(resultado.dados.valores) == 20
    assert resultado.dados.valores[0] == 4.957
    assert resultado.dados.valores[9] == 4.973

def test_erros_de_validacao(criador_json):
    """Testa múltiplos casos de erro para garantir a rejeição do arquivo."""
    # 1. Type Desconhecido
    arq1 = criador_json("err1.json", {"Type": ["C", "U"], "Data": [[1,2], [3,4]]})
    res1 = ler_arquivo(arq1)
    assert any("não suportado" in e for e in res1.erros)

    # 2. X/R com tamanho inconsistente
    arq2 = criador_json("err2.json", {"Type": ["X", "R"], "Data": [[1,2,3], [1,2,3,4]]})
    res2 = ler_arquivo(arq2)
    assert any("inconsistente" in e for e in res2.erros)

    # 3. P com d > n
    arq3 = criador_json("err3.json", {"Type": ["P"], "Data": [[100, 5], [100, 105]]})
    res3 = ler_arquivo(arq3)
    assert any("entre 0 e n" in e for e in res3.erros)

    # 4. Null no Data
    arq4 = criador_json("err4.json", {"Type": ["I", "MR"], "Data": [[5.0], [None]]})
    res4 = ler_arquivo(arq4)
    assert any("finito" in e for e in res4.erros)
    
    # 5. LSE < LIE
    arq5 = criador_json("err5.json", {"Type": ["X", "R"], "Data": [[1,2],[3,4]], "LSE": 10, "LIE": 20})
    res5 = ler_arquivo(arq5)
    assert any("maior que LIE" in e for e in res5.erros)
