import math
import numpy as np
import matplotlib.pyplot as plt
import locale

# Configuração de locale pt-BR com fallbacks seguros
LOCALE_CONFIGURADO = False
for loc in ['pt_BR', 'pt_BR.UTF-8', 'pt-BR', 'Portuguese_Brazil.1252', 'Portuguese_Brazil', 'ptb']:
    try:
        locale.setlocale(locale.LC_ALL, loc)
        LOCALE_CONFIGURADO = True
        break
    except Exception:
        pass


def formatar_numero_br(valor, casas=2):
    """
    Formata números no padrão brasileiro com vírgula decimal,
    utilizando o formatador de locale do ambiente sempre que disponível.
    """
    if valor is None:
        return "—"
    try:
        val_float = float(valor)
        if math.isnan(val_float) or math.isinf(val_float):
            return "—"
        if LOCALE_CONFIGURADO:
            return locale.format_string(f"%.{casas}f", val_float, grouping=False)
        else:
            return f"{val_float:.{casas}f}".replace(".", ",")
    except Exception:
        return str(valor)


def extrair_medicoes(data):
    """
    Extrai lista 1D de medições float a partir de listas aninhadas ou listas simples.
    """
    medicoes = []
    if isinstance(data, (list, tuple, np.ndarray)):
        for item in data:
            if isinstance(item, (list, tuple, np.ndarray)):
                for val in item:
                    if val is not None:
                        try:
                            vf = float(val)
                            if not math.isnan(vf):
                                medicoes.append(vf)
                        except (ValueError, TypeError):
                            pass
            elif item is not None:
                try:
                    vf = float(item)
                    if not math.isnan(vf):
                        medicoes.append(vf)
                except (ValueError, TypeError):
                    pass
    return medicoes


def calcular_classes_histograma(medicoes):
    """
    Calcula as k classes pela regra de Sturges:
    k = ceil(log2(n)) + 1
    w = (max - min) / k
    Retorna k, w, edges, counts, midpoints.
    """
    n = len(medicoes)
    if n < 1:
        return 0, 0.0, np.array([]), np.array([]), np.array([])
    
    min_v = float(min(medicoes))
    max_v = float(max(medicoes))
    
    if n == 1 or min_v == max_v:
        k = 1
        w = 1.0
        edges = np.array([min_v - 0.5, max_v + 0.5])
        counts = np.array([n])
        midpoints = np.array([(edges[0] + edges[1]) / 2.0])
        return k, w, edges, counts, midpoints

    k = int(np.ceil(np.log2(n))) + 1
    w = (max_v - min_v) / k
    edges = np.linspace(min_v, max_v, k + 1)
    counts, _ = np.histogram(medicoes, bins=edges)
    midpoints = (edges[:-1] + edges[1:]) / 2.0
    return k, w, edges, counts, midpoints


def calcular_curva_normal(x_vals, n, w, mu, sigma_curto):
    """
    Calcula a densidade normal escalonada para escala de frequência:
    y(x) = n * w * exp(-(x - mu)^2 / (2 * sigma_curto^2)) / (sigma_curto * sqrt(2*pi))
    """
    if sigma_curto is None or sigma_curto <= 0 or n < 1 or w <= 0:
        return np.zeros_like(x_vals)
    coef = (n * w) / (sigma_curto * np.sqrt(2.0 * np.pi))
    expoente = -((x_vals - mu) ** 2) / (2.0 * (sigma_curto ** 2))
    return coef * np.exp(expoente)


