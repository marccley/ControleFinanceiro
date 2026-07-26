from models import Conta, Categoria, engine, Status, Historico, Tipos
from sqlmodel import Session, select
from datetime import date, datetime
from sqlalchemy.orm import joinedload
from calendar import monthrange

def criar_conta(conta: Conta):
    with Session(engine) as session:
        statement = select(Conta).where(Conta.banco == conta.banco)
        results = session.exec(statement).all()
        if results:
            raise ValueError("Já existe uma conta cadastrada neste banco!")
            
        session.add(conta)
        session.commit() # Salva primeiro para gerar o ID da conta
        session.refresh(conta)
        
        # --- Se o saldo inicial for maior que zero, gera o histórico de abertura ---
        if conta.valor > 0:
            historico_abertura = Historico(
                data=date.today(), # Dia corrente
                descricao="Saldo Inicial de Abertura da Conta",
                tipo=Tipos.ENTRADA,
                valor=conta.valor,
                categoria_id=1, # Categoria Geral padrão
                conta_id=conta.id
            )
            session.add(historico_abertura)
            session.commit()
            
        return conta

def movimentar_dinheiro_parcelado(banco_nome: str, categoria_nome: str, descricao_base: str, valor_total: float, tipo_str: str, data_base: date, e_parcelado: bool, qtd_parcelas: int):
    """Gerencia lançamentos comuns e desmembra compras parceladas no histórico automaticamente"""
    with Session(engine) as session:
        conta = session.exec(select(Conta).where(Conta.banco == banco_nome)).first()
        categoria = session.exec(select(Categoria).where(Categoria.categoria == categoria_nome)).first()
        
        if not conta: raise ValueError("Banco inválido.")
        if not categoria: raise ValueError("Categoria inválida.")
        
        tipo_enum = Tipos.ENTRADA if tipo_str == "Entrada" else Tipos.SAIDA
        
        if e_parcelado and tipo_enum == Tipos.SAIDA:
            if qtd_parcelas < 1: raise ValueError("A quantidade de parcelas deve ser maior que zero.")
            
            valor_parcela = round(valor_total / qtd_parcelas, 2)
            # Corrige pequenas dízimas periódicas ajustando a diferença centesimal na última parcela
            ajuste_ultima_parcela = round(valor_total - (valor_parcela * qtd_parcelas), 2)
            
            from calendar import monthrange
            ano = data_base.year
            mes = data_base.month
            dia_original = data_base.day
            
            for i in range(1, qtd_parcelas + 1):
                # Calcula o avanço de meses para as parcelas futuras
                if i > 1:
                    mes += 1
                    if mes > 12:
                        mes = 1
                        ano += 1
                
                # Garante que o dia se ajusta caso o mês termine antes (ex: dia 31 em meses de 30 dias ou fevereiro)
                ultimo_dia_mes = monthrange(ano, mes)[1]
                dia_ajustado = min(dia_original, ultimo_dia_mes)
                data_parcela = date(ano, mes, dia_ajustado)
                
                # Aplica o resíduo centesimal estritamente na última parcela para o total bater 100% centavos
                valor_final_lancamento = valor_parcela + ajuste_ultima_parcela if i == qtd_parcelas else valor_parcela
                
                # Formata a descrição: "Descrição (parcela X de X)"
                desc_formatada = f"{descricao_base} (parcela {i} de {qtd_parcelas})"
                
                historico = Historico(
                    data=data_parcela,
                    descricao=desc_formatada,
                    tipo=tipo_enum,
                    valor=valor_final_lancamento,
                    categoria_id=categoria.id,
                    conta_id=conta.id
                )
                session.add(historico)
                
                # Apenas desconta o valor do saldo bancário na hora se a parcela vencer no mês corrente/passado
                # (Mantém a lógica de despesa futura segura até a reconciliação do mês específico)
                if data_parcela <= date.today():
                    conta.valor -= valor_final_lancamento
        else:
            # Lançamento comum (Sem parcelamento)
            if tipo_enum == Tipos.ENTRADA:
                conta.valor += valor_total
            else:
                conta.valor -= valor_total
                
            historico = Historico(
                data=data_base,
                descricao=descricao_base,
                tipo=tipo_enum,
                valor=valor_total,
                categoria_id=categoria.id,
                conta_id=conta.id
            )
            session.add(historico)
            
        session.commit()
    
