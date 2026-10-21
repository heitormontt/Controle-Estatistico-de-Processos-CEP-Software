import math
import numpy as np
import pandas as pd
from scipy.stats import norm, binom, poisson
import json
import copy
from datetime import datetime

# Constantes Tabeladas
d2_tab = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078, 11: 3.173, 12: 3.258, 13: 3.336, 14: 3.407, 15: 3.472, 16: 3.532, 17: 3.588, 18: 3.640, 19: 3.689, 20: 3.735, 21: 3.778, 22: 3.819, 23: 3.858, 24: 3.895, 25: 3.931}
A2_tab = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308, 11: 0.285, 12: 0.266, 13: 0.249, 14: 0.235, 15: 0.223, 16: 0.212, 17: 0.203, 18: 0.194, 19: 0.187, 20: 0.180, 21: 0.173, 22: 0.167, 23: 0.162, 24: 0.157, 25: 0.153}
D3_tab = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223, 11: 0.256, 12: 0.283, 13: 0.307, 14: 0.328, 15: 0.347, 16: 0.363, 17: 0.378, 18: 0.391, 19: 0.403, 20: 0.415, 21: 0.425, 22: 0.434, 23: 0.443, 24: 0.451, 25: 0.459}
D4_tab = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777, 11: 1.744, 12: 1.717, 13: 1.693, 14: 1.672, 15: 1.653, 16: 1.637, 17: 1.622, 18: 1.608, 19: 1.597, 20: 1.585, 21: 1.575, 22: 1.566, 23: 1.557, 24: 1.548, 25: 1.541}

def parse_numero(val):
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        try: return float(val.replace(",", "."))
        except: return None
    return None

def aplicar_regras(valores, LC, LSC, LIC, tipo_carta='X', removidos_idx=None):
    if removidos_idx is None: removidos_idx = set()
    sinais = {}
    for i in range(len(valores)):
        sinais[i] = []
        if valores[i] is None: continue
        z = (valores[i] - LC[i]) / ((LSC[i] - LC[i]) / 3) if (LSC[i] - LC[i]) > 0 else 0
        
        # R1: 1 ponto fora (> 3)
        if abs(z) > 3: sinais[i].append("R1")
        
        if tipo_carta in ['R', 'AM', 'P', 'C']:
            pass
        else:
            # R2: 2 de 3 consecutivos > 2 ou < -2
            if i >= 2:
                janela = [valores[j] for j in range(i-2, i+1)]
                if None not in janela:
                    zs = [(janela[k] - LC[i-2+k]) / ((LSC[i-2+k] - LC[i-2+k]) / 3) for k in range(3)]
                    if sum(1 for z_val in zs if z_val > 2) >= 2 or sum(1 for z_val in zs if z_val < -2) >= 2:
                        sinais[i].append("R2")
            # R3: 4 de 5 consecutivos > 1 ou < -1
            if i >= 4:
                janela = [valores[j] for j in range(i-4, i+1)]
                if None not in janela:
                    zs = [(janela[k] - LC[i-4+k]) / ((LSC[i-4+k] - LC[i-4+k]) / 3) for k in range(5)]
                    if sum(1 for z_val in zs if z_val > 1) >= 4 or sum(1 for z_val in zs if z_val < -1) >= 4:
                        sinais[i].append("R3")
                        
        # R4: 8 pontos do mesmo lado da LC
        if i >= 7:
            janela = [valores[j] for j in range(i-7, i+1)]
            if None not in janela:
                diffs = [janela[k] - LC[i-7+k] for k in range(8)]
                if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                    sinais[i].append("R4")
                    
    return sinais

