import json
import pytest
from cep_core import processar_cep, montar_json_calibracao

def test_exemplo_calibrar_x():
    with open("exemplos/exemplo_x_calibrar.json", "r", encoding="utf-8-sig") as f:
         dados = json.load(f)
    ret = processar_cep(dados)
    res = ret["resultado"]
    assert len(res["removidos"]) == 3
    assert 1 in res["removidos"]  # 0-indexed, subgrupo 2
    assert 8 in res["removidos"]  # 0-indexed, subgrupo 9
    assert 16 in res["removidos"] # 0-indexed, subgrupo 17
    
    cap = ret["capacidade"]
    assert round(cap["Cp"], 2) == 19.27
    assert round(cap["Cpk"], 3) == 1.494

def test_ida_volta_calibracao_x():
    # Teste A: Calibração de X e releitura em Fase II
    with open("exemplos/dados_simulado_prova_1_0226.json", "r", encoding="utf-8-sig") as f:
        dados_orig = json.load(f)
        
    ret_calib = processar_cep(dados_orig, source_file="dados_simulado_prova_1_0226.json")
    calib_json = montar_json_calibracao(ret_calib, source_file="dados_simulado_prova_1_0226.json")
    
    dados_fase2 = json.loads(calib_json)
    assert dados_fase2["Data"] == dados_orig["Data"]
    assert dados_fase2["Goal"] == "Acompanhar"
    assert dados_fase2["Calibration"]["Data_is_original"] is True
    assert dados_fase2["Calibration"]["Removed_subgroups"] == [2, 9, 17]
    
    ret_fase2 = processar_cep(dados_fase2)
    lim_f2 = ret_fase2["resultado"]["limites"]
    
    assert abs(lim_f2["LIC_1"][0] - 4.94963) < 1e-4
    assert abs(lim_f2["LSC_1"][0] - 4.97284) < 1e-4
    assert abs(lim_f2["LSC_2"][0] - 0.04253) < 1e-4
    
    s1 = ret_fase2["resultado"]["sinais_1"]
    s2 = ret_fase2["resultado"]["sinais_2"]
    
    # 0-indexed: subgrupo 2 é idx 1, subgrupo 17 é idx 16, subgrupo 9 é idx 8
    assert "R1" in s1[1]   # subgrupo 2 na carta X
    assert "R1" in s1[16]  # subgrupo 17 na carta X
    assert "R1" in s2[8]   # subgrupo 9 na carta R

def test_ida_volta_tipos_r_imr_p_c():
    # Teste B: Ida e volta para tipos R, IMR, P, C
    casos = [
        {
            "Type": "R",
            "Goal": "Calibrar",
            "Data": [
                [10.1, 10.3, 10.2, 10.0, 10.1],
                [10.2, 10.1, 10.3, 10.2, 10.2],
                [10.0, 10.1, 10.2, 10.1, 10.0],
                [10.3, 10.2, 10.1, 10.2, 10.3]
            ]
        },
        {
            "Type": "IMR",
            "Goal": "Calibrar",
            "Label": "Viscosidade do Polímero",
            "Unit": "cP",
            "Data": [300.5, 302.1, 299.8, 301.4, 300.9, 303.0, 298.7, 301.2]
        },
        {
            "Type": "P",
            "Goal": "Calibrar",
            "Data": [
                [2, 50],
                [3, 50],
                [1, 50],
                [4, 50],
                [2, 50]
            ]
        },
        {
            "Type": "C",
            "Goal": "Calibrar",
            "Data": [
                [2], [5], [3], [4], [8], [1], [4], [3]
            ]
        }
    ]
    for c in casos:
        ret_c = processar_cep(c, source_file="teste.json")
        json_str = montar_json_calibracao(ret_c, source_file="teste.json")
        d_reloaded = json.loads(json_str)
        assert d_reloaded["Data"] == c["Data"]
        
        ret_f2 = processar_cep(d_reloaded)
        lim_f2 = ret_f2["resultado"]["limites"]
        lim_c = ret_c["resultado"]["limites"]
        
        assert abs(lim_f2["LSC_1"][0] - lim_c["LSC_1"][0]) < 1e-4
        assert abs(lim_f2["LIC_1"][0] - lim_c["LIC_1"][0]) < 1e-4
        assert abs(lim_f2["LC_1"][0] - lim_c["LC_1"][0]) < 1e-4

def test_calibracao_antiga_sem_data_falha():
    # Teste E: Arquivo sem Data falha com mensagem explicativa
    dados = {
        "Type": "IMR",
        "Goal": "Acompanhar",
        "Label": "Viscosidade do Polímero",
        "Unit": "cP",
        "LSE": 315.0,
        "LIE": 290.0,
        "LSC": {"I": 325.6, "AM": 27.0},
        "LIC": {"I": 281.5, "AM": 0},
        "LC": {"I": 303.5}
    }
    with pytest.raises(ValueError, match="não contém a chave 'Data'"):
        processar_cep(dados)