def listar_contas():
    with Session(engine) as session:
        return session.exec(select(Conta)).all()

def listar_ativas():
    with Session(engine) as session:
        return session.exec(select(Conta).where(Conta.status == Status.ATIVO)).all()

def listar_categorias():
    with Session(engine) as session:
        return session.exec(select(Categoria)).all()

def desativar_conta(id_conta):
    with Session(engine) as session:
        conta = session.get(Conta, id_conta)
        if not conta:
            raise ValueError("Conta não encontrada.")
        if conta.valor > 0:
            raise ValueError('Essa conta ainda possui saldo, não é possível desativar.')
        conta.status = Status.INATIVO
        session.commit()

def transferir_saldo(id_conta_saida, id_conta_entrada, valor, descricao, categoria_id, data_movimentacao):
    with Session(engine) as session:
        conta_saida = session.get(Conta, id_conta_saida)
        conta_entrada = session.get(Conta, id_conta_entrada)
        
        if not conta_saida or not conta_entrada:
            raise ValueError("Uma ou ambas as contas informadas não existem.")
        if conta_saida.valor < valor:
            raise ValueError('Saldo insuficiente na conta de origem.')
            
        conta_saida.valor -= valor
        conta_entrada.valor += valor
        
        historico_saida = Historico(
            data=data_movimentacao, 
            descricao=f"{descricao} (Saída)", 
            tipo=Tipos.SAIDA, 
            valor=valor, 
            categoria_id=categoria_id, 
            conta_id=id_conta_saida
        )
        historico_entrada = Historico(
            data=data_movimentacao, 
            descricao=f"{descricao} (Entrada)", 
            tipo=Tipos.ENTRADA, 
            valor=valor, 
            categoria_id=categoria_id, 
            conta_id=id_conta_entrada
        )
        
        session.add_all([historico_saida, historico_entrada])
        session.commit()

def movimentar_dinheiro(historico: Historico):
    with Session(engine) as session:
        conta = session.get(Conta, historico.conta_id)
        if not conta:
            raise ValueError("Conta informada não existe.")
            
        if historico.tipo == Tipos.ENTRADA:
            conta.valor += historico.valor
        else:
            if conta.valor < historico.valor:
                raise ValueError("Saldo insuficiente para realizar essa saída.")
            conta.valor -= historico.valor

        session.add(historico)
        session.commit()
        session.refresh(historico)
        return historico

def total_contas():
    with Session(engine) as session:
        contas = session.exec(select(Conta)).all()
    return sum(conta.valor for conta in contas)

def buscar_historicos_entre_datas(data_inicio: date, data_fim: date):
    with Session(engine) as session:
        statement = (
            select(Historico)
            .where(Historico.data >= data_inicio, Historico.data <= data_fim)
            .options(joinedload(Historico.categoria), joinedload(Historico.conta))
        )
        return session.exec(statement).all()

def criar_grafico_por_conta():
    with Session(engine) as session:
        # Mantém o filtro para trazer apenas contas ativas e com dinheiro
        statement = select(Conta).where(Conta.status == Status.ATIVO, Conta.valor > 0)
        contas = session.exec(statement).all()
        
        if not contas:
            return False
            
        bancos = [i.banco for i in contas]
        total = [i.valor for i in contas]
        
        import matplotlib.pyplot as plt
        plt.style.use('ggplot')
        
        # Aumentado altura da figura para acomodar o texto inclinado sem cortar
        plt.figure(figsize=(8, 5)) 
        plt.bar(bancos, total, color='teal')
        
        # --- Rotaciona os nomes em 45 graus e alinha à direita ---
        plt.xticks(rotation=45, ha='right')
        
        plt.title('Saldos Atuais por Banco (Contas com Saldo)')
        plt.ylabel('Valor (R$)')
        plt.tight_layout() # Garante que os nomes inclinados não fiquem para fora da janela
        plt.show()
        return True