def calcular_limites(tipo, dados_atuais, ns, removidos, prm=None):
    m = len(dados_atuais)
    idx_ativos = [i for i in range(m) if i not in removidos]
    n_ativos = sum(1 for _ in idx_ativos)
    if n_ativos < 2 and prm is None: return None
    
    res = {"LC_1": [0]*m, "LSC_1": [0]*m, "LIC_1": [0]*m, 
           "LC_2": [None]*m if tipo in ["P", "C"] else [0]*m, 
           "LSC_2": [None]*m if tipo in ["P", "C"] else [0]*m, 
           "LIC_2": [None]*m if tipo in ["P", "C"] else [0]*m, 
           "val_1": [None]*m, "val_2": [None]*m, "memoria": {}}
           
    if tipo == "X" or tipo == "R":
        xbars, rs = [], []
        for i in range(m):
            am = dados_atuais[i]
            xbars.append(np.mean(am))
            rs.append(np.max(am) - np.min(am))
            res["val_1"][i] = xbars[-1]
            res["val_2"][i] = rs[-1]
            
        if prm is None:
            Xbb = np.average([xbars[i] for i in idx_ativos], weights=[ns[i] for i in idx_ativos])
            Rbar = np.mean([rs[i] for i in idx_ativos])
            sigma_hat = np.mean([rs[i]/d2_tab[ns[i]] for i in idx_ativos])
        else:
            Xbb = prm["LC_X"]
            Rbar = prm["Rbar"]
            sigma_hat = prm["sigma_hat"]

        res["parametros"] = {"Xbb": Xbb, "Rbar": Rbar, "sigma_hat": sigma_hat}
        res["memoria"]["X"] = f"Xbb = {Xbb:.5f}; Rbar = {Rbar:.5f}; sigma_hat = {sigma_hat:.5f}"
        
        for i in range(m):
            n = ns[i]
            if prm is None or "LSC_X" not in prm:
                lsc_x = Xbb + A2_tab[n]*Rbar
                lic_x = Xbb - A2_tab[n]*Rbar
                lsc_r = D4_tab[n]*Rbar
                lic_r = D3_tab[n]*Rbar
            else:
                lsc_x = prm["LSC_X"] if not isinstance(prm["LSC_X"], dict) else prm["LSC_X"].get(str(n), prm["LSC_X"])
                lic_x = prm["LIC_X"] if not isinstance(prm["LIC_X"], dict) else prm["LIC_X"].get(str(n), prm["LIC_X"])
                lsc_r = prm.get("LSC_R", D4_tab[n]*Rbar)
                lic_r = prm.get("LIC_R", D3_tab[n]*Rbar)
                if isinstance(lsc_r, dict): lsc_r = lsc_r.get(str(n), lsc_r)
                if isinstance(lic_r, dict): lic_r = lic_r.get(str(n), lic_r)
                
            res["LC_1"][i] = Xbb
            res["LSC_1"][i] = lsc_x
            res["LIC_1"][i] = lic_x
            res["LC_2"][i] = Rbar
            res["LSC_2"][i] = lsc_r
            res["LIC_2"][i] = max(0, lic_r)
            
    elif tipo == "IMR":
        xs, ams = [], []
        for i in range(m):
            xs.append(dados_atuais[i][0])
            res["val_1"][i] = xs[-1]
            if i == 0 or i in removidos or (i-1) in removidos:
                ams.append(None)
            else:
                ams.append(abs(xs[i] - xs[i-1]))
            res["val_2"][i] = ams[-1]
            
        if prm is None:
            xbar = np.mean([xs[i] for i in idx_ativos])
            am_validos = [am for i, am in enumerate(ams) if am is not None and i in idx_ativos]
            if len(am_validos) > 0:
                AMbar = np.mean(am_validos)
            else:
                AMbar = 0.0
            sigma_hat = AMbar / 1.128
        else:
            xbar = prm["LC_X"]
            AMbar = prm["Rbar"]
            sigma_hat = prm["sigma_hat"]

        res["parametros"] = {"Xbb": xbar, "Rbar": AMbar, "sigma_hat": sigma_hat}
        res["memoria"]["IMR"] = f"xbar = {xbar:.5f}; AMbar = {AMbar:.5f}; sigma_hat = {sigma_hat:.5f}"
        
        for i in range(m):
            if prm is None or "LSC_X" not in prm:
                lsc_x = xbar + 2.660 * AMbar
                lic_x = xbar - 2.660 * AMbar
                lsc_r = 3.267 * AMbar
                lic_r = 0.0
            else:
                lsc_x = prm["LSC_X"]
                lic_x = prm["LIC_X"]
                lsc_r = prm.get("LSC_R", 3.267 * AMbar)
                lic_r = prm.get("LIC_R", 0.0)
                
            res["LC_1"][i] = xbar
            res["LSC_1"][i] = lsc_x
            res["LIC_1"][i] = lic_x
            res["LC_2"][i] = AMbar
            res["LSC_2"][i] = lsc_r
            res["LIC_2"][i] = max(0, lic_r)

    elif tipo == "P":
        xs = [dados_atuais[i][0] for i in range(m)]
        for i in range(m):
            res["val_1"][i] = xs[i] / ns[i]
            
        if prm is None:
            soma_x = sum([xs[i] for i in idx_ativos])
            soma_n = sum([ns[i] for i in idx_ativos])
            pbar = soma_x / soma_n if soma_n > 0 else 0
        else:
            pbar = prm["LC_X"]
            
        res["parametros"] = {"pbar": pbar, "sigma_hat": None}
        res["memoria"]["P"] = f"pbar = {pbar:.5f}"
        
        for i in range(m):
            n = ns[i]
            sig = math.sqrt(pbar*(1-pbar)/n)
            lsc_x = pbar + 3*sig
            lic_x = max(0, pbar - 3*sig)
            if prm is not None and "LSC_X" in prm and not isinstance(prm["LSC_X"], dict):
                 lsc_x = prm["LSC_X"]
                 lic_x = prm.get("LIC_X", lic_x)
            res["LC_1"][i] = pbar
            res["LSC_1"][i] = min(1.0, lsc_x)
            res["LIC_1"][i] = max(0.0, lic_x)
            
    elif tipo == "C":
        cs = [dados_atuais[i][0] for i in range(m)]
        for i in range(m):
            res["val_1"][i] = cs[i]
            
        if prm is None:
            cbar = np.mean([cs[i] for i in idx_ativos])
        else:
            cbar = prm["LC_X"]
            
        res["parametros"] = {"cbar": cbar, "sigma_hat": None}
        res["memoria"]["C"] = f"cbar = {cbar:.5f}"
        
        for i in range(m):
            sig = math.sqrt(cbar)
            lsc_x = cbar + 3*sig
            lic_x = max(0, cbar - 3*sig)
            if prm is not None and "LSC_X" in prm:
                 lsc_x = prm["LSC_X"]
                 lic_x = prm.get("LIC_X", lic_x)
            res["LC_1"][i] = cbar
            res["LSC_1"][i] = lsc_x
            res["LIC_1"][i] = max(0.0, lic_x)
            
    return res

