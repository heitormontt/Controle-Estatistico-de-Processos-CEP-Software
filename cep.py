import argparse
import json
import os
from cep_core import processar_cep, montar_json_calibracao
from cep_plot import plotar_cartas, plotar_capacidade
from cep_report import gerar_pdf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI para Software CEP")
    parser.add_argument("arquivo", help="Caminho para o arquivo JSON")
    parser.add_argument("--saida", default="resultados", help="Pasta de saída")
    args = parser.parse_args()
    
    os.makedirs(args.saida, exist_ok=True)
    
    nome_arquivo = os.path.basename(args.arquivo)
    with open(args.arquivo, 'r', encoding='utf-8-sig') as f:
        dados = json.load(f)
        
    ret = processar_cep(dados, source_file=nome_arquivo)
    avisos = ret["resultado"]["dados_parsed"]["avisos"]
    for av in avisos:
        print(f"AVISO: {av}")
    
    # Se for calibração, salvar calibracao.json
    if ret["resultado"]["dados_parsed"]["Goal"] == "Calibrar":
        conteudo_calib = montar_json_calibracao(ret, source_file=nome_arquivo)
        with open(os.path.join(args.saida, "calibracao.json"), 'w', encoding='utf-8') as f:
            f.write(conteudo_calib)
    
    # Salvar relatorio simplificado em JSON
    with open(os.path.join(args.saida, "relatorio.json"), 'w', encoding='utf-8') as f:
        json.dump({
            "avisos": avisos,
            "parametros": ret["resultado"]["limites"].get("parametros"),
            "capacidade": ret["capacidade"]
        }, f, indent=2, ensure_ascii=False)
        
    # Gerar imagem para o PDF
    img_path = os.path.join(args.saida, "cartas.png")
    plotar_cartas(ret["resultado"], ret["resultado"]["dados_parsed"], save_path=img_path)
    
    cap_img_path = None
    if ret.get("capacidade"):
        dados_parsed = ret["resultado"]["dados_parsed"]
        todas_medicoes = []
        for sub in dados_parsed.get("Data", []):
            if isinstance(sub, list):
                todas_medicoes.extend(sub)
            else:
                todas_medicoes.append(sub)
                
        cap_img_path = os.path.join(args.saida, "capacidade.png")
        plotar_capacidade(
            medicoes=todas_medicoes,
            lie=dados_parsed.get("LIE"),
            lse=dados_parsed.get("LSE"),
            unidade=dados_parsed.get("Unit", ""),
            cap=ret["capacidade"],
            save_path=cap_img_path
        )
    
    # Gerar relatorio PDF
    pdf_path = os.path.join(args.saida, "relatorio_cep.pdf")
    gerar_pdf(ret, img_path, arquivo_saida=pdf_path, caminho_grafico_capacidade=cap_img_path)
    
    print(f"Processamento concluído. Resultados e PDF salvos em {args.saida}/")