def atualizar_conta(id_conta: int, novo_banco: str, novo_valor: float, novo_status: str):
    with Session(engine) as session:
        conta = session.get(Conta, id_conta)
        if not conta:
            raise ValueError("Conta não encontrada.")
        conta.banco = novo_banco
        conta.valor = novo_valor
        conta.status = Status.ATIVO if novo_status.upper() == "ATIVO" else Status.INATIVO
        session.commit()

def atualizar_historico(id_historico: int, nova_descricao: str, novo_valor: float, nova_data: date, novo_banco_nome: str, nova_categoria_nome: str, novo_tipo_str: str):
    with Session(engine) as session:
        historico = session.get(Historico, id_historico)
        if not historico:
            raise ValueError("Registro de histórico não encontrado.")
        
        # 1. Busca as referências das novas entidades pelos nomes digitados
        nova_conta = session.exec(select(Conta).where(Conta.banco == novo_banco_nome)).first()
        nova_cat = session.exec(select(Categoria).where(Categoria.categoria == nova_categoria_nome)).first()
        
        if not nova_conta:
            raise ValueError(f"O banco '{novo_banco_nome}' não existe ou está incorreto.")
        if not nova_cat:
            raise ValueError(f"A categoria '{nova_categoria_nome}' não existe ou está incorreta.")
            
        if "ENTRADA" in novo_tipo_str.upper():
            novo_tipo = Tipos.ENTRADA
        else:
            novo_tipo = Tipos.SAIDA

        # 2. DESFAZ o efeito do saldo na conta antiga antes da edição
        conta_antiga = session.get(Conta, historico.conta_id)
        if conta_antiga:
            if historico.tipo == Tipos.ENTRADA:
                conta_antiga.valor -= historico.valor
            else:
                conta_antiga.valor += historico.valor

        # 3. APLICA o efeito do novo valor e tipo na conta nova (ou na mesma, se não mudou)
        if novo_tipo == Tipos.ENTRADA:
            nova_conta.valor += novo_valor
        else:
            nova_conta.valor -= novo_valor

        # 4. Atualiza os dados do histórico
        historico.descricao = nova_descricao
        historico.valor = novo_valor
        historico.data = nova_data
        historico.conta_id = nova_conta.id
        historico.categoria_id = nova_cat.id
        historico.tipo = novo_tipo
        
        session.commit()

def buscar_historicos_avancado(data_inicio: date, data_fim: date, banco_nome: str = "Todos"):
    with Session(engine) as session:
        statement = (
            select(Historico)
            .join(Conta)
            .where(Historico.data >= data_inicio, Historico.data <= data_fim)
            # --- Ordena da data mais antiga primeiro para a mais nova por último ---
            .order_by(Historico.data.asc())
            .options(joinedload(Historico.categoria), joinedload(Historico.conta))
        )
        if banco_nome != "Todos":
            statement = statement.where(Conta.banco == banco_nome)
            
        return session.exec(statement).all()

def reconciliar_saldos_em_lote():
    #Calcula os valores de movimentações da tabela do início até o dia atual (hoje). Valores futuros são guardados, mas desconsiderados do saldo imediato.
    with Session(engine) as session:
        contas = session.exec(select(Conta)).all()
        
        for conta in contas:
            historicos = session.exec(select(Historico).where(Historico.conta_id == conta.id)).all()
            
            if not historicos:
                continue
                
            saldo_calculado = 0.0
            for item in historicos:
                # --- TRAVA CRONOLÓGICA ---
                # Se a transação for de uma data maior que o dia de hoje, ignora no saldo atual
                if item.data > date.today():
                    continue
                    
                if item.tipo == Tipos.ENTRADA:
                    saldo_calculado += item.valor
                else:
                    saldo_calculado -= item.valor
            
            # Atualiza o valor contábil líquido consolidado até o presente momento
            conta.valor = saldo_calculado
            
        session.commit()

