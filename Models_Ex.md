# Arquitetura da camada Models

Este documento explica as responsabilidades das pastas `entities`, `repositories`, `settings` e `migrations` dentro da camada `models`.

## Estrutura do projeto

```text
src/
├── controllers/
├── routes/
├── services/
└── models/
    └── sqlite/
        ├── entities/
        ├── repositories/
        └── settings/

migrations/
```

## Visão geral

| Camada | Responsabilidade | Pergunta que responde |
|---|---|---|
| `entities` | Representar tabelas e relacionamentos | Como os dados são estruturados? |
| `repositories` | Consultar e modificar registros | Como acesso e altero os dados? |
| `settings` | Configurar conexão, engine e sessões | Como me conecto ao banco? |
| `migrations` | Versionar mudanças nas tabelas | Como altero a estrutura do banco? |
| `services` | Aplicar regras de negócio | Essa operação pode acontecer? |
| `controllers` | Organizar entrada e saída | Como processo a requisição? |
| `routes` | Definir os endpoints HTTP | Qual URL chama cada controller? |

## Fluxo da aplicação

```text
Requisição HTTP
       │
       ▼
     Route
       │
       ▼
   Controller
       │
       ▼
    Service
       │
       ▼
  Repository
       │
       ├── usa as Entities
       └── usa a Session
                │
                ▼
             Banco SQL
```

Uma forma simples de memorizar:

```text
Route       = define o endereço
Controller  = recebe e responde
Service     = decide o que pode acontecer
Repository  = executa ações nos registros
Entity      = define o formato dos dados
Settings    = configura o acesso ao banco
Migration   = modifica a estrutura do banco
```

# 1. Entities

As entidades representam as tabelas do banco no código Python.

Elas definem:

- Nome da tabela;
- Colunas;
- Tipos dos dados;
- Chaves primárias;
- Chaves estrangeiras;
- Relacionamentos;
- Restrições.

## Exemplo de entidade

```python
from sqlalchemy import BIGINT, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from src.models.sqlite.settings.base import Base


class PetsTable(Base):
    __tablename__ = "pets"

    id = Column(BIGINT, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)

    owner_id = Column(
        BIGINT,
        ForeignKey("people.id"),
        nullable=False,
    )

    owner = relationship(
        "PeopleTable",
        back_populates="pets",
    )

    def __repr__(self):
        return (
            f"PetsTable(id={self.id}, "
            f"name={self.name}, type={self.type})"
        )
```

## Principais elementos

| Elemento | Exemplo | Significado |
|---|---|---|
| Classe | `PetsTable` | Representa uma tabela |
| `__tablename__` | `"pets"` | Nome da tabela no banco |
| `Column` | `Column(String)` | Define uma coluna |
| `primary_key` | `primary_key=True` | Identifica cada registro |
| `nullable` | `nullable=False` | Torna o campo obrigatório |
| `ForeignKey` | `ForeignKey("people.id")` | Referencia outra tabela |
| `relationship` | `relationship("PeopleTable")` | Relaciona objetos Python |

## ForeignKey e relationship

A `ForeignKey` cria uma relação no banco:

```python
owner_id = Column(
    BIGINT,
    ForeignKey("people.id"),
)
```

Isso informa que `owner_id` referencia o campo `id` da tabela `people`.

O `relationship` cria uma relação entre objetos Python:

```python
owner = relationship(
    "PeopleTable",
    back_populates="pets",
)
```

Assim, é possível acessar:

```python
pet.owner
```

Resumo:

```text
ForeignKey   = relacionamento no banco
relationship = relacionamento entre objetos Python
```

## O que não deve ficar na Entity?

A Entity não deve:

- Receber requisições HTTP;
- Criar conexões;
- Abrir sessões;
- Executar `commit`;
- Conter consultas complexas;
- Decidir regras de negócio da aplicação.

A Entity representa o formato do dado.

# 2. Repositories

Os repositories são responsáveis pelo acesso aos registros do banco.

Eles normalmente executam o CRUD:

| Letra | Operação | SQL |
|---|---|---|
| C | Create | `INSERT` |
| R | Read | `SELECT` |
| U | Update | `UPDATE` |
| D | Delete | `DELETE` |

## Operações comuns

