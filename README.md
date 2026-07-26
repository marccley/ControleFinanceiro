# 📊 Sistema de Controle Financeiro Avançado

Este é um aplicativo desktop moderno de gestão e controle financeiro pessoal desenvolvido em **Python**. O sistema utiliza uma arquitetura robusta dividida em banco de dados local relacional, regras de negócio contábeis automatizadas e uma interface gráfica rica, elástica e dinâmica.

## 🛠️ Tecnologias Utilizadas

*   **Python 3.14** (Linguagem base)
*   **CustomTkinter**: Interface gráfica moderna com suporte nativo a modo escuro/claro e componentes de scroll customizados.
*   **SQLModel / SQLAlchemy**: Mapeamento Objeto-Relacional (ORM) para interações seguras e estáveis com o banco de dados.
*   **SQLite**: Banco de dados relacional leve em arquivo local.
*   **ReportLab**: Geração de relatórios executivos em formato PDF com tabelas zebradas, cores dinâmicas e sumários contábeis consolidados.
*   **Matplotlib**: Renderização de gráficos de barras horizontais com legendas inclinadas para distribuição de saldos ativos.
*   **PyInstaller**: Empacotamento do ecossistema em executáveis independentes para distribuição em Windows (`.exe`) e Linux.

## 💡 Créditos e Desenvolvimento Co-Piloto

### 🎬 Projeto Base e Inspiração
Este software foi construído tendo como fundação conceitual e inspiração o **Projeto 1** do canal **[Python Puro](https://youtube.com)** (disponível no roteiro público do Notion do Canal). Agradecimentos ao canal por disponibilizar a lógica inicial de terminal estruturada em SQLModel que serviu de semente para este sistema.

### 🤖 Co-Piloto Estratégico
A evolução estrutural, expansão das regras de negócio e a transição completa do terminal para a interface gráfica moderna foram desenvolvidas com o auxílio estratégico do **Google Gemini**, atuando em formato de *Pair Programming*. 

A IA atuou diretamente na:
*   Refatoração de scripts de terminal legados para o ecossistema gráfico do **CustomTkinter**.
*   Criação de componentes dinâmicos de interface (menus suspensos customizados com suporte a scroll nativo do mouse e travas contra janelas flutuantes que perdem o foco).
*   Estruturação da lógica matemática para desmembramento automático de despesas parceladas (com divisão exata de centavos na última parcela) e geração em lote de cobranças recorrentes de 12 meses.
*   Tratamento de strings e conversões de máscaras de moedas para o padrão brasileiro (ponto para milhar e vírgula para decimal).

## 🚀 Funcionalidades e Regras de Negócio

1.  **Visão Geral (Dashboard Otimizado)**:
    *   Exibição do patrimônio combinado recalculado em tempo real.
    *   **Layout Elástico**: Container central de contas expandido verticalmente para máxima visualização de dados, com botões de ação e gráficos mantidos harmonicamente na base.
    *   Grade de edição direta por linha (altere dados de bancos ou saldos e salve na hora pressionando a tecla `Enter`).
    *   Botão pop-up unificado para **Criar Nova Conta** com trava de foco absoluto (`grab_set`) que gera automaticamente um lançamento de abertura no histórico caso o saldo inicial seja maior que R$ 0,00.
    *   Botões de **Excluir Conta** e **Gerenciar Categorias** equipados com caixas de seleção suspensas e protegidos por **travas de integridade** (só permite a remoção se o banco ou categoria não possuírem movimentações associadas no histórico).
2.  **Nova Movimentação (Fluxos Avançados)**:
    *   Campos com dropdowns dinâmicos que exibem os saldos reais atuais de cada instituição no padrão brasileiro (`1.500,00`).
    *   **Compra Parcelada**: Desmembra automaticamente despesas futuras mês a mês, inserindo o sufixo `(parcela X de X)` na descrição do lançamento (mecanismo inteligente exclusivo para o tipo Saída).
    *   **Cobrança Recorrente**: Replica de forma automatizada o faturamento selecionado por 12 meses consecutivos com o sufixo `(Recorrente X/12)`.
3.  **Transferências entre Bancos**:
    *   Movimentação segura de fundos entre contas com validações contra origens e destinos idênticos.
4.  **Extrato Dinâmico (Auditoria e Controle)**:
    *   Filtro cronológico avançado que exibe lançamentos na ordem natural tradicional (da transação **mais antiga no topo para a mais nova por último**).
    *   Edição direta de qualquer célula do histórico (mudar banco, categoria ou tipo via dropdowns integrados na linha recalcula e estorna saldos automaticamente no SQLite).
    *   Botão de lixeira individual por linha: remove o lançamento sem restrições e ajusta o saldo associado na mesma hora.
5.  **Reconciliação e Trava Contábil**:
    *   O motor de auditoria recalcula o saldo dos bancos do início até o dia presente de forma 100% automatizada por trás dos panos. 
    *   **Trava Cronológica**: Movimentações, parcelas ou recorrências agendadas para datas futuras permanecem salvas de forma íntegra no extrato, mas são ignoradas no saldo atual do dia de hoje, sendo incorporadas automaticamente apenas quando a data for alcançada.
6.  **Exportação Avançada Dupla**:
    *   **Excel (CSV)**: Emite um arquivo estruturado com delimitadores compatíveis com planilhas digitais.
    *   **Relatório PDF**: Gera um documento executivo profissional, com linhas zebradas, identificação de transações em verde (entradas) e vermelho (saídas), rodapés com paginação dinâmica e um painel consolidado com o saldo líquido final do período.

## 📦 Como Instalar e Executar

### Pré-requisitos
Certifique-se de possuir o Python instalado em sua máquina e o pacote do Tkinter caso utilize Linux (`sudo apt install python3-tk`).

1.  Clone este repositório em sua máquina:
    ```bash
    git clone https://github.com
    cd nome-do-repositorio
    ```
2.  Instale todas as bibliotecas necessárias para o ecossistema:
    ```bash
    pip install customtkinter sqlmodel matplotlib reportlab pyinstaller
    ```
3.  Execute a aplicação através do arquivo centralizador de rotas:
    ```bash
    python main.py
    ```