def avaliar_limites_especificacao(mu, sigma_global, lie=None, lse=None):
    """
    Regra de 'fora da escala': só desenha a linha de um limite se ele estiver a até 6*sigma_global da média.
    Caso contrário, não desenha, não usa esse limite para definir o intervalo do eixo X e cita-o na nota de rodapé.
    Retorna: (visiveis, fora_da_escala, nota_rodape)
    """
    visiveis = []
    fora_da_escala = []
    
    limite_6sigma = 6.0 * sigma_global if (sigma_global is not None and sigma_global > 0) else float('inf')

    if lie is not None:
        try:
            lie_f = float(lie)
            if abs(lie_f - mu) <= limite_6sigma:
                visiveis.append(("LIE", lie_f))
            else:
                fora_da_escala.append(("LIE", lie_f))
        except (ValueError, TypeError):
            pass

    if lse is not None:
        try:
            lse_f = float(lse)
            if abs(lse_f - mu) <= limite_6sigma:
                visiveis.append(("LSE", lse_f))
            else:
                fora_da_escala.append(("LSE", lse_f))
        except (ValueError, TypeError):
            pass

    # Monta a nota de rodapé se houver limites fora da escala
    nota_rodape = None
    if fora_da_escala:
        itens_fora = [f"{nome} = {formatar_numero_br(val, 4)}" for nome, val in fora_da_escala]
        nota_rodape = f"{' e '.join(itens_fora)} fora da escala"

    return visiveis, fora_da_escala, nota_rodape


def calcular_estatisticas_capacidade(medicoes, lie=None, lse=None, cap_existente=None):
    """
    Obtém ou calcula os parâmetros e índices de capacidade (mu, sigma_curto, sigma_global, RCP, RCPk, Ppk).
    Reutiliza os valores calculados previamente pelo software quando disponíveis em cap_existente.
    """
    n = len(medicoes)
    if n < 2:
        return {
            "n": n,
            "valido": False,
            "motivo": "Menos de 2 medições"
        }

    # Se já vier de retorno_cep["capacidade"], reaproveitar integralmente
    if cap_existente and isinstance(cap_existente, dict):
        mu = cap_existente.get("mu_hat")
        sigma_curto = cap_existente.get("sigma_hat")
        sigma_global = cap_existente.get("s")
        rcp = cap_existente.get("Cp")
        rcpk = cap_existente.get("Cpk")
        ppk = cap_existente.get("Ppk")
    else:
        mu = float(np.mean(medicoes))
        sigma_global = float(np.std(medicoes, ddof=1)) if n > 1 else 0.0
        # sigma_curto para medições individuais via Amplitude Móvel média (MRbar / d2, d2=1.128)
        diffs = np.abs(np.diff(medicoes))
        mr_bar = float(np.mean(diffs)) if len(diffs) > 0 else 0.0
        sigma_curto = mr_bar / 1.128 if mr_bar > 0 else 0.0
        
        rcp = None
        if lse is not None and lie is not None and sigma_curto > 0:
            rcp = (float(lse) - float(lie)) / (6.0 * sigma_curto)
            
        rcpk = None
        if sigma_curto > 0:
            cpu = (float(lse) - mu) / (3.0 * sigma_curto) if lse is not None else float('inf')
            cpl = (mu - float(lie)) / (3.0 * sigma_curto) if lie is not None else float('inf')
            min_c = min(cpu, cpl)
            if min_c != float('inf'):
                rcpk = min_c

        ppk = None
        if sigma_global > 0:
            ppu = (float(lse) - mu) / (3.0 * sigma_global) if lse is not None else float('inf')
            ppl = (mu - float(lie)) / (3.0 * sigma_global) if lie is not None else float('inf')
            min_p = min(ppu, ppl)
            if min_p != float('inf'):
                ppk = min_p

    valido = bool((sigma_curto is not None and sigma_curto > 0) or (sigma_global is not None and sigma_global > 0))

    # Classificação qualitativa do RCPk (suposição conforme especificado):
    # >= 1.33: (capaz), 1.00 a < 1.33: (marginal), < 1.00: (não capaz)
    status_rcpk = None
    if rcpk is not None and not math.isinf(rcpk):
        if rcpk >= 1.33:
            status_rcpk = "(capaz)"
        elif rcpk >= 1.00:
            status_rcpk = "(marginal)"
        else:
            status_rcpk = "(não capaz)"

    return {
        "n": n,
        "mu": mu,
        "sigma_curto": sigma_curto,
        "sigma_global": sigma_global,
        "rcp": rcp,
        "rcpk": rcpk,
        "ppk": ppk,
        "status_rcpk": status_rcpk,
        "valido": valido
    }


