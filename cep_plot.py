import matplotlib.pyplot as plt
import numpy as np
import io
from cep_capacidade import plotar_capacidade

def plotar_cartas(res, dados_parsed, save_path=None):
    tipo = dados_parsed["Type"]
    limites = res["limites"]
    m = len(limites["val_1"])
    x_axis = np.arange(1, m+1)
    
    fig, axes = plt.subplots(2 if tipo in ["X", "R", "IMR"] else 1, 1, figsize=(10, 8 if tipo in ["X", "R", "IMR"] else 5))
    if not isinstance(axes, np.ndarray): axes = [axes]
    
    def desenhar_carta(ax, vals, LCs, LSCs, LICs, sinais, removidos, titulo, ylabel):
        ax.plot(x_axis, vals, marker='o', color='blue', alpha=0.5, zorder=1)
        ax.step(x_axis, LCs, color='green', linestyle='-', where='mid', zorder=2, label='LC')
        ax.step(x_axis, LSCs, color='red', linestyle='--', where='mid', zorder=2, label='LSC')
        ax.step(x_axis, LICs, color='red', linestyle='--', where='mid', zorder=2, label='LIC')
        
        for i in range(m):
            if i in removidos:
                ax.scatter(x_axis[i], vals[i], edgecolors='gray', facecolors='none', s=100, zorder=3, label='Removido' if i==list(removidos)[0] else "")
            elif "R1" in sinais.get(i, []):
                ax.scatter(x_axis[i], vals[i], color='red', s=100, zorder=4, label='Fora Controle' if i==0 else "")
            elif len(sinais.get(i, [])) > 0:
                ax.scatter(x_axis[i], vals[i], color='orange', s=100, zorder=3, label='Alerta Regra' if i==0 else "")
                
        ax.set_title(titulo)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Subgrupo")
        ax.grid(True, alpha=0.3)
        
    removidos = res["removidos"]
    label = dados_parsed.get("Label", "Característica")
    unit = dados_parsed.get("Unit", "")
    ylab = f"{label} ({unit})" if unit else label
    
    desenhar_carta(axes[0], limites["val_1"], limites["LC_1"], limites["LSC_1"], limites["LIC_1"], res["sinais_1"], removidos, f"Carta {tipo} - {dados_parsed['Goal']}", ylab)
    
    if tipo in ["X", "R", "IMR"]:
        tipo2 = "R" if tipo != "IMR" else "AM"
        desenhar_carta(axes[1], limites["val_2"], limites["LC_2"], limites["LSC_2"], limites["LIC_2"], res["sinais_2"], removidos, f"Carta {tipo2} - {dados_parsed['Goal']}", "Amplitude")
        
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, format='png')
        plt.close(fig)
        return save_path
    
    return fig