def calibrar(dados_parsed):
    removidos = set()
    historico = []
    
    tipo = dados_parsed["Type"]
    dados = dados_parsed["Data"]
    ns = dados_parsed["n_i"]
    
    for it in range(21):
        res = calcular_limites(tipo, dados, ns, removidos)
        if res is None: break
        
        sinais_1 = aplicar_regras(res["val_1"], res["LC_1"], res["LSC_1"], res["LIC_1"], tipo_carta='X' if tipo != 'P' and tipo != 'C' else tipo, removidos_idx=removidos)
        sinais_2 = {}
        if tipo in ["X", "R", "IMR"]:
            sinais_2 = aplicar_regras(res["val_2"], res["LC_2"], res["LSC_2"], res["LIC_2"], tipo_carta='R' if tipo != 'IMR' else 'AM', removidos_idx=removidos)
            
        novos_removidos = set()
        detalhe_rem = []
        for i in range(len(dados)):
            if i in removidos: continue
            if "R1" in sinais_1.get(i, []):
                novos_removidos.add(i)
                detalhe_rem.append(f"Subgrupo {i+1} (Carta principal)")
            elif "R1" in sinais_2.get(i, []):
                novos_removidos.add(i)
                detalhe_rem.append(f"Subgrupo {i+1} (Carta amplitude)")
                
        historico.append({
            "iteracao": it,
            "removidos_antes": list(removidos),
            "novos_removidos": detalhe_rem,
            "parametros": res["parametros"]
        })
        
        if not novos_removidos:
            break
            
        removidos.update(novos_removidos)
        if len(dados) - len(removidos) < 2:
            break
            
    res_final = calcular_limites(tipo, dados, ns, removidos)
    sinais_finais_1 = aplicar_regras(res_final["val_1"], res_final["LC_1"], res_final["LSC_1"], res_final["LIC_1"], tipo_carta='X' if tipo != 'P' and tipo != 'C' else tipo)
    if tipo in ["X", "R", "IMR"]:
        sinais_finais_2 = aplicar_regras(res_final["val_2"], res_final["LC_2"], res_final["LSC_2"], res_final["LIC_2"], tipo_carta='R' if tipo != 'IMR' else 'AM')
    else:
        sinais_finais_2 = {}
        
    return {
        "limites": res_final,
        "sinais_1": sinais_finais_1,
        "sinais_2": sinais_finais_2,
        "historico": historico,
        "removidos": removidos,
        "dados_parsed": dados_parsed
    }

