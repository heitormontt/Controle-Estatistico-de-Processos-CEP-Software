import streamlit as st
import json
import pandas as pd
import os
import tempfile
from cep_core import processar_cep, montar_json_calibracao
from cep_plot import plotar_cartas, plotar_capacidade
from cep_report import gerar_pdf

st.set_page_config(page_title="Software CEP", layout="wide")
st.title("Software de Controle Estatístico de Processo (CEP)")

uploaded_file = st.sidebar.file_uploader("Carregar arquivo JSON", type=["json"])
if uploaded_file:
    try:
        conteudo_bytes = uploaded_file.read()
        dados = json.loads(conteudo_bytes.decode("utf-8-sig"))
        
        try:
            ret = processar_cep(dados, source_file=uploaded_file.name)
        except Exception as e:
            st.error(f"Erro ao processar dados: {str(e)}")
            st.stop()
            
        res_calib = ret["resultado"]
        dados_parsed = res_calib["dados_parsed"]
        
        st.sidebar.success("Arquivo processado com sucesso!")
        if dados_parsed["avisos"]:
            for av in dados_parsed["avisos"]: st.sidebar.warning(av)
            
        aba1, aba2, aba3, aba4, aba5 = st.tabs(["Cartas", "Dados e Sinais", "Capacidade", "Deslocamento", "Exportação"])
        
        with aba1:
            fig = plotar_cartas(res_calib, dados_parsed)
            st.pyplot(fig)
            
        with aba2:
            st.subheader("Resumo por Subgrupo")
            df_dados = []
            m = len(dados_parsed["Data"])
            for i in range(m):
                s1 = res_calib["sinais_1"].get(i, [])
                s2 = res_calib["sinais_2"].get(i, [])
                status = "REMOVIDO" if i in res_calib["removidos"] else ("FORA" if "R1" in s1 or "R1" in s2 else ("ALERTA" if s1 or s2 else "OK"))
                regras = ",".join(s1 + s2)
                df_dados.append({
                    "Subgrupo": i+1,
                    "Val 1 (X/p/c)": res_calib["limites"]["val_1"][i],
                    "Val 2 (R/AM)": res_calib["limites"]["val_2"][i] if res_calib["limites"]["val_2"][i] is not None else "-",
                    "Status": status,
                    "Regras Violadas": regras
                })
            st.dataframe(pd.DataFrame(df_dados), use_container_width=True)
            
            st.subheader("Memória de Cálculo (Última Iteração)")
            for k, v in res_calib["limites"].get("memoria", {}).items():
                st.write(f"**{k}**: {v}")
                
        # Extração de medições individuais de todos os subgrupos
        todas_medicoes = []
        for sub in dados_parsed.get("Data", []):
            if isinstance(sub, list):
                todas_medicoes.extend(sub)
            else:
                todas_medicoes.append(sub)

        with aba3:
            cap = ret["capacidade"]
            tem_limite = dados_parsed.get("LSE") is not None or dados_parsed.get("LIE") is not None
            tipo_variavel = dados_parsed.get("Type") in ["X", "R", "IMR"]

            if cap or (tipo_variavel and tem_limite):
                st.markdown(
                    """
                    <div style="background-color: #0D1117; border-bottom: 1px solid #3D444D; padding: 18px 0; margin-bottom: 25px; text-align: center;">
                        <span style="font-size: 24px; font-weight: 600; color: #F0F6FC; letter-spacing: 0.5px;">Capacidade do processo</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                fig_cap = plotar_capacidade(
                    medicoes=todas_medicoes,
                    lie=dados_parsed.get("LIE"),
                    lse=dados_parsed.get("LSE"),
                    unidade=dados_parsed.get("Unit", ""),
                    cap=cap
                )
                st.pyplot(fig_cap, use_container_width=True)
                
                if cap:
                    with st.expander("Ver Resumo Numérico (JSON)"):
                        st.json(cap)
            else:
                st.info("Capacidade não calculada (falta LSE/LIE ou tipo não aplicável).")
                
        with aba4:
            desl = ret["deslocamento"]
            if desl and desl["tabela"]:
                st.dataframe(pd.DataFrame(desl["tabela"]), use_container_width=True)
            else:
                st.info("Análise de deslocamento não disponível para este cenário.")
                
        with aba5:
            st.subheader("Downloads")
            
            if dados_parsed["Goal"] == "Calibrar":
                conteudo_calib = montar_json_calibracao(ret, source_file=uploaded_file.name)
                st.download_button(
                    "Baixar calibracao.json",
                    data=conteudo_calib.encode("utf-8"),
                    file_name="calibracao.json",
                    mime="application/json"
                )
                st.caption("ℹ️ Este arquivo contém os limites calibrados e os dados originais formatados para a Fase II (**Acompanhamento**).")
            
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                img_path = tmp_img.name
            plotar_cartas(res_calib, dados_parsed, save_path=img_path)
            
            cap_img_path = None
            if cap:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_cap:
                    cap_img_path = tmp_cap.name
                plotar_capacidade(
                    medicoes=todas_medicoes,
                    lie=dados_parsed.get("LIE"),
                    lse=dados_parsed.get("LSE"),
                    unidade=dados_parsed.get("Unit", ""),
                    cap=cap,
                    save_path=cap_img_path
                )
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                pdf_path = tmp_pdf.name
            
            gerar_pdf(ret, img_path, arquivo_saida=pdf_path, caminho_grafico_capacidade=cap_img_path)
            
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("Baixar Relatório PDF", data=pdf_file, file_name="relatorio_cep.pdf", mime="application/pdf")
            
            try:
                os.remove(img_path)
                os.remove(pdf_path)
                if cap_img_path:
                    os.remove(cap_img_path)
            except:
                pass
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: {str(e)}")
else:
    st.info("Por favor, carregue um arquivo JSON no menu lateral.")
