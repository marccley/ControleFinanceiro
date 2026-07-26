from sqlmodel import SQLModel, Field, create_engine, Relationship
from enum import Enum
from datetime import date
from typing import Optional

class Status(Enum):
    ATIVO = 'Ativo'
    INATIVO = 'Inativo'

class Tipos(Enum):
    ENTRADA = 'Entrada'
    SAIDA = 'Saída'

class Conta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    valor: float
    banco: str
    status: Status = Field(default=Status.ATIVO)

class Categoria(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    categoria: str

class Historico(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    data: date
    descricao: str
    tipo: Tipos = Field(default=Tipos.ENTRADA)
    valor: float
    categoria_id: int = Field(foreign_key="categoria.id")
    categoria: Categoria = Relationship()
    conta_id: int = Field(foreign_key="conta.id")
    conta: Conta = Relationship()
    
    # Propriedade utilitária para exibir a data formatada no padrão brasileiro
    @property
    def data_formatada(self) -> str:
        return self.data.strftime('%d/%m/%Y') if self.data else ""

sqlite_file_name = 'database.db'
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)

if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)