def movimentar_dinheiro_recorrente(banco_nome: str, categoria_nome: str, descricao_base: str, valor: float, tipo_str: str, data_base: date):
    """NOVO: Registra uma movimentação recorrente replicando-a por 12 meses consecutivos"""
    with Session(engine) as session:
        conta = session.exec(select(Conta).where(Conta.banco == banco_nome)).first()
        categoria = session.exec(select(Categoria).where(Categoria.categoria == categoria_nome)).first()
        
        if not conta: raise ValueError("Banco inválido.")
        if not categoria: raise ValueError("Categoria inválida.")
        
        tipo_enum = Tipos.ENTRADA if tipo_str == "Entrada" else Tipos.SAIDA
        
        ano = data_base.year
        mes = data_base.month
        dia_original = data_base.day
        
        for i in range(1, 13): # Executa exatamente 12 replicações
            if i > 1:
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
            
            ultimo_dia_mes = monthrange(ano, mes)[1]
            dia_ajustado = min(dia_original, ultimo_dia_mes)
            data_lancamento = date(ano, mes, dia_ajustado)
            
            # Modifica a descrição para manter rastreabilidade
            desc_formatada = f"{descricao_base} (Recorrente {i}/12)"
            
            historico = Historico(
                data=data_lancamento,
                descricao=desc_formatada,
                tipo=tipo_enum,
                valor=valor,
                categoria_id=categoria.id,
                conta_id=conta.id
            )
            session.add(historico)
            
            # Aplica o impacto financeiro no saldo de forma contínua
            if tipo_enum == Tipos.ENTRADA:
                conta.valor += valor
            else:
                conta.valor -= valor
                
        session.commit()

def deletar_conta(id_conta: int):
    """Exclui um banco apenas se não houver nenhuma movimentação vinculada a ele"""
    with Session(engine) as session:
        # Verifica se existem históricos vinculados
        vinculos = session.exec(select(Historico).where(Historico.conta_id == id_conta)).first()
        if vinculos:
            raise ValueError("Não é possível excluir este banco pois ele possui movimentações registradas.")
        
        conta = session.get(Conta, id_conta)
        if not conta:
            raise ValueError("Banco não encontrado.")
            
        session.delete(conta)
        session.commit()

def deletar_categoria(id_categoria: int):
    """Exclui uma categoria apenas se não houver nenhuma movimentação usando seu ID"""
    with Session(engine) as session:
        vinculos = session.exec(select(Historico).where(Historico.categoria_id == id_categoria)).first()
        if vinculos:
            raise ValueError("Não é possível excluir esta categoria pois ela está sendo usada no histórico.")
            
        categoria = session.get(Categoria, id_categoria)
        if not categoria:
            raise ValueError("Categoria não encontrada.")
            
        session.delete(categoria)
        session.commit()

def criar_categoria_rapida(nome_categoria: str):
    """Cadastra uma nova categoria no banco de dados"""
    with Session(engine) as session:
        existe = session.exec(select(Categoria).where(Categoria.categoria == nome_categoria)).first()
        if existe:
            raise ValueError("Esta categoria já está cadastrada.")
            
        nova_cat = Categoria(categoria=nome_categoria)
        session.add(nova_cat)
        session.commit()

def deletar_movimentacao_sem_restricao(id_historico: int):
    """Exclui um lançamento do histórico sem restrições e devolve/retira o saldo da conta"""
    with Session(engine) as session:
        historico = session.get(Historico, id_historico)
        if not historico:
            raise ValueError("Lançamento não encontrado no histórico.")
            
        # Ajusta o saldo da conta vinculada antes de apagar a movimentação
        conta = session.get(Conta, historico.conta_id)
        if conta:
            if historico.tipo == Tipos.ENTRADA:
                conta.valor -= historico.valor
            else:
                conta.valor += historico.valor
                
        session.delete(historico)
        session.commit()