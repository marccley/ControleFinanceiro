import csv
from tkinter import filedialog, messagebox, ttk, simpledialog
import customtkinter as ctk
from datetime import datetime
import calendar
import view
from models import Conta, Historico, Tipos
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def formatar_moeda_br(valor: float) -> str:
    # Converte um número float para o formato de moeda brasileiro: . para milhar e , para decimal
    texto_br = f"{valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    return texto_br

class CTkMenuScrollavelVerdadeiro(ctk.CTkButton):
    def __init__(self, master, values=None, command=None, **kwargs):
        super().__init__(master, text="Selecione...", fg_color=("#D3D3D3", "#3B3B3B"), 
                         text_color=("#000000", "#FFFFFF"), hover_color=("#C0C0C0", "#4F4F4F"), **kwargs)
        self.values = values if values else []
        self.command = command
        self._valor_selecionado = ""
        self.popup = None
        
        self.configure(command=self._abrir_menu_customizado)

    def configure(self, **kwargs):
        if "values" in kwargs:
            self.values = kwargs.pop("values")
        super().configure(**kwargs)

    def set(self, valor):
        self._valor_selecionado = valor
        self.configure(text=valor)

    def get(self):
        return self._valor_selecionado

    def _fechar_menu(self, event=None):
        # Desvincula o monitoramento global de cliques para economizar processamento
        try:
            self.winfo_toplevel().unbind_all("<Button-1>")
        except Exception:
            pass
            
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
        self.popup = None

    def _verificar_clique_fora(self, event):
        # Se o usuário clicar fora do menu suspenso, fecha ele automaticamente
        if self.popup and self.popup.winfo_exists():
            # Obtém a posição x e y de onde o mouse foi clicado na tela
            x, y = event.x_root, event.y_root
            px = self.popup.winfo_rootx()
            py = self.popup.winfo_rooty()
            pw = self.popup.winfo_width()
            ph = self.popup.winfo_height()
            
            # Verifica se as coordenadas do clique estão fora dos limites do popup
            if not (px <= x <= px + pw and py <= y <= py + ph):
                # Pequeno atraso para garantir que não cancele um clique legítimo no botão de disparo
                self.popup.after(10, self._fechar_menu)

    def _abrir_menu_customizado(self):
        if self.popup and self.popup.winfo_exists():
            self._fechar_menu()
            return

        janela_mae = self.winfo_toplevel()

        # Cria apenas o menu flutuante real (sem segundas janelas transparentes/pretas)
        self.popup = ctk.CTkToplevel(janela_mae)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)

        # Localização exata abaixo do botão de disparo
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        largura = self.winfo_width()
        altura = min(280, len(self.values) * 34 + 12)
        self.popup.geometry(f"{largura}x{altura}+{x}+{y}")

        # Frame rolável nativo estável com suporte total à scroll do mouse
        frame_scroll = ctk.CTkScrollableFrame(self.popup, width=largura-16, height=altura-10, corner_radius=6)
        frame_scroll.pack(expand=True, fill="both", padx=2, pady=2)

        # Alimenta os botões de opções de forma indexada
        for opcao in self.values:
            btn_opcao = ctk.CTkButton(
                frame_scroll, 
                text=opcao, 
                anchor="w", 
                fg_color="transparent",
                text_color=("#000000", "#FFFFFF"),
                hover_color=("#E0E0E0", "#4A4A4A"),
                height=28,
                corner_radius=4,
                command=lambda opt=opcao: self._selecionar_opcao(opt)
            )
            btn_opcao.pack(fill="x", pady=1, padx=2)

        # Ativa o monitoramento inteligente de cliques na aplicação inteira
        janela_mae.bind_all("<Button-1>", self._verificar_clique_fora, add="+")

    def _selecionar_opcao(self, valor):
        self.set(valor)
        self._fechar_menu()
        if self.command:
            self.command(valor)