def analisar_capacidade(dados_parsed, res_limites):
    tipo = dados_parsed["Type"]
    if tipo not in ["X", "R", "IMR"]: return None
    LSE = dados_parsed.get("LSE")
    LIE = dados_parsed.get("LIE")
    if LSE is None and LIE is None: return None
    
    dados = dados_parsed["Data"]
    removidos = res_limites.get("removidos", set())
    todas_medicoes = []
    for i, am in enumerate(dados):
        if i not in removidos:
            todas_medicoes.extend(am)
            
    if not todas_medicoes: return None
    
    s = np.std(todas_medicoes, ddof=1) if len(todas_medicoes) > 1 else 0
    mu_hat = res_limites["limites"]["parametros"]["Xbb"]
    sigma_hat = res_limites["limites"]["parametros"]["sigma_hat"]
    
    cap = {"mu_hat": mu_hat, "sigma_hat": sigma_hat, "s": s, "LSE": LSE, "LIE": LIE}
    
    if sigma_hat > 0:
        if LSE is not None and LIE is not None:
            cap["Cp"] = (LSE - LIE) / (6 * sigma_hat)
            cap["Pp"] = (LSE - LIE) / (6 * s) if s > 0 else None
            
        if LSE is not None:
            cap["Cpu"] = (LSE - mu_hat) / (3 * sigma_hat)
            cap["Ppu"] = (LSE - mu_hat) / (3 * s) if s > 0 else None
        else:
            cap["Cpu"] = cap["Ppu"] = float('inf')
            
        if LIE is not None:
            cap["Cpl"] = (mu_hat - LIE) / (3 * sigma_hat)
            cap["Ppl"] = (mu_hat - LIE) / (3 * s) if s > 0 else None
        else:
            cap["Cpl"] = cap["Ppl"] = float('inf')
            
        cap["Cpk"] = min(cap["Cpu"], cap["Cpl"])
        cap["Ppk"] = min(cap["Ppu"], cap["Ppl"])
        
        ppm_exp = 0
        if LSE is not None: ppm_exp += (1 - norm.cdf(LSE, loc=mu_hat, scale=sigma_hat)) * 1e6
        if LIE is not None: ppm_exp += norm.cdf(LIE, loc=mu_hat, scale=sigma_hat) * 1e6
        cap["ppm_esperado"] = ppm_exp
        
    out_count = 0
    for v in todas_medicoes:
        if LSE is not None and v > LSE: out_count += 1
        if LIE is not None and v < LIE: out_count += 1
    cap["ppm_observado"] = (out_count / len(todas_medicoes)) * 1e6
    
    return cap

