import json
from fpdf import FPDF
import tempfile
import os

def formatar_numero(valor, casas=5):
    if valor is None: return "-"
    try:
        return f"{valor:.{casas}f}".replace(".", ",")
    except:
        return str(valor)

class RelatorioCEP(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatório de Controle Estatístico de Processo', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf(retorno_cep, caminho_grafico, arquivo_saida="relatorio.pdf", caminho_grafico_capacidade=None):
    pdf = RelatorioCEP()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    res = retorno_cep["resultado"]
    dados_parsed = res["dados_parsed"]
    cap = retorno_cep["capacidade"]
    desl = retorno_cep["deslocamento"]
    
    # Metadados
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Metadados da Análise', 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 6, f"Rótulo: {dados_parsed.get('Label', '-')}", 0, 1)
    pdf.cell(0, 6, f"Tipo de Carta: {dados_parsed.get('Type')} | Objetivo: {dados_parsed.get('Goal')}", 0, 1)
    pdf.cell(0, 6, f"Unidade: {dados_parsed.get('Unit', '-')} | Criado por: {dados_parsed.get('Created_by', '-')}", 0, 1)
    pdf.cell(0, 6, f"Data da Medição: {dados_parsed.get('Measured_at', '-')}", 0, 1)
    pdf.ln(5)
    
    # Parâmetros Calculados
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Parâmetros (Última Iteração)', 0, 1)
    pdf.set_font("Arial", size=10)
    if "memoria" in res["limites"]:
        for k, v in res["limites"]["memoria"].items():
            pdf.cell(0, 6, f"{k}: {v}", 0, 1)
    pdf.ln(5)
    
    # Gráfico
    if caminho_grafico and os.path.exists(caminho_grafico):
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Cartas de Controle', 0, 1)
        pdf.image(caminho_grafico, x=10, w=190)
        pdf.ln(5)
        
    # Sinais e Removidos
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, 'Status por Subgrupo', 0, 1)
    pdf.set_font("Arial", size=9)
    m = len(dados_parsed["Data"])
    for i in range(m):
        s1 = res["sinais_1"].get(i, [])
        s2 = res["sinais_2"].get(i, [])
        status = "REMOVIDO" if i in res["removidos"] else ("FORA" if "R1" in s1 or "R1" in s2 else ("ALERTA" if s1 or s2 else "OK"))
        regras = ",".join(s1 + s2)
        val1 = formatar_numero(res["limites"]["val_1"][i])
        val2 = formatar_numero(res["limites"]["val_2"][i]) if res["limites"]["val_2"][i] is not None else "-"
        pdf.cell(0, 5, f"Subgrupo {i+1}: Val1={val1} | Val2={val2} | Status: {status} | Regras: {regras}", 0, 1)
    pdf.ln(5)
    
    # Capacidade
    if cap:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Análise de Capacidade', 0, 1)
        pdf.set_font("Arial", size=10)
        for k, v in cap.items():
            if v != float('inf') and v is not None:
                pdf.cell(0, 6, f"{k}: {formatar_numero(v)}", 0, 1)
        pdf.ln(5)
        if caminho_grafico_capacidade and os.path.exists(caminho_grafico_capacidade):
            pdf.image(caminho_grafico_capacidade, x=10, w=190)
            pdf.ln(5)
        
    # Deslocamento
    if desl and desl["tabela"]:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, 'Análise de Deslocamento (Beta / Poder / ARL)', 0, 1)
        pdf.set_font("Arial", size=8)
        col_w = [15, 20, 25, 25, 25, 25, 25, 25]
        header = ["k", "Delta0", "Beta(Q)", "Poder(Q)", "ARL(Q)", "Beta(C)", "Poder(C)", "ARL(C)"]
        for i, h in enumerate(header):
            pdf.cell(col_w[i], 6, h, 1, 0, 'C')
        pdf.ln()
        
        for linha in desl["tabela"]:
            pdf.cell(col_w[0], 6, formatar_numero(linha.get("k")), 1)
            pdf.cell(col_w[1], 6, formatar_numero(linha.get("delta0")), 1)
            pdf.cell(col_w[2], 6, formatar_numero(linha.get("beta_quadro")), 1)
            pdf.cell(col_w[3], 6, formatar_numero(linha.get("poder_quadro")), 1)
            pdf.cell(col_w[4], 6, formatar_numero(linha.get("arl1_quadro")), 1)
            pdf.cell(col_w[5], 6, formatar_numero(linha.get("beta_carta")), 1)
            pdf.cell(col_w[6], 6, formatar_numero(linha.get("poder_carta")), 1)
            pdf.cell(col_w[7], 6, formatar_numero(linha.get("arl1_carta")), 1)
            pdf.ln()

    pdf.output(arquivo_saida)
    return arquivo_saida
