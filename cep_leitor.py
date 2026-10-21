import json
import math
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum

# --- MODELOS DE DADOS ---

class FamiliaCarta(Enum):
    XBAR_R = "XBAR_R"
    I_MR = "I_MR"
    P = "P"

@dataclass
class ConjuntoDeDados:
    arquivo_origem: str
    tipos: List[str]
    familia: FamiliaCarta
    medido_em: Union[datetime, str, None] = None
    unidade: Optional[str] = None
    criado_por: Optional[str] = None
    objetivo: Optional[str] = None
    lse: Optional[float] = None
    lie: Optional[float] = None
    extras: Dict[str, Any] = field(default_factory=dict)
    
    # Dados específicos (preenchidos conforme a família)
    subgrupos: Optional[List[List[float]]] = None
    tamanho_subgrupo: Optional[int] = None
    valores: Optional[List[float]] = None
    tamanhos_amostra: Optional[List[int]] = None
    defeituosos: Optional[List[int]] = None

@dataclass
class ResultadoLeitura:
    dados: Optional[ConjuntoDeDados] = None
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)


# --- ESTRATÉGIAS DE VALIDAÇÃO POR FAMÍLIA DE CARTA ---

class ValidadorCarta:
    """Classe base para validação específica do nó 'Data'."""
    def validar_e_extrair(self, arquivo: str, data: List[List[float]], erros: List[str], avisos: List[str]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

class ValidadorXR(ValidadorCarta):
    def validar_e_extrair(self, arquivo: str, data: List[List[float]], erros: List[str], avisos: List[str]) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        n_esperado = len(data[0])
        if n_esperado < 2:
            erros.append(f"[{arquivo}] Data[0]: Esperado subgrupo com pelo menos 2 valores em carta X/R, encontrado {n_esperado}.")
            return None
            
        for i, linha in enumerate(data):
            if len(linha) != n_esperado:
                erros.append(f"[{arquivo}] Data[{i}]: Tamanho de subgrupo inconsistente. Esperado {n_esperado}, encontrado {len(linha)}.")
                return None
                
        return {"subgrupos": data, "tamanho_subgrupo": n_esperado}

class ValidadorIMR(ValidadorCarta):
    def validar_e_extrair(self, arquivo: str, data: List[List[float]], erros: List[str], avisos: List[str]) -> Optional[Dict[str, Any]]:
        valores_achatados = []
        for i, linha in enumerate(data):
            if len(linha) != 1:
                erros.append(f"[{arquivo}] Data[{i}]: Esperado exatamente 1 valor por linha na carta I/MR, encontrado {len(linha)}.")
                return None
            valores_achatados.append(linha[0])
            
        return {"valores": valores_achatados}

class ValidadorP(ValidadorCarta):
    def validar_e_extrair(self, arquivo: str, data: List[List[float]], erros: List[str], avisos: List[str]) -> Optional[Dict[str, Any]]:
        n_lista = []
        d_lista = []
        
        for i, linha in enumerate(data):
            if len(linha) != 2:
                erros.append(f"[{arquivo}] Data[{i}]: Esperado [n, d] (2 valores) na carta P, encontrado {len(linha)}.")
                return None
                
            n_val, d_val = linha
            # Aceitar 100.0 como inteiro
            if not (float(n_val).is_integer() and float(d_val).is_integer()):
                erros.append(f"[{arquivo}] Data[{i}]: Valores n e d devem ser inteiros.")
                return None
                
            n, d = int(n_val), int(d_val)
            if n <= 0:
                erros.append(f"[{arquivo}] Data[{i}]: Tamanho da amostra (n) deve ser > 0, encontrado {n}.")
                return None
            if d < 0 or d > n:
                erros.append(f"[{arquivo}] Data[{i}]: Número de defeituosos (d) deve estar entre 0 e n ({n}), encontrado {d}.")
                return None
                
            n_lista.append(n)
            d_lista.append(d)
            
        return {"tamanhos_amostra": n_lista, "defeituosos": d_lista}

# Registro de tipos suportados. Chave é uma tupla das strings (sem ordenação forçada)
REGISTRO_VALIDADORES = {
    ("X", "R"): (FamiliaCarta.XBAR_R, ValidadorXR()),
    ("I", "MR"): (FamiliaCarta.I_MR, ValidadorIMR()),
    ("P",): (FamiliaCarta.P, ValidadorP())
}

# --- FUNÇÕES PRINCIPAIS ---

def ler_arquivo(caminho: Union[str, Path], MIN_LINHAS: int = 20) -> ResultadoLeitura:
    res = ResultadoLeitura()
    caminho_path = Path(caminho)
    nome_arq = caminho_path.name
    
    if not caminho_path.is_file():
        res.erros.append(f"[{nome_arq}] Arquivo inexistente ou inacessível.")
        return res
        
    try:
        # utf-8-sig lê UTF-8 com ou sem BOM
        with caminho_path.open('r', encoding='utf-8-sig') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        res.erros.append(f"[{nome_arq}] JSON inválido: {str(e)}")
        return res
        
    if not isinstance(raw_data, dict):
        res.erros.append(f"[{nome_arq}] Raiz do arquivo deve ser um objeto JSON.")
        return res

    # 1. Extração e validação de chaves esperadas/desconhecidas
    chaves_esperadas = {"Unit", "Measured_at", "Created_by", "Type", "Goal", "LSE", "LIE", "Data"}
    extras = {}
    for k, v in raw_data.items():
        if k not in chaves_esperadas:
            res.avisos.append(f"[{nome_arq}] Chave desconhecida encontrada: '{k}'.")
            extras[k] = v
            
    for k in ["Unit", "Measured_at", "Created_by", "Goal"]:
        if k not in raw_data:
            res.avisos.append(f"[{nome_arq}] Campo esperado ausente: '{k}'.")

    # 2. Validação de Type
    raw_type = raw_data.get("Type")
    if not raw_type:
        res.erros.append(f"[{nome_arq}] Campo 'Type' ausente ou vazio.")
        return res
        
    tipos_limpos = []
    if isinstance(raw_type, str):
        t_upper = raw_type.strip().upper()
        if t_upper in ["X", "XBAR", "XR", "XBAR_R"]:
            tipos_limpos = ["X", "R"]
        elif t_upper in ["I", "IMR", "I_MR"]:
            tipos_limpos = ["I", "MR"]
        elif t_upper in ["P", "C"]:
            tipos_limpos = [t_upper]
        else:
            tipos_limpos = [t_upper]
    elif isinstance(raw_type, list):
        for t in raw_type:
            if not isinstance(t, str):
                res.erros.append(f"[{nome_arq}] Item em 'Type' não é string: {t}")
                return res
            tipos_limpos.append(t.strip().upper())
    else:
        res.erros.append(f"[{nome_arq}] Campo 'Type' deve ser string ou lista.")
        return res
        
    chave_registro = tuple(tipos_limpos)
    if chave_registro not in REGISTRO_VALIDADORES:
        res.erros.append(f"[{nome_arq}] Tipo de carta não suportado: {raw_type}")
        return res
        
    familia, validador = REGISTRO_VALIDADORES[chave_registro]

    # 3. Validação Básica de Data
    raw_matriz = raw_data.get("Data")
    if not isinstance(raw_matriz, list) or len(raw_matriz) < 2:
        res.erros.append(f"[{nome_arq}] Campo 'Data' ausente ou com menos de 2 linhas.")
        return res
        
    if len(raw_matriz) < MIN_LINHAS:
        res.avisos.append(f"[{nome_arq}] 'Data' possui {len(raw_matriz)} linhas (recomendado mínimo de {MIN_LINHAS}).")

    # Suposição anotada: Validar finitude e tipagem aqui no nível superior antes de delegar à estratégia
    data_numerica = []
    for i, linha in enumerate(raw_matriz):
        if not isinstance(linha, list):
            res.erros.append(f"[{nome_arq}] Data[{i}] não é uma lista.")
            return res
        linha_limpa = []
        for j, val in enumerate(linha):
            if type(val) not in (int, float) or type(val) is bool or not math.isfinite(val):
                res.erros.append(f"[{nome_arq}] Data[{i}][{j}]: Esperado número finito, encontrado '{val}'.")
                return res
            linha_limpa.append(float(val))
        data_numerica.append(linha_limpa)

    if res.erros:
        return res

    # 4. Validação e conversão por Estratégia (Type)
    dados_especificos = validador.validar_e_extrair(nome_arq, data_numerica, res.erros, res.avisos)
    if not dados_especificos: # Erros foram populados dentro do validador
        return res

    # 5. Validação de LSE / LIE
    lse = raw_data.get("LSE")
    lie = raw_data.get("LIE")
    
    if lse is not None and not isinstance(lse, (int, float)):
        res.erros.append(f"[{nome_arq}] LSE presente mas não numérico.")
    if lie is not None and not isinstance(lie, (int, float)):
        res.erros.append(f"[{nome_arq}] LIE presente mas não numérico.")
        
    if lse is not None and lie is not None and isinstance(lse, (int, float)) and isinstance(lie, (int, float)):
        if lse <= lie:
            res.erros.append(f"[{nome_arq}] LSE ({lse}) deve ser maior que LIE ({lie}).")

    if res.erros:
        return res

    if familia in (FamiliaCarta.XBAR_R, FamiliaCarta.I_MR):
        if lse is None or lie is None:
            res.avisos.append(f"[{nome_arq}] Tipo de carta {familia.name} sem LSE ou LIE definidos.")
        else:
            # Checagem de limites (Aviso apenas)
            fora_limite = 0
            posicoes = []
            for i, linha in enumerate(data_numerica):
                for j, val in enumerate(linha):
                    if val > lse or val < lie:
                        fora_limite += 1
                        posicoes.append(f"[{i}][{j}]")
            if fora_limite > 0:
                res.avisos.append(f"[{nome_arq}] {fora_limite} valor(es) fora dos limites [LIE, LSE] nas posições: {', '.join(posicoes[:5])}{'...' if fora_limite > 5 else ''}.")

    # 6. Parse de Data/Hora
    dt_medicao = raw_data.get("Measured_at")
    if dt_medicao:
        try:
            dt_medicao = datetime.strptime(dt_medicao, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            res.avisos.append(f"[{nome_arq}] Measured_at '{dt_medicao}' fora do formato AAAA-MM-DD HH:MM:SS.")

    # 7. Construção do Objeto de Saída
    conjunto = ConjuntoDeDados(
        arquivo_origem=nome_arq,
        tipos=tipos_limpos,
        familia=familia,
        medido_em=dt_medicao,
        unidade=raw_data.get("Unit"),
        criado_por=raw_data.get("Created_by"),
        objetivo=raw_data.get("Goal"),
        lse=float(lse) if lse is not None else None,
        lie=float(lie) if lie is not None else None,
        extras=extras,
        **dados_especificos
    )
    
    res.dados = conjunto
    return res

def ler_pasta(caminho: Union[str, Path], padrao: str = "*.json") -> List[ResultadoLeitura]:
    pasta = Path(caminho)
    resultados = []
    if pasta.is_dir():
        for arq in pasta.glob(padrao):
            resultados.append(ler_arquivo(arq))
    return resultados

def validar_json_web(conteudo_arquivo: dict) -> ResultadoLeitura:
    res = ResultadoLeitura()
    nome_arq = "upload_web"
    
    raw_data = conteudo_arquivo
    
    if not isinstance(raw_data, dict):
        res.erros.append(f"Raiz do arquivo deve ser um objeto JSON.")
        return res

    chaves_esperadas = {"Unit", "Measured_at", "Created_by", "Type", "Goal", "LSE", "LIE", "Data"}
    extras = {}
    for k, v in raw_data.items():
        if k not in chaves_esperadas:
            extras[k] = v
            
    raw_type = raw_data.get("Type")
    if not raw_type:
        res.erros.append(f"Campo 'Type' ausente ou vazio.")
        return res
        
    tipos_limpos = []
    if isinstance(raw_type, str):
        t_upper = raw_type.strip().upper()
        if t_upper in ["X", "XBAR", "XR", "XBAR_R"]:
            tipos_limpos = ["X", "R"]
        elif t_upper in ["I", "IMR", "I_MR"]:
            tipos_limpos = ["I", "MR"]
        elif t_upper in ["P", "C"]:
            tipos_limpos = [t_upper]
        else:
            tipos_limpos = [t_upper]
    elif isinstance(raw_type, list):
        for t in raw_type:
            if not isinstance(t, str):
                res.erros.append(f"Item em 'Type' não é string: {t}")
                return res
            tipos_limpos.append(t.strip().upper())
    else:
        res.erros.append(f"Campo 'Type' deve ser string ou lista.")
        return res
        
    chave_registro = tuple(tipos_limpos)
    if chave_registro not in REGISTRO_VALIDADORES:
        res.erros.append(f"Tipo desconhecido: {raw_type}")
        return res
        
    familia, validador = REGISTRO_VALIDADORES[chave_registro]

    raw_matriz = raw_data.get("Data")
    if not isinstance(raw_matriz, list) or len(raw_matriz) < 2:
        res.erros.append(f"Campo 'Data' ausente ou com menos de 2 linhas.")
        return res
        
    data_numerica = []
    for i, linha in enumerate(raw_matriz):
        if not isinstance(linha, list):
            res.erros.append(f"Data[{i}] não é uma lista.")
            return res
        linha_limpa = []
        for j, val in enumerate(linha):
            if type(val) not in (int, float) or type(val) is bool or not math.isfinite(val):
                res.erros.append(f"Data[{i}][{j}]: Esperado número finito, encontrado '{val}'.")
                return res
            linha_limpa.append(float(val))
        data_numerica.append(linha_limpa)

    if res.erros:
        return res

    dados_especificos = validador.validar_e_extrair(nome_arq, data_numerica, res.erros, res.avisos)
    if not dados_especificos: 
        return res

    lse = raw_data.get("LSE")
    lie = raw_data.get("LIE")
    
    if lse is not None and lie is not None and isinstance(lse, (int, float)) and isinstance(lie, (int, float)):
        if lse <= lie:
            res.erros.append(f"LSE ({lse}) deve ser maior que LIE ({lie}).")

    if res.erros:
        return res

    dt_medicao = raw_data.get("Measured_at")
    if dt_medicao:
        try:
            dt_medicao = datetime.strptime(dt_medicao, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    conjunto = ConjuntoDeDados(
        arquivo_origem=nome_arq,
        tipos=tipos_limpos,
        familia=familia,
        medido_em=dt_medicao,
        unidade=raw_data.get("Unit"),
        criado_por=raw_data.get("Created_by"),
        objetivo=raw_data.get("Goal"),
        lse=float(lse) if lse is not None else None,
        lie=float(lie) if lie is not None else None,
        extras=extras,
        **dados_especificos
    )
    
    res.dados = conjunto
    return res