def analise_deslocamento(dados_parsed, res_limites, delta0=None):
    tipo = dados_parsed["Type"]
    if delta0 is None: delta0 = dados_parsed.get("Delta0")
    if delta0 is None: delta0 = 0.0
    
    prm = res_limites["limites"]["parametros"]
    sigma_hat = prm.get("sigma_hat")
    
    res = {"delta0": delta0, "tabela": []}
    
    if tipo in ["X", "R", "IMR"] and sigma_hat:
        ks = [0, 0.5, 1, 1.5, 2, 2.5, 3]
        for k in ks:
            d0 = k * sigma_hat
            beta_quadro = norm.cdf(d0/sigma_hat + 3) - norm.cdf(d0/sigma_hat - 3)
            linha = {"k": k, "delta0": d0, "beta_quadro": beta_quadro, "poder_quadro": 1-beta_quadro, "arl1_quadro": 1/(1-beta_quadro) if beta_quadro < 1 else float('inf')}
            
            n_mean = np.mean(dados_parsed["n_i"])
            if tipo == "X" and n_mean > 1:
                Xbb = prm["Xbb"]
                LSC = res_limites["limites"]["LSC_1"][0]
                LIC = res_limites["limites"]["LIC_1"][0]
                Z_sup = (LSC - (Xbb + d0)) / (sigma_hat / math.sqrt(n_mean))
                Z_inf = (LIC - (Xbb + d0)) / (sigma_hat / math.sqrt(n_mean))
                beta_carta = norm.cdf(Z_sup) - norm.cdf(Z_inf)
                linha["beta_carta"] = beta_carta
                linha["poder_carta"] = 1-beta_carta
                linha["arl1_carta"] = 1/(1-beta_carta) if beta_carta < 1 else float('inf')
            else:
                linha["beta_carta"] = beta_quadro
                
            res["tabela"].append(linha)
            
    return res