class CTkComboBoxScrollavel(ctk.CTkComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Vincula o evento de abertura do menu para injetar o suporte ao scroll do mouse
        self._canvas.bind("<Enter>", self._habilitar_scroll_menu)

    def _habilitar_scroll_menu(self, event):
        # Acessa a janela popup nativa do Tkinter gerada por trás do CustomTkinter
        if hasattr(self, "_dropdown_menu") and self._dropdown_menu:
            menu_nativo = self._dropdown_menu
            
            # Adiciona o suporte a scroll para sistemas Windows / macOS
            menu_nativo.bind_all("<MouseWheel>", lambda e: menu_nativo.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            
            # Adiciona o suporte a scroll para sistemas Linux
            menu_nativo.bind_all("<Button-4>", lambda e: menu_nativo.yview_scroll(-1, "units"))
            menu_nativo.bind_all("<Button-5>", lambda e: menu_nativo.yview_scroll(1, "units"))

class CanvasNumerado(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_paginas = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.desenhar_rodape(num_paginas)
            super().showPage()
        super().save()

    def desenhar_rodape(self, total_paginas):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#7F8C8D"))
        
        # Linha fina decorativa superior ao rodapé
        self.setStrokeColor(colors.HexColor("#BDC3C7"))
        self.setLineWidth(0.5)
        self.line(36, 45, 576, 45)
        
        # Textos informativos inferiores
        texto_pag = f"Página {self._pageNumber} de {total_paginas}"
        self.drawRightString(576, 30, texto_pag)
        self.drawString(36, 30, "📊 Sistema de Controle Financeiro Pessoal")
        self.restoreState()

class AppFinanceiro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("📊 Sistema de Controle Financeiro Avançado")
        self.geometry("1050x700")
        self.resizable(True, True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self, width=1030, height=665)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.tabview.add("Visão Geral")
        self.tabview.add("Nova Movimentação")
        self.tabview.add("Transferência")
        self.tabview.add("Extrato")

        # Dicionário para mapear "Nome do Banco" -> ID da Conta
        self.mapa_contas = {}
        self.mapa_categorias = {}


        # 1. Primeiro configura as abas que criam os elementos visuais (inputs e dropdowns)
        self.configurar_aba_movimentacao()
        self.configurar_aba_transferencia()
        self.configurar_aba_extrato()
        
        # 2. Cria a Visão Geral com total segurança, pois todos os objetos já existem
        self.configurar_aba_visao_geral()
        
        # 3. Alimenta e sincroniza as informações do banco de dados na tela
        self.carregar_dados_bancos()
        self.filtrar_historico()

    def carregar_dados_bancos(self):
        """Atualiza os componentes Dropdown/Combobox exibindo o nome do banco junto com o saldo atual"""
        contas_ativas = view.listar_ativas()
        
        # Mantem o mapa apenas com o nome bruto do banco como chave
        self.mapa_contas = {c.banco: c.id for c in contas_ativas}
        
        # Cria a lista de exibição formatada: "Nome do Banco (R$ X.XX)"
        lista_bancos_com_saldo = [f"{c.banco} (R$ {formatar_moeda_br(c.valor)})" for c in contas_ativas] if contas_ativas else []
        
        # Configura a Aba 2: Nova Movimentação
        if lista_bancos_com_saldo:
            self.cb_mov_banco.configure(values=lista_bancos_com_saldo)
            self.cb_mov_banco.set("Selecione um banco...")
        else:
            self.cb_mov_banco.configure(values=["Nenhuma conta ativa"])
            self.cb_mov_banco.set("Nenhuma conta ativa")
        
        # Configura a Aba 3: Transferência
        if lista_bancos_com_saldo:
            self.cb_trans_origem.configure(values=lista_bancos_com_saldo)
            self.cb_trans_origem.set("Selecione a origem...")
            
            self.cb_trans_destino.configure(values=lista_bancos_com_saldo)
            self.cb_trans_destino.set("Selecione o destino...")
        else:
            self.cb_trans_origem.configure(values=["Nenhuma conta ativa"])
            self.cb_trans_origem.set("Nenhuma conta ativa")
            self.cb_trans_destino.configure(values=["Nenhuma conta ativa"])
            self.cb_trans_destino.set("Nenhuma conta ativa")

        # Configura o Filtro da Aba 4: Extrato
        todas_contas = view.listar_contas()
        lista_extrato = ["Todos"] + [c.banco for c in todas_contas]
        self.cb_ext_banco.configure(values=lista_extrato)
        self.cb_ext_banco.set("Todos")

        # Carrega as categorias do banco de dados para a Aba 2
        categorias = view.listar_categorias()
        self.mapa_categorias = {cat.categoria: cat.id for cat in categorias}
        lista_cats = list(self.mapa_categorias.keys()) if self.mapa_categorias else []
        
        if lista_cats:
            self.cb_mov_categoria.configure(values=lista_cats)
            self.cb_mov_categoria.set("Selecione uma categoria...")
        else:
            self.mapa_categorias = {"Geral": 1}
            self.cb_mov_categoria.configure(values=["Geral"])
            self.cb_mov_categoria.set("Geral")

    # --- ABA 1: VISÃO GERAL ---
    def configurar_aba_visao_geral(self):
        self.aba_visao = self.tabview.tab("Visão Geral")
        self.aba_visao.grid_columnconfigure((0, 1, 2), weight=1)
        
        # MELHORIA: Configura a linha da tabela (Row 2) para expandir e ocupar 100% do espaço vertical livre
        self.aba_visao.grid_rowconfigure(2, weight=1) 

        # [ROW 0] Card de Patrimônio Total
        self.card_total = ctk.CTkFrame(self.aba_visao, fg_color=("#EAEAEA", "#2B2B2B"), corner_radius=10)
        self.card_total.grid(row=0, column=0, columnspan=3, padx=15, pady=10, sticky="ew")
        
        self.lbl_total_titulo = ctk.CTkLabel(self.card_total, text="Patrimônio Total Combinado", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_total_titulo.pack(pady=(10, 5))
        
        self.lbl_total_valor = ctk.CTkLabel(self.card_total, text="R$ 0,00", font=ctk.CTkFont(size=24, weight="bold"), text_color="#2ECC71")
        self.lbl_total_valor.pack(pady=(0, 10))

        # [ROW 1] Título Indicativo da Tabela
        self.lbl_contas = ctk.CTkLabel(self.aba_visao, text="Suas Contas Bancárias (Altere e aperte ENTER para salvar):", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_contas.grid(row=1, column=0, columnspan=3, padx=15, pady=(10, 2), sticky="w")

        # [ROW 2] Container Rolável das Contas (Aumentado para height=360 e com expansão elástica nsew)
        self.frame_grade_contas = ctk.CTkScrollableFrame(self.aba_visao, height=360)
        self.frame_grade_contas.grid(row=2, column=0, columnspan=3, padx=15, pady=5, sticky="nsew")
        self.frame_grade_contas.grid_columnconfigure((1, 2, 3), weight=1)

        # [ROW 3] Bloco de Botões de Ação (Mantidos na parte inferior do layout)
        ctk.CTkButton(self.aba_visao, text="➕ Criar Nova Conta", fg_color="#2980B9", hover_color="#1F618D", 
                      command=self.abrir_popup_criar_conta).grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(self.aba_visao, text="🗑️ Excluir Conta", fg_color="#C0392B", hover_color="#922B21", 
                      command=self.abrir_popup_excluir_conta).grid(row=3, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(self.aba_visao, text="🏷️ Categorias", fg_color="#8E44AD", hover_color="#7D3C98", 
                      command=self.abrir_popup_gerenciar_categorias).grid(row=3, column=2, padx=10, pady=10, sticky="ew")

        # [ROW 4] Botão do Gráfico de Distribuição (Base do layout com destaque total)
        self.btn_grafico = ctk.CTkButton(self.aba_visao, text="📈 Ver Gráfico de Distribuição de Saldos", fg_color="teal", hover_color="#005F5F", 
                                         command=view.criar_grafico_por_conta)
        self.btn_grafico.grid(row=4, column=0, columnspan=3, padx=15, pady=(5, 15), sticky="ew")

        self.atualizar_visao_geral()

    def abrir_popup_excluir_conta(self):
        popup = ctk.CTkToplevel(self)
        popup.title("🗑️ Remover Conta Bancária")
        popup.geometry("380x200")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        
        # Garante foco absoluto e congela a janela de trás
        popup.grab_set()

        ctk.CTkLabel(popup, text="Selecione a Conta para Excluir:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(25, 0))
        
        # Criação do componente customizado com scroll
        cb_excluir_conta = CTkMenuScrollavelVerdadeiro(popup)
        cb_excluir_conta.pack(fill="x", padx=20, pady=10)

        # Função auxiliar para carregar as contas ativas com seus respectivos saldos
        def atualizar_combo_exclusao_contas():
            contas_ativas = view.listar_contas()  # Traz todas as contas do banco de dados
            # Formata a exibição: "Banco (R$ Saldo) [ID: X]" para facilitar o fatiamento do ID
            lista_opcoes = [f"{c.banco} (R$ {c.valor:,.2f}) [ID: {c.id}]" for c in contas_ativas] if contas_ativas else []
            
            if lista_opcoes:
                cb_excluir_conta.configure(values=lista_opcoes)
                cb_excluir_conta.set("Escolha a conta...")
            else:
                cb_excluir_conta.configure(values=["Nenhuma conta cadastrada"])
                cb_excluir_conta.set("Nenhuma conta cadastrada")

        def executar_remocao_conta():
            selecao = cb_excluir_conta.get()
            if selecao in ["Escolha a conta...", "Nenhuma conta cadastrada"]:
                messagebox.showwarning("Aviso", "Por favor, selecione uma conta válida na lista.", parent=popup)
                return
                
            try:
                # Pega a segunda parte da quebra [1] para tratar como texto puro
                id_bruto = selecao.split("[ID: ")[1]
                id_conta = int(id_bruto.replace("]", "").strip())
                
                # Pega a primeira parte da quebra [0] para ler o nome do banco
                nome_banco = selecao.split(" (R$")[0].strip()
                
                if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja remover permanentemente a conta '{nome_banco}'?\nEsta ação não poderá ser desfeita.", parent=popup):
                    view.deletar_conta(id_conta)
                    
                    popup.destroy()
                    messagebox.showinfo("Sucesso", f"A conta '{nome_banco}' foi removida com sucesso!")
                    
                    self.atualizar_visao_geral()
                    
            except Exception as e: 
                messagebox.showerror("Erro de Integridade", f"Não foi possível excluir.\nDetalhes: {e}", parent=popup)

            
        # Botão de ação empacotado corretamente usando apenas .pack()
        btn_remover = ctk.CTkButton(popup, text="🗑️ Remover Conta Selecionada", fg_color="#E74C3C", hover_color="#C0392B", command=executar_remocao_conta)
        btn_remover.pack(fill="x", padx=20, pady=15)

        # Inicializa a lista de contas na abertura do popup
        atualizar_combo_exclusao_contas()

    def abrir_popup_gerenciar_categorias(self):
        popup = ctk.CTkToplevel(self)
        popup.title("🏷️ Gerenciar Categorias")
        popup.geometry("380x350")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        
        # Garante foco absoluto na janela aberta
        popup.grab_set()

        # --- SEÇÃO 1: CADASTRO DE NOVA CATEGORIA ---
        ctk.CTkLabel(popup, text="Nova Categoria:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(15,0))
        txt_cat = ctk.CTkEntry(popup, placeholder_text="Ex: Transporte, Alimentação...")
        txt_cat.pack(fill="x", padx=20, pady=5)
        
        def add():
            try:
                nome = txt_cat.get().strip()
                if not nome:
                    raise ValueError("O nome da categoria não pode ficar vazio.")
                view.criar_categoria_rapida(nome)
                messagebox.showinfo("Sucesso", f"Categoria '{nome}' cadastrada!", parent=popup)
                txt_cat.delete(0, 'end')
                
                # Recarrega os dados nos seletores da janela mãe e do popup
                self.carregar_dados_bancos()
                atualizar_combo_exclusao()
            except Exception as e: 
                messagebox.showerror("Erro", str(e), parent=popup)
            
        ctk.CTkButton(popup, text="➕ Adicionar Categoria", fg_color="#2ECC71", hover_color="#27AE60", command=add).pack(fill="x", padx=20, pady=5)
        
        # --- SEÇÃO 2: EXCLUSÃO DE CATEGORIA COM SELETOR ---
        ctk.CTkLabel(popup, text="Selecione a Categoria para Remover:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(20,0))
        
        # Criando e empacotando o componente usando apenas o .pack() para não sumir
        cb_excluir_cat = CTkMenuScrollavelVerdadeiro(popup)
        cb_excluir_cat.pack(fill="x", padx=20, pady=5)

        # Função auxiliar interna para carregar/recarregar a lista do seletor de exclusão
        def atualizar_combo_exclusao():
            todas_categorias = view.listar_categorias()
            # Gera a lista com o ID embutido para saber exatamente qual remover: "Nome (ID: 1)"
            lista_opcoes = [f"{cat.categoria} (ID: {cat.id})" for cat in todas_categorias] if todas_categorias else []
            if lista_opcoes:
                cb_excluir_cat.configure(values=lista_opcoes)
                cb_excluir_cat.set("Escolha a categoria...")
            else:
                cb_excluir_cat.configure(values=["Nenhuma categoria cadastrada"])
                cb_excluir_cat.set("Nenhuma categoria cadastrada")

        def rem():
            selecao = cb_excluir_cat.get()
            if selecao == "Escolha a categoria..." or selecao == "Nenhuma categoria cadastrada":
                messagebox.showwarning("Aviso", "Por favor, selecione uma categoria válida na lista.", parent=popup)
                return
                
            try:
                # Adicionado o índice [1] para capturar o ID da lista gerada pelo split
                id_bruto = selecao.split("(ID: ")[1]
                id_categoria = int(id_bruto.replace(")", "").strip())
                
                # Adicionado o índice [0] para capturar o nome limpo da categoria
                nome_categoria = selecao.split(" (ID: ")[0].strip()
                
                if messagebox.askyesno("Confirmar Exclusão", f"Tem certeza que deseja remover a categoria '{nome_categoria}'?", parent=popup):
                    view.deletar_categoria(id_categoria)
                    messagebox.showinfo("Sucesso", "Categoria removida com sucesso!", parent=popup)
                    
                    self.carregar_dados_bancos()
                    atualizar_combo_exclusao()
            except Exception as e: 
                messagebox.showerror("Erro de Integridade", f"Não foi possível excluir.\nDetalhes: {e}", parent=popup)

            
        # Botão empacotado corretamente com .pack()
        btn_remover_cat = ctk.CTkButton(popup, text="🗑️ Remover Categoria Selecionada", fg_color="#E74C3C", hover_color="#C0392B", command=rem)
        btn_remover_cat.pack(fill="x", padx=20, pady=5)

        # Carrega a lista de categorias assim que a janelinha abre
        atualizar_combo_exclusao()

    def atualizar_visao_geral(self):
        try:
            view.reconciliar_saldos_em_lote()
        except Exception as e:
            print(f"[AVISO] Falha ao processar reconciliação: {e}")

        total = view.total_contas()
        self.lbl_total_valor.configure(text=f"R$ {formatar_moeda_br(total)}")

        for widget in self.frame_grade_contas.winfo_children():
            widget.destroy()

        # Cabeçalhos da tabela interna
        ctk.CTkLabel(self.frame_grade_contas, text="ID", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Banco / Instituição", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Saldo Disponível (R$)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Status (Selecione)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=10, pady=5)

        # Renderiza cada conta com os saldos perfeitamente reconciliados
        for idx, conta in enumerate(view.listar_contas(), start=1):
            ctk.CTkLabel(self.frame_grade_contas, text=str(conta.id)).grid(row=idx, column=0, padx=10, pady=2)
            
            ent_banco = ctk.CTkEntry(self.frame_grade_contas)
            ent_banco.insert(0, conta.banco)
            ent_banco.grid(row=idx, column=1, padx=10, pady=2, sticky="ew")

            ent_valor = ctk.CTkEntry(self.frame_grade_contas)
            ent_valor.insert(0, formatar_moeda_br(conta.valor))
            ent_valor.grid(row=idx, column=2, padx=10, pady=2, sticky="ew")

            cb_status = ctk.CTkComboBox(self.frame_grade_contas, values=["Ativo", "Inativo"], width=100)
            cb_status.set(conta.status.value)
            cb_status.grid(row=idx, column=3, padx=10, pady=2, sticky="ew")

            args = (conta.id, ent_banco, ent_valor, cb_status)
            ent_banco.bind("<Return>", lambda e, c_id=conta.id, eb=ent_banco, ev=ent_valor, cs=cb_status: self.salvar_linha_conta(c_id, eb, ev, cs))
            ent_valor.bind("<Return>", lambda e, c_id=conta.id, eb=ent_banco, ev=ent_valor, cs=cb_status: self.salvar_linha_conta(c_id, eb, ev, cs))
            cb_status.configure(command=lambda v, c_id=conta.id, eb=ent_banco, ev=ent_valor, cs=cb_status: self.salvar_linha_conta(c_id, eb, ev, cs))
        
        if hasattr(self, "cb_mov_banco"):
            self.carregar_dados_bancos()

    def abrir_popup_criar_conta(self):
        # Cria uma janela flutuante customizada vinculada à aplicação principal
        popup_conta = ctk.CTkToplevel(self)
        popup_conta.title("➕ Nova Conta Bancária")
        popup_conta.geometry("400x250")
        popup_conta.resizable(False, False)
        
        # Garante que o popup fique sempre por cima de tudo e capture o foco nativo
        popup_conta.attributes("-topmost", True)
        popup_conta.grab_set()

        # Posiciona o popup centralizado em relação à tela principal
        popup_conta.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (popup_conta.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (popup_conta.winfo_height() // 2)
        popup_conta.geometry(f"+{x}+{y}")

        # Componentes Visuais do Formulário
        ctk.CTkLabel(popup_conta, text="Cadastrar Nova Conta", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

        ctk.CTkLabel(popup_conta, text="Nome do Banco / Instituição:").pack(anchor="w", padx=30)
        txt_nome = ctk.CTkEntry(popup_conta, placeholder_text="Ex: Itaú, Nubank, Bradesco...")
        txt_nome.pack(fill="x", padx=30, pady=(0, 10))

        ctk.CTkLabel(popup_conta, text="Saldo Inicial Disponível (R$):").pack(anchor="w", padx=30)
        txt_saldo = ctk.CTkEntry(popup_conta, placeholder_text="0,00")
        txt_saldo.insert(0, "0,00")
        txt_saldo.pack(fill="x", padx=30, pady=(0, 20))

        # Função interna com a ordem invertida de fechamento
        def salvar_nova_conta(event=None):
            nome = txt_nome.get().strip()
            saldo_str = txt_saldo.get().strip().replace(".", "").replace(",", ".")

            try:
                if not nome:
                    raise ValueError("O nome do banco não pode ficar em branco.")
                
                saldo = float(saldo_str) if saldo_str else 0.0
                
                # Envia para a camada de persistência (view.py)
                nova_conta = Conta(banco=nome, valor=saldo)
                view.criar_conta(nova_conta)
                
                popup_conta.destroy()
                
                messagebox.showinfo("Sucesso", f"Conta '{nome}' cadastrada e pronta para uso!")
                
                # Atualiza os dados visuais do aplicativo
                self.atualizar_visao_geral()
                if hasattr(self, "filtrar_historico"):
                    self.filtrar_historico() # Garante a renderização do saldo inicial no extrato na hora
                
            except ValueError as e:
                messagebox.showerror("Erro de Preenchimento", f"Verifique os dados informados.\nDetalhes: {e}", parent=popup_conta)
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", str(e), parent=popup_conta)


        # Botão de confirmação
        btn_salvar = ctk.CTkButton(popup_conta, text="💾 Salvar Conta", fg_color="#2ECC71", hover_color="#27AE60", command=salvar_nova_conta)
        btn_salvar.pack(fill="x", padx=30)

        # Atalhos de teclado: Pressionar ENTER em qualquer campo envia o formulário, ESC fecha a janela
        txt_nome.bind("<Return>", salvar_nova_conta)
        txt_saldo.bind("<Return>", salvar_nova_conta)
        popup_conta.bind("<Escape>", lambda e: popup_conta.destroy())

        # Força o cursor a começar piscando diretamente no campo de texto do nome
        txt_nome.focus_set()

    def atualizar_visao_geral(self):
        # A reconciliação inteligente agora acontece nos bastidores sem a necessidade de botão na tela
        try:
            view.reconciliar_saldos_em_lote()
        except Exception as e:
            print(f"[AVISO] Falha ao processar reconciliação: {e}")

        total = view.total_contas()
        self.lbl_total_valor.configure(text=f"R$ {formatar_moeda_br(total)}")

        # Limpa e redesenha a tabela de contas de forma síncrona
        for widget in self.frame_grade_contas.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self.frame_grade_contas, text="ID", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Banco / Instituição", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Saldo Disponível (R$)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=10, pady=5)
        ctk.CTkLabel(self.frame_grade_contas, text="Status", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=10, pady=5)

        for idx, conta in enumerate(view.listar_contas(), start=1):
            ctk.CTkLabel(self.frame_grade_contas, text=str(conta.id)).grid(row=idx, column=0, padx=10, pady=2)
            
            ent_banco = ctk.CTkEntry(self.frame_grade_contas)
            ent_banco.insert(0, conta.banco)
            ent_banco.grid(row=idx, column=1, padx=10, pady=2, sticky="ew")

            ent_valor = ctk.CTkEntry(self.frame_grade_contas)
            ent_valor.insert(0, formatar_moeda_br(conta.valor))
            ent_valor.grid(row=idx, column=2, padx=10, pady=2, sticky="ew")

            cb_status = ctk.CTkComboBox(self.frame_grade_contas, values=["Ativo", "Inativo"], width=100)
            cb_status.set(conta.status.value)
            cb_status.grid(row=idx, column=3, padx=10, pady=2, sticky="ew")

            args = (conta.id, ent_banco, ent_valor, cb_status)
            ent_banco.bind("<Return>", lambda e, a=args: self.salvar_linha_conta(*a))
            ent_valor.bind("<Return>", lambda e, a=args: self.salvar_linha_conta(*a))
            cb_status.configure(command=lambda v, a=args: self.salvar_linha_conta(*a))
        
        if hasattr(self, "cb_mov_banco"):
            self.carregar_dados_bancos()

    def salvar_linha_conta(self, id_conta, ent_banco, ent_valor, cb_status):
        try:
            banco = ent_banco.get().strip()
            # Aceita vírgula ou ponto nativamente na hora de digitar
            novo_saldo = float(ent_valor.get().strip().replace(".", "").replace(",", "."))
            status = cb_status.get().strip()

            # Atualiza diretamente os campos editados sem criar históricos automáticos indesejados
            view.atualizar_conta(id_conta, banco, novo_saldo, status)
            messagebox.showinfo("Sucesso", "Dados da conta atualizados com sucesso!")
            
            # Recarrega a tela de forma limpa
            self.atualizar_visao_geral()
            if hasattr(self, "filtrar_historico"):
                self.filtrar_historico()

        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Verifique os dados digitados.\nDetalhes: {e}")
    
    # --- ABA 2: NOVA MOVIMENTAÇÃO ---
    def configurar_aba_movimentacao(self):
        aba = self.tabview.tab("Nova Movimentação")
        aba.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(aba, text="Lançar Nova Movimentação", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=15, sticky="w")

        ctk.CTkLabel(aba, text="Escolha a Conta / Banco:").grid(row=1, column=0, padx=20, pady=8, sticky="w")
        self.cb_mov_banco = CTkMenuScrollavelVerdadeiro(aba)
        self.cb_mov_banco.grid(row=1, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(aba, text="Escolha a Categoria:").grid(row=2, column=0, padx=20, pady=8, sticky="w")
        self.cb_mov_categoria = CTkMenuScrollavelVerdadeiro(aba)
        self.cb_mov_categoria.grid(row=2, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(aba, text="Descrição:").grid(row=3, column=0, padx=20, pady=8, sticky="w")
        self.txt_mov_descricao = ctk.CTkEntry(aba, placeholder_text="Ex: Compras Supermercado, Assinatura...")
        self.txt_mov_descricao.grid(row=3, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(aba, text="Valor (R$):").grid(row=4, column=0, padx=20, pady=8, sticky="w")
        self.txt_mov_valor = ctk.CTkEntry(aba, placeholder_text="0,00")
        self.txt_mov_valor.grid(row=4, column=1, padx=20, pady=8, sticky="ew")

        ctk.CTkLabel(aba, text="Tipo de Fluxo:").grid(row=5, column=0, padx=20, pady=8, sticky="w")
        self.cb_mov_tipo = ctk.CTkComboBox(aba, values=["Entrada", "Saída"], command=self._monitorar_tipo_fluxo_parcelas)
        self.cb_mov_tipo.grid(row=5, column=1, padx=20, pady=8, sticky="ew")

        # --- CONTAINER DE FLUXOS AVANÇADOS ---
        ctk.CTkLabel(aba, text="Opções Avançadas:").grid(row=6, column=0, padx=20, pady=8, sticky="w")
        
        self.frame_opcoes_avancadas = ctk.CTkFrame(aba, fg_color="transparent")
        self.frame_opcoes_avancadas.grid(row=6, column=1, padx=20, pady=8, sticky="w")
        
        self.check_parcelado = ctk.CTkCheckBox(self.frame_opcoes_avancadas, text="Parcelado", command=self._alternar_modos_exclusivos_parcela)
        self.check_parcelado.pack(side="left", padx=(0, 10))
        
        self.lbl_qtd_parcelas = ctk.CTkLabel(self.frame_opcoes_avancadas, text="Qtd:")
        self.lbl_qtd_parcelas.pack(side="left", padx=2)
        self.txt_qtd_parcelas = ctk.CTkEntry(self.frame_opcoes_avancadas, width=45, justify="center")
        self.txt_qtd_parcelas.insert(0, "1")
        self.txt_qtd_parcelas.pack(side="left", padx=2)

        # Caixa de seleção para Cobrança Recorrente de 12 meses
        self.check_recorrente = ctk.CTkCheckBox(self.frame_opcoes_avancadas, text="Cobrança Recorrente (12 Meses)", command=self._alternar_modos_exclusivos_recorrente)
        self.check_recorrente.pack(side="left", padx=(15, 0))

        ctk.CTkLabel(aba, text="Data do Lançamento / Início:").grid(row=7, column=0, padx=20, pady=8, sticky="w")
        self.txt_mov_data = ctk.CTkEntry(aba, placeholder_text="DD/MM/AAAA")
        self.txt_mov_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_mov_data.grid(row=7, column=1, padx=20, pady=8, sticky="ew")

        self.btn_salvar_mov = ctk.CTkButton(aba, text="💾 Confirmar Lançamento", fg_color="#2ECC71", hover_color="#27AE60", command=self.executar_movimentacao)
        self.btn_salvar_mov.grid(row=8, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        
        self.cb_mov_tipo.set("Saída")
        self._monitorar_tipo_fluxo_parcelas("Saída")

    def _monitorar_tipo_fluxo_parcelas(self, escolha):
        if escolha == "Entrada":
            self.check_parcelado.deselect()
            self.check_recorrente.deselect()
            self.check_parcelado.configure(state="disabled")
            self.check_recorrente.configure(state="disabled")
            self.txt_qtd_parcelas.configure(state="disabled")
        else:
            self.check_parcelado.configure(state="normal")
            self.check_recorrente.configure(state="normal")
            self._alternar_modos_exclusivos_parcela()

    def _alternar_modos_exclusivos_parcela(self):
        # Regra de Interface: Se selecionar parcelado, desmarca a recorrência automática
        if self.check_parcelado.get() == 1:
            self.check_recorrente.deselect()
            self.txt_qtd_parcelas.configure(state="normal")
        else:
            self.txt_qtd_parcelas.configure(state="disabled")
   
    def _alternar_visibilidade_parcelas(self):
        # Habilita ou desabilita a digitação da quantidade de parcelas se a box estiver ticada
        if self.check_parcelado.get() == 1:
            self.txt_qtd_parcelas.configure(state="normal")
        else:
            self.txt_qtd_parcelas.configure(state="disabled")

    def _alternar_modos_exclusivos_recorrente(self):
        # Regra de Interface: Se selecionar recorrente, desmarca e desabilita o parcelamento
        if self.check_recorrente.get() == 1:
            self.check_parcelado.deselect()
            self.txt_qtd_parcelas.configure(state="disabled")

    def executar_movimentacao(self):
        try:
            banco_selecionado = self.cb_mov_banco.get().split(" (R$")[0].strip()
            cat_selecionada = self.cb_mov_categoria.get()
            tipo_fluxo = self.cb_mov_tipo.get()
            
            if banco_selecionado in ["Selecione um banco...", "Nenhuma conta ativa"]:
                raise ValueError("Por favor, selecione um banco válido.")
            if cat_selecionada == "Selecione uma categoria...":
                raise ValueError("Por favor, selecione uma categoria válida.")

            descricao = self.txt_mov_descricao.get().strip()
            # Limpeza robusta para converter a moeda BR (1.500,50 ou 1,50) para float Python puro
            valor_limpo = self.txt_mov_valor.get().strip().replace(".", "").replace(",", ".")
            valor = float(valor_limpo)
            
            data_obj = datetime.strptime(self.txt_mov_data.get().strip(), "%d/%m/%Y").date()
            
            e_parcelado = bool(self.check_parcelado.get() == 1)
            e_recorrente = bool(self.check_recorrente.get() == 1)

            if not descricao:
                raise ValueError("A descrição da movimentação não pode ficar em branco.")

            # Direcionamento inteligente baseado nas caixas marcadas pelo usuário
            if e_recorrente:
                view.movimentar_dinheiro_recorrente(
                    banco_nome=banco_selecionado, categoria_nome=cat_selecionada,
                    descricao_base=descricao, valor=valor, tipo_str=tipo_fluxo, data_base=data_obj
                )
            else:
                qtd_parcelas = int(self.txt_qtd_parcelas.get()) if e_parcelado else 1
                view.movimentar_dinheiro_parcelado(
                    banco_nome=banco_selecionado, categoria_nome=cat_selecionada, descricao_base=descricao,
                    valor_total=valor, tipo_str=tipo_fluxo, data_base=data_obj, e_parcelado=e_parcelado, qtd_parcelas=qtd_parcelas
                )
            
            messagebox.showinfo("Sucesso", "Lançamento registrado com sucesso!")
            
            self.atualizar_visao_geral()
            self.filtrar_historico()
            
            self.txt_mov_descricao.delete(0, 'end')
            self.txt_mov_valor.delete(0, 'end')
            self.check_parcelado.deselect()
            self.check_recorrente.deselect()
            self.txt_qtd_parcelas.configure(state="disabled")
            
        except ValueError as e:
            messagebox.showerror("Erro de Preenchimento", f"Verifique as informações digitadas.\nDetalhes: {e}")

    # --- ABA 3: TRANSFERÊNCIA ---
    def configurar_aba_transferencia(self):
        aba = self.tabview.tab("Transferência")
        aba.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(aba, text="Transferir Saldo Entre Bancos", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="w")

        ctk.CTkLabel(aba, text="Conta de Origem (Débito):").grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.cb_trans_origem = CTkMenuScrollavelVerdadeiro(aba)
        self.cb_trans_origem.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(aba, text="Conta de Destino (Crédito):").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.cb_trans_destino = CTkMenuScrollavelVerdadeiro(aba)
        self.cb_trans_destino.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(aba, text="Valor da Operação (R$):").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.txt_trans_valor = ctk.CTkEntry(aba, placeholder_text="0.00")
        self.txt_trans_valor.grid(row=3, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(aba, text="Histórico/Descrição:").grid(row=4, column=0, padx=20, pady=10, sticky="w")
        self.txt_trans_desc = ctk.CTkEntry(aba, placeholder_text="Ex: Ajuste de saldos")
        self.txt_trans_desc.grid(row=4, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(aba, text="Data da Transferência:").grid(row=5, column=0, padx=20, pady=10, sticky="w")
        self.txt_trans_data = ctk.CTkEntry(aba, placeholder_text="DD/MM/AAAA")
        self.txt_trans_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_trans_data.grid(row=5, column=1, padx=20, pady=10, sticky="ew")

        self.btn_exec_trans = ctk.CTkButton(aba, text="💸 Executar Transferência", fg_color="#3498DB", hover_color="#2980B9", command=self.executar_transferencia)
        self.btn_exec_trans.grid(row=6, column=0, columnspan=2, padx=20, pady=30, sticky="ew")

    def executar_transferencia(self):
        try:
            selecao_origem = self.cb_trans_origem.get()
            selecao_destino = self.cb_trans_destino.get()
            
            if selecao_origem == "Selecione a origem..." or selecao_origem == "Nenhuma conta ativa":
                raise ValueError("Selecione uma conta de origem válida.")
            if selecao_destino == "Selecione o destino..." or selecao_destino == "Nenhuma conta ativa":
                raise ValueError("Selecione uma conta de destino válida.")

            # Extrai o nome bruto dos bancos limpando a parte do saldo
            banco_origem = selecao_origem.split(" (R$")[0].strip()
            banco_destino = selecao_destino.split(" (R$")[0].strip()
            
            if banco_origem == banco_destino:
                raise ValueError("A conta de origem e destino não podem ser iguais.")
                
            id_origem = self.mapa_contas[banco_origem]
            id_destino = self.mapa_contas[banco_destino]
            valor = float(self.txt_trans_valor.get().replace(",", "."))
            desc = self.txt_trans_desc.get()
            data_obj = datetime.strptime(self.txt_trans_data.get().strip(), "%d/%m/%Y").date()

            view.transferir_saldo(id_origem, id_destino, valor, desc, categoria_id=1, data_movimentacao=data_obj)
            messagebox.showinfo("Sucesso", "Transferência efetuada com sucesso!")
            
            # Recarrega as grades e atualiza as listas suspensas com os saldos atualizados
            self.atualizar_visao_geral()
            self.carregar_dados_bancos()
            self.filtrar_historico()
            
            self.txt_trans_valor.delete(0, 'end')
            self.txt_trans_desc.delete(0, 'end')
        except ValueError as e:
            messagebox.showerror("Erro", str(e))

    # --- ABA 4: EXTRATO ---
    def configurar_aba_extrato(self):
        self.aba_extrato = self.tabview.tab("Extrato")
        self.aba_extrato.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        self.aba_extrato.grid_rowconfigure(1, weight=1)

        hoje = datetime.now()
        primeiro_dia = hoje.replace(day=1).strftime("%d/%m/%Y")
        _, ultimo_dia_num = calendar.monthrange(hoje.year, hoje.month)
        ultimo_dia = hoje.replace(day=ultimo_dia_num).strftime("%d/%m/%Y")

        ctk.CTkLabel(self.aba_extrato, text="Início:").grid(row=0, column=0, padx=(10, 2), pady=15, sticky="w")
        self.txt_ext_inicio = ctk.CTkEntry(self.aba_extrato, width=90, justify="center")
        self.txt_ext_inicio.insert(0, primeiro_dia)
        self.txt_ext_inicio.grid(row=0, column=0, padx=(50, 5), pady=15, sticky="w")

        ctk.CTkLabel(self.aba_extrato, text="Fim:").grid(row=0, column=1, padx=(5, 2), pady=15, sticky="w")
        self.txt_ext_fim = ctk.CTkEntry(self.aba_extrato, width=90, justify="center")
        self.txt_ext_fim.insert(0, ultimo_dia)
        self.txt_ext_fim.grid(row=0, column=1, padx=(40, 10), pady=15, sticky="w")

        ctk.CTkLabel(self.aba_extrato, text="Banco:").grid(row=0, column=2, padx=(10, 2), pady=15, sticky="w")
        self.cb_ext_banco = CTkMenuScrollavelVerdadeiro(self.aba_extrato)
        self.cb_ext_banco.grid(row=0, column=2, padx=(60, 10), pady=15, sticky="ew")

        self.btn_filtrar = ctk.CTkButton(self.aba_extrato, text="🔍 Filtrar", width=100, command=self.filtrar_historico)
        self.btn_filtrar.grid(row=0, column=3, padx=10, pady=15, sticky="ew")
        
        ctk.CTkButton(self.aba_extrato, text="📥 Excel (CSV)", fg_color="#27AE60", hover_color="#1E8449", width=110, command=self.exportar_extrato_csv).grid(row=0, column=5, padx=5, pady=15, sticky="ew")
        ctk.CTkButton(self.aba_extrato, text="📄 Gerar PDF", fg_color="#C0392B", hover_color="#922B21", width=110, command=self.exportar_extrato_pdf).grid(row=0, column=6, padx=(5, 10), pady=15, sticky="ew")

        self.frame_tabela_extrato = ctk.CTkFrame(self.aba_extrato)
        self.frame_tabela_extrato.grid(row=1, column=0, columnspan=7, padx=10, pady=5, sticky="nsew")

        # Estilização do Treeview nativo de alta velocidade
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=25, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#333333", foreground="white", borderwidth=0)

        self.tree_extrato = ttk.Treeview(self.frame_tabela_extrato, columns=("id", "data", "descricao", "banco", "categoria", "tipo", "valor"), show="headings")
        self.tree_extrato.heading("id", text="ID")
        self.tree_extrato.heading("data", text="Data")
        self.tree_extrato.heading("descricao", text="Descrição")
        self.tree_extrato.heading("banco", text="Banco")
        self.tree_extrato.heading("categoria", text="Categoria")
        self.tree_extrato.heading("tipo", text="Tipo")
        self.tree_extrato.heading("valor", text="Valor")

        self.tree_extrato.column("id", width=50, anchor="center")
        self.tree_extrato.column("data", width=95, anchor="center")
        self.tree_extrato.column("descricao", width=250, anchor="w")
        self.tree_extrato.column("banco", width=130, anchor="w")
        self.tree_extrato.column("categoria", width=130, anchor="w")
        self.tree_extrato.column("tipo", width=90, anchor="center")
        self.tree_extrato.column("valor", width=110, anchor="e")
        self.tree_extrato.pack(expand=True, fill="both", padx=5, pady=5)

        # Trata os gatilhos de duplo clique e teclado
        self.tree_extrato.bind("<Double-1>", self.editar_linha_extrato_popup)
        self.tree_extrato.bind("<Delete>", lambda e: self.excluir_movimentacao_tree())

        self.lbl_ajuda_extrato = ctk.CTkLabel(self.aba_extrato, text="💡 Dica: Dê duplo clique em uma linha para editar ou pressione DELETE para excluir um registro.", font=ctk.CTkFont(size=11, slant="italic"))
        self.lbl_ajuda_extrato.grid(row=2, column=0, columnspan=7, padx=10, pady=5, sticky="w")

    def filtrar_historico(self):
        try:
            data_ini = datetime.strptime(self.txt_ext_inicio.get().strip(), "%d/%m/%Y").date()
            data_fim = datetime.strptime(self.txt_ext_fim.get().strip(), "%d/%m/%Y").date()
            banco_sel = self.cb_ext_banco.get()

            self.ultimos_resultados_filtrados = view.buscar_historicos_avancado(data_ini, data_fim, banco_sel)

            for item in self.tree_extrato.get_children():
                self.tree_extrato.delete(item)

            for item in self.ultimos_resultados_filtrados:
                nome_banco = item.conta.banco if item.conta else "N/A"
                nome_cat = item.categoria.categoria if item.categoria else "Geral"
                
                self.tree_extrato.insert("", "end", values=(
                    item.id,
                    item.data_formatada,
                    item.descricao,
                    nome_banco,
                    nome_cat,
                    item.tipo.value,
                    f"R$ {formatar_moeda_br(item.valor)}"
                ))
        except ValueError as e:
            messagebox.showerror("Erro de Filtro", f"Use o formato correto DD/MM/AAAA.\nErro: {e}")

    def excluir_movimentacao_tree(self):
        item_selecionado = self.tree_extrato.selection()
        if not item_selecionado: return
        valores = self.tree_extrato.item(item_selecionado, "values")
        id_historico = int(valores[0])
        self.excluir_movimentacao_grade(id_historico)

    def editar_linha_extrato_popup(self, event):
        """CORRIGIDO: Instancia uma janela real estável (ctk.CTk) sem grab_set para evitar travamento no Linux/Wayland"""
        item_selecionado = self.tree_extrato.selection()
        if not item_selecionado: return
        valores = self.tree_extrato.item(item_selecionado, "values")
        
        id_hist = int(valores[0])
        data_atual = valores[1]
        desc_atual = valores[2]
        banco_atual = valores[3]
        cat_atual = valores[4]
        tipo_atual = valores[5]
        valor_atual = valores[6].replace("R$", "").replace(" ", "").strip()

        # Janela base independente à prova de telas em branco no Linux
        popup = ctk.CTk()
        popup.title(f"📝 Editar Lançamento ID {id_hist}")
        popup.geometry("420x550")
        popup.resizable(False, False)

        # Força o posicionamento em primeiro plano acima da janela mãe
        popup.attributes("-topmost", True)
        
        # --- REMOVIDO O GRAB_SET() PARA MATAR O ERRO WINDOW NOT VIEWABLE ---
        popup.update() # Apenas força a renderização inicial dos frames na GPU
        # ------------------------------------------------------------------

        popup.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(popup, text="Data (DD/MM/AAAA):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=40, pady=(15,0))
        txt_data = ctk.CTkEntry(popup)
        txt_data.insert(0, data_atual)
        txt_data.grid(row=1, column=0, sticky="ew", padx=40, pady=(0,10))

        ctk.CTkLabel(popup, text="Descrição:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=40, pady=(5,0))
        txt_desc = ctk.CTkEntry(popup)
        txt_desc.insert(0, desc_atual)
        txt_desc.grid(row=3, column=0, sticky="ew", padx=40, pady=(0,10))

        ctk.CTkLabel(popup, text="Banco:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", padx=40, pady=(5,0))
        cb_banco = CTkMenuScrollavelVerdadeiro(popup, values=[c.banco for c in view.listar_contas()])
        cb_banco.set(banco_atual)
        cb_banco.grid(row=5, column=0, sticky="ew", padx=40, pady=(0,10))

        ctk.CTkLabel(popup, text="Categoria:", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, sticky="w", padx=40, pady=(5,0))
        cb_cat = CTkMenuScrollavelVerdadeiro(popup, values=[cat.categoria for cat in view.listar_categorias()])
        cb_cat.set(cat_atual)
        cb_cat.grid(row=7, column=0, sticky="ew", padx=40, pady=(0,10))

        ctk.CTkLabel(popup, text="Tipo:", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, sticky="w", padx=40, pady=(5,0))
        cb_tipo = CTkMenuScrollavelVerdadeiro(popup, values=["Entrada", "Saída"])
        cb_tipo.set(tipo_atual)
        cb_tipo.grid(row=9, column=0, sticky="ew", padx=40, pady=(0,10))

        ctk.CTkLabel(popup, text="Valor Monetário (R$):", font=ctk.CTkFont(weight="bold")).grid(row=10, column=0, sticky="w", padx=40, pady=(5,0))
        txt_valor = ctk.CTkEntry(popup)
        txt_valor.insert(0, valor_atual)
        txt_valor.grid(row=11, column=0, sticky="ew", padx=40, pady=(0,20))

        def salvar():
            try:
                nova_data = datetime.strptime(txt_data.get().strip(), "%d/%m/%Y").date()
                descricao = txt_desc.get().strip()
                banco_nome = cb_banco.get().strip()
                categoria_nome = cb_cat.get().strip()
                tipo_str = cb_tipo.get().strip()
                valor = float(txt_valor.get().strip().replace(".", "").replace(",", "."))

                view.atualizar_historico(id_hist, descricao, valor, nova_data, banco_nome, categoria_nome, tipo_str)
                popup.destroy()
                messagebox.showinfo("Sucesso", "Lançamento updated e saldos recalculados!")
                
                self.atualizar_visao_geral()
                self.filtrar_historico()
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", f"Verifique as informações digitadas.\nErro: {e}", parent=popup)

        btn_salvar = ctk.CTkButton(popup, text="💾 Salvar Alterações", fg_color="#2ECC71", hover_color="#27AE60", command=salvar)
        btn_salvar.grid(row=12, column=0, sticky="ew", padx=40, pady=10)
        
        popup.mainloop()

    def excluir_movimentacao_grade(self, id_historico):
        if messagebox.askyesno("Confirmar Exclusão", f"Deseja excluir definitivamente o lançamento ID {id_historico}?\nO saldo bancário associado será corrigido automaticamente."):
            try:
                view.deletar_movimentacao_sem_restricao(id_historico)
                messagebox.showinfo("Sucesso", "Movimentação excluída e saldo atualizado!")
                self.atualizar_visao_geral()
                self.filtrar_historico()
            except Exception as e:
                messagebox.showerror("Erro ao excluir", str(e))

    def exportar_extrato_csv(self):
        if not hasattr(self, 'ultimos_resultados_filtrados') or not self.ultimos_resultados_filtrados:
            messagebox.showwarning("Aviso", "Não existem dados filtrados na tela para exportar. Clique em Filtrar primeiro.")
            return

        caminho_arquivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Arquivo CSV (Excel)", "*.csv"), ("Todos os arquivos", "*.*")],
            title="Salvar Extrato Filtrado"
        )
        if not caminho_arquivo:
            return

        try:
            with open(caminho_arquivo, mode='w', newline='', encoding='utf-8-sig') as arquivo:
                escritor = csv.writer(arquivo, delimiter=';')
                escritor.writerow(["ID", "Data", "Descrição", "Banco", "Categoria", "Tipo", "Valor (R$)"])
                
                for item in self.ultimos_resultados_filtrados:
                    nome_banco = item.conta.banco if item.conta else "N/A"
                    nome_cat = item.categoria.categoria if item.categoria else "Geral"
                    sinal = "" if item.tipo == Tipos.ENTRADA else "-"
                    
                    escritor.writerow([
                        item.id,
                        item.data_formatada,
                        item.descricao,
                        nome_banco,
                        nome_cat,
                        item.tipo.value,
                        f"{sinal}{item.valor:.2f}".replace(".", ",")
                    ])
            messagebox.showinfo("Sucesso", "Extrato exportado com sucesso em formato CSV!")
        except Exception as e:
            messagebox.showerror("Erro ao exportar", f"Não foi possível salvar o arquivo:\n{e}")

    def salvar_linha_extrato(self, id_hist, ent_data, ent_desc, cb_banco, cb_cat, cb_tipo, ent_valor):
        """Função mantida para compatibilidade interna do motor gráfico"""
        pass

    def exportar_extrato_pdf(self):
        if not hasattr(self, 'ultimos_resultados_filtrados') or not self.ultimos_resultados_filtrados:
            messagebox.showwarning("Aviso", "Não existem dados filtrados na tela para exportar. Clique em Filtrar primeiro.")
            return

        caminho_arquivo = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Documento PDF", "*.pdf")],
            title="Exportar Relatório PDF"
        )
        if not caminho_arquivo: return

        try:
            doc = SimpleDocTemplate(caminho_arquivo, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=54)
            elementos = []

            estilos = getSampleStyleSheet()
            estilo_titulo = ParagraphStyle('TituloPDF', parent=estilos['Heading1'], fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor("#2C3E50"), spaceAfter=6)
            estilo_sub = ParagraphStyle('SubPDF', parent=estilos['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor("#7F8C8D"), spaceAfter=15)
            estilo_celula = ParagraphStyle('CelulaPDF', parent=estilos['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#2C3E50"))
            estilo_header = ParagraphStyle('HeaderPDF', parent=estilos['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.white)

            elementos.append(Paragraph("RELATÓRIO FINANCEIRO PESSOAL", estilo_titulo))
            data_emissao = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
            elementos.append(Paragraph(f"Extraído em: {data_emissao} | Período: {self.txt_ext_inicio.get()} até {self.txt_ext_fim.get()}", estilo_sub))

            dados_tabela = [[
                Paragraph("ID", estilo_header),
                Paragraph("Data", estilo_header),
                Paragraph("Descrição", estilo_header),
                Paragraph("Banco", estilo_header),
                Paragraph("Categoria", estilo_header),
                Paragraph("Tipo", estilo_header),
                Paragraph("Valor", estilo_header)
            ]]

            total_entradas = 0.0
            total_saidas = 0.0

            for item in self.ultimos_resultados_filtrados:
                nome_banco = item.conta.banco if item.conta else "N/A"
                nome_cat = item.categoria.categoria if item.categoria else "Geral"
                
                if item.tipo == Tipos.ENTRADA:
                    total_entradas += item.valor
                    cor_valor_tipo = "#27AE60"
                    texto_valor = f"R$ {formatar_moeda_br(item.valor)}"
                else:
                    total_saidas += item.valor
                    cor_valor_tipo = "#C0392B"
                    texto_valor = f"- R$ {formatar_moeda_br(item.valor)}"

                estilo_valor_dinamico = ParagraphStyle('ValPDF', parent=estilo_celula, textColor=colors.HexColor(cor_valor_tipo))

                dados_tabela.append([
                    Paragraph(str(item.id), estilo_celula),
                    Paragraph(item.data_formatada, estilo_celula),
                    Paragraph(item.descricao, estilo_celula),
                    Paragraph(nome_banco, estilo_celula),
                    Paragraph(nome_cat, estilo_celula),
                    Paragraph(item.tipo.value, estilo_celula),
                    Paragraph(texto_valor, estilo_valor_dinamico)
                ])

            larguras = [35, 65, 170, 95, 95, 50, 80]
            tabela_pdf = Table(dados_tabela, colWidths=larguras, repeatRows=1)

            estilo_tabela = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LINEBELOW', (0,0), (-1,0), 1.5, colors.HexColor("#1A252F")),
                ('LINEBELOW', (0,1), (-1,-1), 0.5, colors.HexColor("#ECF0F1")),
            ])

            for i in range(1, len(dados_tabela)):
                if i % 2 == 0:
                    estilo_tabela.add('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8F9F9"))

            tabela_pdf.setStyle(estilo_tabela)
            elementos.append(tabela_pdf)
            elementos.append(Spacer(1, 20))

            elementos.append(Paragraph("<b>Resumo do Período Filtrado:</b>", estilo_celula))
            elementos.append(Spacer(1, 5))
            
            dados_resumo = [
                [Paragraph(f"Total de Entradas (Crédito): <font color='#27AE60'><b>R$ {formatar_moeda_br(total_entradas)}</b></font>", estilo_celula)],
                [Paragraph(f"Total de Saídas (Débito): <font color='#C0392B'><b>R$ {formatar_moeda_br(total_saidas)}</b></font>", estilo_celula)],
                [Paragraph(f"Saldo Líquido no Período: <b>R$ {formatar_moeda_br(total_entradas - total_saidas)}</b>", estilo_celula)]
            ]
            tabela_resumo = Table(dados_resumo, colWidths=[540])
            tabela_resumo.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EAEDED")),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#BDC3C7"))
            ]))
            elementos.append(tabela_resumo)

            doc.build(elementos, canvasmaker=CanvasNumerado)
            messagebox.showinfo("Sucesso", "Relatório financeiro em PDF exportado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro ao exportar", f"Não foi possível gerar o PDF:\n{e}")

if __name__ == "__main__":
    app = AppFinanceiro()
    app.mainloop()