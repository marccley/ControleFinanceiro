import os
import sys
import customtkinter as ctk
from models import SQLModel, engine
from templates import AppFinanceiro

def obter_caminho_recurso(caminho_relativo):
    """ Retorna o caminho correto para recursos quando compilado pelo PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, caminho_relativo)

def iniciar_sistema():
    print("[INFO] Verificando integridade do banco de dados...")
    SQLModel.metadata.create_all(engine)
    
    # Corrige problemas de renderização e fontes do CustomTkinter em binários compilados
    ctk.deactivate_automatic_dpi_awareness()
    
    print("[INFO] Inicializando a interface gráfica...")
    app = AppFinanceiro()
    app.mainloop()

if __name__ == "__main__":
    iniciar_sistema()