def processar_cep(json_str_or_dict, source_file=None):
    if isinstance(json_str_or_dict, str): d = json.loads(json_str_or_dict)
    else: d = json_str_or_dict
    
    from cep_leitor import validar_json_web, FamiliaCarta
    res_leitura = validar_json_web(d)
    
    if res_leitura.erros:
        raise ValueError("Erros de validação: " + " | ".join(res_leitura.erros))
        
    conj = res_leitura.dados
    
    if conj.familia == FamiliaCarta.XBAR_R: tipo_core = "X"
    elif conj.familia == FamiliaCarta.I_MR: tipo_core = "IMR"
    elif conj.familia == FamiliaCarta.P: tipo_core = "P"
    else: tipo_core = "X"
    
    parsed_data = []
    ns = []
    if conj.familia == FamiliaCarta.XBAR_R:
        parsed_data = conj.subgrupos
        ns = [conj.tamanho_subgrupo] * len(conj.subgrupos)
    elif conj.familia == FamiliaCarta.I_MR:
        parsed_data = [[x] for x in conj.valores]
        ns = [1] * len(conj.valores)
    elif conj.familia == FamiliaCarta.P:
        # A engine antiga para P exige [[defeituosos, tamanho], ...]
        for n_val, d_val in zip(conj.tamanhos_amostra, conj.defeituosos):
            parsed_data.append([d_val, n_val])
            ns.append(n_val)
            
    goal = conj.objetivo or "Calibrar"
    goal_lower = goal.lower().strip()
    if goal_lower.startswith("acomp") or goal_lower.startswith("monit") or goal_lower.startswith("segu"):
        goal = "Acompanhar"
    else:
        goal = "Calibrar"
        
    dados_parsed = {
        "Type": tipo_core,
        "Goal": goal,
        "Data": parsed_data,
        "n_i": ns,
        "raw_data_original": d.get("Data", []),
        "LSE": conj.lse,
        "LIE": conj.lie,
        "Label": d.get("Label", ""),
        "Unit": conj.unidade or "",
        "Measured_at": d.get("Measured_at", ""),
        "Created_by": conj.criado_por or "",
        "avisos": res_leitura.avisos,
        "source_file": source_file,
        "Delta0": conj.extras.get("Delta0")
    }
    
    # Repassando os limites calibrados se existirem para Fase II
    for lim_key in ["LSC", "LIC", "LC", "Calibration"]:
        if lim_key in d: dados_parsed[lim_key] = d[lim_key]
        
    if dados_parsed["Goal"] == "Acompanhar":
        if "LSC" not in dados_parsed or "LIC" not in dados_parsed:
            # Em vez de dar crash, vamos ser inteligentes: se não tem limites, forçamos a Calibrar e avisamos.
            dados_parsed["Goal"] = "Calibrar"
            dados_parsed["avisos"].append(
                "O objetivo estava como 'Acompanhar/Monitorar', mas o JSON não possuía LSC e LIC. "
                "O software alterou automaticamente para 'Calibrar' (Fase I)."
            )

    if dados_parsed["Goal"] == "Calibrar":
        res_calib = calibrar(dados_parsed)
    else:
        # Acompanhar - A logica do acompanhar era INLINE no else da engine original
        prm = {}
        tipo = dados_parsed["Type"]
        
        def get_lim(chave, carta, fallback=None):
            val = dados_parsed.get(chave)
            if isinstance(val, dict):
                if carta in val: return val[carta]
                if fallback and fallback in val: return val[fallback]
                return None
            return val
            
        carta_1 = "X" if tipo in ["X", "R"] else ("I" if tipo == "IMR" else tipo)
        prm["LSC_X"] = get_lim("LSC", carta_1, fallback="X")
        prm["LIC_X"] = get_lim("LIC", carta_1, fallback="X")
        prm["LC_X"] = get_lim("LC", carta_1, fallback="X")
        
        if tipo in ["X", "R", "IMR"]:
            carta_2 = "R" if tipo != "IMR" else "AM"
            prm["LSC_R"] = get_lim("LSC", carta_2, fallback="R" if tipo == "IMR" else "AM")
            prm["LIC_R"] = get_lim("LIC", carta_2, fallback="R" if tipo == "IMR" else "AM")
            prm["LC_R"] = get_lim("LC", carta_2, fallback="R" if tipo == "IMR" else "AM")
        
        n_mean = int(np.round(np.mean(dados_parsed["n_i"]))) if dados_parsed["n_i"] else 1
        n_mean = max(2, min(n_mean, 25))
        
        if tipo in ["X", "R"]:
            if prm["LC_X"] is None and prm["LSC_X"] is not None and prm["LIC_X"] is not None:
                prm["LC_X"] = (prm["LSC_X"] + prm["LIC_X"])/2
            if prm["LSC_X"] is not None and prm["LIC_X"] is not None:
                prm["Rbar"] = (prm["LSC_X"] - prm["LIC_X"]) / (2 * A2_tab[n_mean])
                prm["sigma_hat"] = prm["Rbar"] / d2_tab[n_mean]
            elif prm.get("LSC_R") is not None:
                prm["Rbar"] = prm["LSC_R"] / D4_tab[n_mean]
                prm["sigma_hat"] = prm["Rbar"] / d2_tab[n_mean]
        elif tipo == "IMR":
            if prm["LC_X"] is None and prm["LSC_X"] is not None and prm["LIC_X"] is not None:
                prm["LC_X"] = (prm["LSC_X"] + prm["LIC_X"])/2
            if prm["LSC_X"] is not None and prm["LIC_X"] is not None:
                prm["Rbar"] = (prm["LSC_X"] - prm["LIC_X"]) / (2 * 2.660) # AMbar
                prm["sigma_hat"] = prm["Rbar"] / 1.128
            elif prm.get("LSC_R") is not None:
                prm["Rbar"] = prm["LSC_R"] / 3.267
                prm["sigma_hat"] = prm["Rbar"] / 1.128
        elif tipo in ["P", "C"]:
            if prm["LC_X"] is None and prm["LSC_X"] is not None and prm["LIC_X"] is not None:
                prm["LC_X"] = (prm["LSC_X"] + prm["LIC_X"])/2

        limites = calcular_limites(tipo, dados_parsed["Data"], dados_parsed["n_i"], set(), prm=prm)
        sinais_1 = aplicar_regras(limites["val_1"], limites["LC_1"], limites["LSC_1"], limites["LIC_1"], tipo_carta='X' if tipo not in ['P', 'C'] else tipo)
        if tipo in ["X", "R", "IMR"]:
             sinais_2 = aplicar_regras(limites["val_2"], limites["LC_2"], limites["LSC_2"], limites["LIC_2"], tipo_carta='R' if tipo != 'IMR' else 'AM')
        else: sinais_2 = {}
             
        res_calib = {
            "limites": limites,
            "sinais_1": sinais_1,
            "sinais_2": sinais_2,
            "historico": [],
            "removidos": set(),
            "dados_parsed": dados_parsed
        }
        
    cap = analisar_capacidade(dados_parsed, res_calib)
    desloc = analise_deslocamento(dados_parsed, res_calib)
    
    return {
        "resultado": res_calib,
        "capacidade": cap,
        "deslocamento": desloc
    }