| Operação | Método possível | SQLAlchemy |
|---|---|---|
| Criar | `create()` | `session.add()` |
| Buscar todos | `find_all()` | `select()` |
| Buscar por ID | `find_by_id()` | `session.get()` |
| Atualizar | `update()` | Alterar atributos |
| Excluir | `delete()` | `session.delete()` |
| Confirmar | — | `session.commit()` |
| Desfazer | — | `session.rollback()` |

## Exemplo de repository

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.sqlite.entities.pets import PetsTable


class PetsRepository:
    def __init__(self, session: Session):
        self.__session = session

    def create(
        self,
        name: str,
        pet_type: str,
        owner_id: int,
    ) -> PetsTable:
        pet = PetsTable(
            name=name,
            type=pet_type,
            owner_id=owner_id,
        )

        try:
            self.__session.add(pet)
            self.__session.commit()
            self.__session.refresh(pet)

            return pet
        except Exception:
            self.__session.rollback()
            raise

    def find_by_id(
        self,
        pet_id: int,
    ) -> PetsTable | None:
        return self.__session.get(PetsTable, pet_id)

    def find_all(self) -> list[PetsTable]:
        statement = select(PetsTable)
        result = self.__session.execute(statement)

        return list(result.scalars().all())

    def update_name(
        self,
        pet_id: int,
        name: str,
    ) -> PetsTable | None:
        pet = self.find_by_id(pet_id)

        if pet is None:
            return None

        try:
            pet.name = name

            self.__session.commit()
            self.__session.refresh(pet)

            return pet
        except Exception:
            self.__session.rollback()
            raise

    def delete(self, pet_id: int) -> bool:
        pet = self.find_by_id(pet_id)

        if pet is None:
            return False

        try:
            self.__session.delete(pet)
            self.__session.commit()

            return True
        except Exception:
            self.__session.rollback()
            raise
```

## O que deve ficar no Repository?

Exemplos:

```python
session.add(pet)
session.get(PetsTable, pet_id)
session.execute(statement)
session.delete(pet)
session.commit()
session.rollback()
```

## O que não deve ficar no Repository?

O Repository não deve decidir regras como:

```python
if person.age < 18:
    raise ValueError("A pessoa não pode adotar")
```

Essa é uma regra de negócio e deve ficar no Service.

O Repository sabe **como salvar**.  
O Service decide **se pode salvar**.

# 3. Settings

A pasta `settings` configura o acesso ao banco.

Ela normalmente contém:

```text
settings/
├── __init__.py
├── base.py
└── connection.py
```

## `base.py`

A `Base` registra as entidades utilizadas pelo SQLAlchemy:

```python
from sqlalchemy.orm import declarative_base


Base = declarative_base()
```

Todas as entidades devem herdar da mesma `Base`:

```python
class PetsTable(Base):
    pass
```

Com isso, o SQLAlchemy reúne os metadados das tabelas:

```python
Base.metadata
```

## `connection.py`

Esse arquivo configura:

- URL do banco;
- Engine;
- Fábrica de sessões;
- Abertura e fechamento das sessões.

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class DBConnectionHandler:
    def __init__(self) -> None:
        connection_string = os.getenv(
            "DATABASE_URL",
            "sqlite:///storage.db",
        )

        self.__engine = create_engine(connection_string)

        self.__session_factory = sessionmaker(
            bind=self.__engine,
            autoflush=False,
            autocommit=False,
        )

    def get_engine(self):
        return self.__engine

    def get_session(self):
        return self.__session_factory()


db_connection = DBConnectionHandler()
```

## Usando a conexão

```python
from src.models.sqlite.settings.connection import db_connection


session = db_connection.get_session()

try:
    # Utilizar repositories
    pass
finally:
    session.close()
```

O fechamento da sessão é importante para liberar os recursos da conexão.

## SQLite e MySQL

A estrutura pode continuar praticamente igual. A principal mudança está na URL e no driver.

SQLite:

```text
sqlite:///storage.db
```

MySQL:

```text
mysql+pymysql://usuario:senha@mysql:3306/nome_do_banco
```

A URL pode ser configurada por variável de ambiente:

```env
DATABASE_URL=mysql+pymysql://usuario:senha@mysql:3306/pets
```

# 4. Migrations

Migrations representam o histórico de mudanças na estrutura do banco.

Elas podem:

- Criar tabelas;
- Remover tabelas;
- Adicionar colunas;
- Remover colunas;
- Alterar tipos;
- Criar índices;
- Criar chaves estrangeiras;
- Desfazer alterações.

## Migration não é Repository

| Repository | Migration |
|---|---|
| Altera registros | Altera tabelas |
| Executa `INSERT` | Executa `CREATE TABLE` |
| Executa `UPDATE` | Executa `ALTER TABLE` |
| Executa `DELETE` | Pode executar `DROP TABLE` |
| É usado durante a aplicação | É usado na evolução do banco |

Exemplo:

```text
Repository:
“Cadastre o pet Rex.”

Migration:
“Adicione a coluna owner_id na tabela pets.”
```

## Onde fica?

Geralmente, as migrations ficam na raiz do projeto:

```text
api_mvc/
├── migrations/
├── src/
├── alembic.ini
└── requirements.txt
```

A ferramenta mais comum com SQLAlchemy é o Alembic.

Instalação:

```bash
pip install alembic
```

Inicialização:

```bash
alembic init migrations
```

Criar uma migration:

```bash
alembic revision --autogenerate -m "create pets table"
```

Aplicar as migrations:

```bash
alembic upgrade head
```

Desfazer a última migration:

```bash
alembic downgrade -1
```

## `create_all` ou migrations?

Durante os primeiros estudos, é possível criar tabelas assim:

```python
Base.metadata.create_all(engine)
```

Porém, `create_all()` não mantém um histórico completo das mudanças e não atualiza toda estrutura existente automaticamente.

Em projetos reais, migrations são mais adequadas:

```text
Estudo simples    → Base.metadata.create_all()
Projeto evoluindo → Alembic migrations
```

# 5. Services

Services contêm as regras de negócio da aplicação.

## Exemplo

```python
class CreatePetService:
    def __init__(self, pets_repository):
        self.__pets_repository = pets_repository

    def execute(
        self,
        name: str,
        pet_type: str,
        owner_id: int,
    ):
        if not name.strip():
            raise ValueError("O nome é obrigatório")

        if pet_type not in {"dog", "cat"}:
            raise ValueError("Tipo de pet inválido")

        return self.__pets_repository.create(
            name=name,
            pet_type=pet_type,
            owner_id=owner_id,
        )
```

Nesse exemplo:

- O Service valida os dados;
- O Repository salva os dados;
- A Entity representa o pet;
- Settings fornece a sessão.

# Tabela de responsabilidades

| Código ou responsabilidade | Camada |
|---|---|
| `Column(String)` | Entity |
| `primary_key=True` | Entity |
| `ForeignKey("people.id")` | Entity |
| `relationship(...)` | Entity |
| `session.add()` | Repository |
| `session.get()` | Repository |
| `session.delete()` | Repository |
| `session.commit()` | Repository |
| `session.rollback()` | Repository |
| `create_engine()` | Settings |
| `sessionmaker()` | Settings |
| URL do banco | Settings/variável de ambiente |
| Regra de idade mínima | Service |
| Verificar se o pet já possui dono | Service |
| Receber uma requisição HTTP | Route/Controller |
| Formatar uma resposta HTTP | Controller |
| Criar ou alterar tabelas | Migration |

# Resumo para memorizar

| Camada | Frase curta |
|---|---|
| Entity | Define o dado |
| Repository | Manipula o dado |
| Settings | Conecta ao banco |
| Migration | Modifica as tabelas |
| Service | Aplica as regras |
| Controller | Coordena entrada e saída |
| Route | Define o endereço HTTP |

## Analogia da biblioteca

| Camada | Analogia |
|---|---|
| Entity | A ficha que descreve o livro |
| Repository | O funcionário que cadastra e procura livros |
| Settings | A chave e o endereço da biblioteca |
| Migration | A reforma que altera as estantes |
| Service | As regras para emprestar livros |
| Controller | O atendente que recebe o pedido |
| Route | O balcão correto para cada atendimento |

# Regra final

```text
ENTITY
Descreve como o dado é formado.

REPOSITORY
Executa ações nos registros.

SETTINGS
Fornece conexão e sessões.

MIGRATION
Versiona mudanças nas tabelas.

SERVICE
Aplica as regras de negócio.

CONTROLLER
Recebe os dados e prepara a resposta.

ROUTE
Liga uma URL ao controller.
```