def obter_passo_redondo(span, alvo_ticks=7):
    """
    Determina um passo 'redondo' (1, 2, 5 * 10^p) para o eixo X.
    """
    if span <= 0:
        return 1.0
    passo_bruto = span / alvo_ticks
    ordem = math.floor(math.log10(passo_bruto))
    frac = passo_bruto / (10 ** ordem)
    if frac < 1.5:
        mult = 1.0
    elif frac < 3.0:
        mult = 2.0
    elif frac < 7.0:
        mult = 5.0
    else:
        mult = 10.0
    return mult * (10 ** ordem)


def obter_passo_inteiro_y(y_max_lim):
    """
    Determina um passo redondo inteiro para o eixo Y.
    Para y_max_lim em torno de 38, resulta em passo 4 (0, 4, 8, ..., 36).
    """
    alvo = 9.0
    bruto = y_max_lim / alvo
    passos_padrao = [1, 2, 4, 5, 10, 20, 25, 50, 100, 200, 500, 1000]
    return min(passos_padrao, key=lambda p: abs(p - bruto))


def plotar_capacidade(medicoes, lie=None, lse=None, unidade="", cap=None, save_path=None, dpi=72):
    """
    Desenha o gráfico de capacidade do processo exatamente conforme a referência visual:
    - Cartão branco 755x345 px (proporção 2.2:1).
    - Área de plotagem 686x217 px (57 px esq, 11 px dir, 55 px topo, 73 px base).
    - Histograma (Sturges, vão 7%, cor #2A78D6).
    - Curva normal em escala de frequência (#515253, 2 px).
    - Linha da média (#505050, 1.2 px) com rótulo 'μ x,xxxx'.
    - Linha de limites traço-ponto (#222222, 1.5 px) com rótulo 'LSE/LIE x,xxxx'.
    - Formatação pt-BR com vírgula decimal.
    - Regra de limites fora da escala (> 6*sigma_global).
    - Casos de borda tratados sem erro.
    """
    # Garante fonte padrão sans-serif equivalente (DejaVu Sans)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans', 'Helvetica']

    medicoes_limpas = extrair_medicoes(medicoes)
    stats = calcular_estatisticas_capacidade(medicoes_limpas, lie=lie, lse=lse, cap_existente=cap)

    # Caso de borda: dados insuficientes ou sigma <= 0
    if not stats.get("valido", False) or len(medicoes_limpas) < 2:
        fig = plt.figure(figsize=(755.0 / 72.0, 345.0 / 72.0), dpi=dpi, facecolor='#FFFFFF')
        ax_err = fig.add_axes([0, 0, 1, 1], facecolor='#FFFFFF')
        ax_err.axis('off')
        ax_err.text(
            0.5, 0.5,
            "Dados insuficientes para calcular a capacidade do processo.",
            fontsize=12,
            color="#555555",
            ha="center",
            va="center"
        )
        if save_path:
            fig.savefig(save_path, format='png', dpi=144)
            plt.close(fig)
            return save_path
        return fig

    n = stats["n"]
    mu = stats["mu"]
    sigma_curto = stats["sigma_curto"]
    sigma_global = stats["sigma_global"]

    # Avaliação dos limites visíveis e fora da escala
    vis_limits, fora_escala, nota_rodape = avaliar_limites_especificacao(mu, sigma_global, lie=lie, lse=lse)

    # Dimensões do cartão e da área de plotagem em coordenadas normalizadas [0, 1]
    card_w = 755.0
    card_h = 345.0
    left = 57.0 / card_w
    bottom = 73.0 / card_h
    plot_w = 686.0 / card_w
    plot_h = 217.0 / card_h

    fig = plt.figure(figsize=(card_w / 72.0, card_h / 72.0), dpi=dpi, facecolor='#FFFFFF')
    ax = fig.add_axes([left, bottom, plot_w, plot_h], facecolor='#FFFFFF')

    # Intervalo do Eixo X: cobre todas as medições e limites visíveis com 4% de folga em cada lado
    vals_visiveis = list(medicoes_limpas) + [val for _, val in vis_limits]
    min_x = min(vals_visiveis)
    max_x = max(vals_visiveis)
    span_x = max_x - min_x
    if span_x <= 0:
        span_x = 1.0

    xlim = (min_x - 0.04 * span_x, max_x + 0.04 * span_x)
    ax.set_xlim(xlim)

    # 1. Histograma (Classes de Sturges)
    k, w, edges, counts, midpoints = calcular_classes_histograma(medicoes_limpas)
    bar_width = w * 0.93  # vão branco de ~7% da largura da classe
    ax.bar(midpoints, counts, width=bar_width, color='#2A78D6', edgecolor='none', zorder=1)

    # 2. Curva normal suave (>= 200 pontos cobrindo todo o eixo X)
    x_curve = np.linspace(xlim[0], xlim[1], 400)
    y_curve = calcular_curva_normal(x_curve, n, w, mu, sigma_curto)
    ax.plot(x_curve, y_curve, color='#515253', linewidth=2.0, zorder=2)

    # 3. Limites e escala do Eixo Y (de 0 até ~1.17x o maior valor entre barra e pico)
    max_count = max(counts) if len(counts) > 0 else 0
    max_curve = float(np.max(y_curve)) if len(y_curve) > 0 else 0.0
    y_max_data = max(max_count, max_curve)
    y_lim_top = y_max_data * 1.17 if y_max_data > 0 else 10.0
    ax.set_ylim(0, y_lim_top)

    # Ticks do Eixo X em passo redondo, 3 casas decimais
    step_x = obter_passo_redondo(span_x, alvo_ticks=7)
    tick_start = math.ceil(xlim[0] / step_x) * step_x
    ticks_x = []
    cur_tx = tick_start
    while cur_tx <= xlim[1] + (step_x * 0.01):
        ticks_x.append(cur_tx)
        cur_tx = round(cur_tx + step_x, 8)
    ax.set_xticks(ticks_x)
    ax.set_xticklabels([formatar_numero_br(t, 3) for t in ticks_x])

    # Ticks do Eixo Y em passo redondo inteiro
    step_y = obter_passo_inteiro_y(y_lim_top)
    ticks_y = [i * step_y for i in range(int(y_lim_top / step_y) + 1)]
    ax.set_yticks(ticks_y)
    ax.set_yticklabels([str(int(t)) for t in ticks_y])

    # Estilização dos Eixos (somente esquerdo e inferior, sem grade)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#444444')
    ax.spines['bottom'].set_linewidth(1.0)
    ax.spines['left'].set_color('#BBBBBB')
    ax.spines['left'].set_linewidth(1.0)

    ax.tick_params(axis='x', direction='out', length=4, width=1, colors='#BBBBBB', labelcolor='#555555', labelsize=11, pad=5)
    ax.tick_params(axis='y', direction='out', length=4, width=1, colors='#BBBBBB', labelcolor='#555555', labelsize=11, pad=5)

    ax.set_ylabel("Frequência", fontsize=11, color='#555555', labelpad=8)
    x_label = f"Medição individual ({unidade})" if unidade else "Medição individual"
    ax.set_xlabel(x_label, fontsize=11, color='#555555', labelpad=8)

    # Altura dos rótulos: ≈ 15 px abaixo do topo da área de plotagem
    y_label_pos = y_lim_top * (1.0 - 15.0 / 217.0)

    # Detecção de colisão entre rótulo da média e limites próximos
    colisao_dir = False
    colisao_esq = False
    lim_dist = 0.05 * span_x
    for tipo_lim, val_lim in vis_limits:
        if 0 < (val_lim - mu) < lim_dist:
            colisao_dir = True
        elif 0 < (mu - val_lim) < lim_dist:
            colisao_esq = True

    ha_mu = 'center'
    x_mu_label = mu
    if colisao_dir and not colisao_esq:
        ha_mu = 'right'
        x_mu_label = mu - 0.005 * span_x
    elif colisao_esq and not colisao_dir:
        ha_mu = 'left'
        x_mu_label = mu + 0.005 * span_x

    # 4. Linha da Média (contínua, #505050, 1.2 px)
    ax.vlines(mu, 0, y_lim_top, colors='#505050', linewidth=1.2, zorder=3)
    ax.text(x_mu_label, y_label_pos, f"μ {formatar_numero_br(mu, 4)}", color='#555555', fontsize=10, ha=ha_mu, va='center', zorder=4)

    # 5. Linhas dos Limites de Especificação (traço-ponto #222222, 1.5 px)
    # Padrão traço-ponto ≈ 10 px traço, 3 vazio, 2 ponto, 3 vazio
    dashes_pattern = (0, (7, 2, 1.5, 2))
    for tipo_lim, val_lim in vis_limits:
        ax.vlines(val_lim, 0, y_lim_top, colors='#222222', linestyle=dashes_pattern, linewidth=1.5, zorder=3)
        rotulo_lim = f"{tipo_lim} {formatar_numero_br(val_lim, 4)}"
        if tipo_lim == "LSE":
            # Rótulo encostado à esquerda da linha
            ax.text(val_lim - 0.002 * span_x, y_label_pos, rotulo_lim, color='#222222', fontsize=10, ha='right', va='center', zorder=4)
        else:
            # LIE: Rótulo encostado à direita da linha
            ax.text(val_lim + 0.002 * span_x, y_label_pos, rotulo_lim, color='#222222', fontsize=10, ha='left', va='center', zorder=4)

    # 6. Título do Cartão (negrito 13 px, #111111, alinhado à borda esquerda da plotagem)
    fig.text(
        left,
        (card_h - 13.0) / card_h,
        "Capacidade do processo – medições individuais e especificação",
        fontsize=13,
        fontweight='bold',
        color='#111111',
        ha='left',
        va='top'
    )

    # 7. Subtítulo (11 px, #555555, 3 espaços entre itens)
    sub_parts = []
    rcp = stats.get("rcp")
    rcpk = stats.get("rcpk")
    ppk = stats.get("ppk")
    status_rcpk = stats.get("status_rcpk")

    # Omite RCP se for especificação unilateral
    if rcp is not None and not math.isinf(rcp):
        sub_parts.append(f"RCP = {formatar_numero_br(rcp, 2)}")
    if rcpk is not None and not math.isinf(rcpk):
        texto_rcpk = f"RCPk = {formatar_numero_br(rcpk, 2)}"
        if status_rcpk:
            texto_rcpk += f" {status_rcpk}"
        sub_parts.append(texto_rcpk)
    elif rcp is not None:
        sub_parts.append("RCPk = —")

    if ppk is not None and not math.isinf(ppk):
        sub_parts.append(f"Ppk = {formatar_numero_br(ppk, 2)}")
    elif rcp is not None:
        sub_parts.append("Ppk = —")

    subtitulo = "   ".join(sub_parts)
    fig.text(
        left,
        (card_h - 38.0) / card_h,
        subtitulo,
        fontsize=11,
        color='#555555',
        ha='left',
        va='top'
    )

    # 8. Nota de Rodapé (10 px, #888888, canto inferior esquerdo do cartão ≈ 12 px)
    if nota_rodape:
        fig.text(
            12.0 / card_w,
            13.0 / card_h,
            nota_rodape,
            fontsize=10,
            color='#888888',
            ha='left',
            va='bottom'
        )

    if save_path:
        fig.savefig(save_path, format='png', dpi=dpi)
        plt.close(fig)
        return save_path

    return fig