def to_native(val):
    if val is None: return None
    if isinstance(val, (np.floating, float)): return float(val)
    if isinstance(val, (np.integer, int)): return int(val)
    if isinstance(val, (np.bool_, bool)): return bool(val)
    if isinstance(val, np.ndarray): return [to_native(x) for x in val.tolist()]
    if isinstance(val, (list, tuple)): return [to_native(x) for x in val]
    if isinstance(val, dict): return {str(k): to_native(v) for k, v in val.items()}
    return val

def formatar_bloco_data(data):
    if not isinstance(data, list):
        return json.dumps(to_native(data), ensure_ascii=False)
    if len(data) == 0:
        return "[]"
    
    # Se for lista de listas (subgrupos)
    if any(isinstance(item, list) for item in data):
        linhas = []
        for i, item in enumerate(data):
            virgula = "," if i < len(data) - 1 else ""
            item_native = to_native(item)
            item_str = json.dumps(item_native, ensure_ascii=False)
            linhas.append(f"    {item_str}{virgula}")
        return "[\n" + "\n".join(linhas) + "\n  ]"
    
    # Se for lista plana (ex.: IMR ou C em formato plano)
    linhas = []
    chunk_size = 10
    total = len(data)
    for i in range(0, total, chunk_size):
        chunk = to_native(data[i:i+chunk_size])
        chunk_str = ", ".join(json.dumps(x, ensure_ascii=False) for x in chunk)
        virgula = "," if (i + chunk_size) < total else ""
        linhas.append(f"    {chunk_str}{virgula}")
    return "[\n" + "\n".join(linhas) + "\n  ]"

def montar_json_calibracao(ret, source_file=None):
    res_calib = ret["resultado"]
    dados_parsed = res_calib["dados_parsed"]
    
    raw_data = dados_parsed.get("raw_data_original")
    if raw_data is None:
        raw_data = dados_parsed.get("Data")
    raw_data = to_native(raw_data)
    
    tipo = dados_parsed["Type"]
    
    doc = {
        "Type": tipo,
        "Goal": "Acompanhar"
    }
    
    for campo in ["Label", "Unit", "Measured_at", "Created_by", "LSE", "LIE", "Delta0"]:
        if campo in dados_parsed and dados_parsed[campo] is not None:
            doc[campo] = to_native(dados_parsed[campo])
            
    lsc1 = to_native(res_calib["limites"]["LSC_1"][0])
    lic1 = to_native(res_calib["limites"]["LIC_1"][0])
    lc1 = to_native(res_calib["limites"]["LC_1"][0])
    
    if tipo in ["X", "R"]:
        lsc2 = to_native(res_calib["limites"]["LSC_2"][0])
        lic2 = to_native(res_calib["limites"]["LIC_2"][0])
        doc["LSC"] = {"X": lsc1, "R": lsc2}
        doc["LIC"] = {"X": lic1, "R": lic2}
        doc["LC"] = {"X": lc1}
    elif tipo == "IMR":
        lsc2 = to_native(res_calib["limites"]["LSC_2"][0])
        lic2 = to_native(res_calib["limites"]["LIC_2"][0])
        doc["LSC"] = {"I": lsc1, "AM": lsc2}
        doc["LIC"] = {"I": lic1, "AM": lic2}
        doc["LC"] = {"I": lc1}
    else:
        # P e C
        doc["LSC"] = lsc1
        doc["LIC"] = lic1
        doc["LC"] = lc1
        
    removidos_base1 = sorted([int(idx) + 1 for idx in res_calib.get("removidos", set())])
    doc["Calibration"] = {
        "Data_is_original": True,
        "Removed_subgroups": removidos_base1,
        "Source_file": source_file or dados_parsed.get("source_file", ""),
        "Generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    base_json = json.dumps(doc, indent=2, ensure_ascii=False)
    
    if base_json.endswith("\n}"):
        json_sem_fim = base_json[:-2]
    elif base_json.endswith("}"):
        json_sem_fim = base_json[:-1]
    else:
        json_sem_fim = base_json
        
    bloco_data = formatar_bloco_data(raw_data)
    final_json = json_sem_fim + ',\n  "Data": ' + bloco_data + '\n}\n'
    return final_json
