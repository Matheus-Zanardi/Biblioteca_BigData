# Sistema de Empréstimo de Livros

## Integrantes do Grupo
- Augusto Fisco Milreu - RM98245
- David Denunci - RM98603
- Fernando Popolili - RM99919
- Matheus Zanardi - RM98832
- Pedro Gava - RM551043


Backend em Python + MongoDB para a biblioteca da faculdade.

## O que você precisa ter

- **Python 3.10+** (teste com `python --version`)
- **Docker Desktop instalado e aberto** (ou uma conta no MongoDB Atlas)

## Como rodar

Abra o terminal **dentro da pasta do projeto** (onde está o `main.py`).

**1. Instalar as dependências**
```bash
pip install -r requirements.txt
```

**2. Subir o MongoDB**
```bash
docker compose up -d
```
Na primeira vez, o Docker baixa a imagem e pode demorar. Para conferir, rode `docker ps`: deve aparecer `biblioteca-mongo`.

**3. Abrir o menu**
```bash
python main.py
```

**4. Parar o banco quando terminar**
```bash
docker compose down
```
Os dados ficam salvos em um volume do Docker e não se perdem ao parar. Para apagar tudo, use `docker compose down -v`.

### Usando o MongoDB Atlas (sem Docker)

Defina a variável de ambiente com a sua string de conexão antes de rodar:

```bash
# Windows (PowerShell)
$env:MONGO_URI="mongodb+srv://usuario:senha@cluster.mongodb.net"
# Mac/Linux
export MONGO_URI="mongodb+srv://usuario:senha@cluster.mongodb.net"

python main.py
```

## Primeiro uso (exemplo)

Cadastre antes de emprestar:

1. Opção `1`: cadastrar um livro (ex.: ISBN `111`, 2 exemplares).
2. Opção `6`: cadastrar um aluno (ex.: matrícula `A1`, e-mail com `@`).
3. Opção `8`: emprestar (ISBN `111`, matrícula `A1`). **Guarde o ID** que aparece.
4. Opção `9`: devolver, informando o ID.
5. Opção `10`: ver os relatórios.

**Testar atraso e multa:** nas opções 8, 9 e 10 dá para informar uma data (`AAAA-MM-DD`). Exemplo: empreste em `2026-10-01` e devolva em `2026-10-10`. O prazo vence em `2026-10-08`, então são 2 dias de atraso e multa de R$ 4,00.

## Menu

| Opção | Função |
|---|---|
| 1 | Cadastrar livro |
| 2 | Buscar livro por ISBN |
| 3 | Listar livros |
| 4 | Atualizar livro |
| 5 | Remover livro |
| 6 | Cadastrar aluno |
| 7 | Buscar livros por título/autor/categoria |
| 8 | Emprestar livro |
| 9 | Devolver livro |
| 10 | Relatórios |
| 11 | Empréstimos em aberto de um aluno |
| 12 | Buscar aluno |

## Regras de negócio

- Prazo de devolução: **7 dias**.
- Máximo de **3 empréstimos em aberto** por aluno.
- Aluno com empréstimo atrasado **não pode pegar outro livro**.
- Multa: **R$ 2,00 por dia** de atraso.
- Livro com empréstimo em aberto **não pode ser removido**.
- ISBN e matrícula são **únicos**.

## Testes

```bash
pytest
```
No Windows, se aparecer "pytest não é reconhecido", use `python -m pytest`.

Os testes **não precisam do MongoDB rodando**: usam `mongomock`. Há pelo menos um teste por requisito de R1 a R6.

## Estrutura

| Arquivo | Papel |
|---|---|
| `db.py` | conexão e índices |
| `service.py` | regras de negócio e exceções |
| `main.py` | menu de terminal |
| `tests/` | testes com pytest |
| `docker-compose.yml` | MongoDB via Docker |

## Decisões da equipe

- **Índices únicos** em `livros.isbn` e `alunos.matricula`: o próprio banco impede duplicatas, e o `DuplicateKeyError` vira `IsbnDuplicado` / `MatriculaDuplicada`.
- **Estoque atômico:** `update_one({isbn, exemplares_disponiveis: {$gt: 0}}, {$inc: -1})`. Se nada for modificado, lança `LivroIndisponivel`. Dois empréstimos simultâneos nunca deixam o estoque negativo.
- **Devolução única:** o update filtra `data_devolucao: None`; devolver de novo lança `EmprestimoJaDevolvido`.
- **Data como parâmetro:** `emprestar`, `devolver` e `relatorio_atrasados` aceitam `hoje`, o que permite testar atrasos sem esperar. As datas são normalizadas para meia-noite (contagem em dias inteiros).
- **Ordem das validações no empréstimo:** atraso → limite de 3 → estoque. O estoque é a última checagem, para não baixá-lo se uma regra anterior falhar.
- **Atrasado** = sem `data_devolucao` e `data_prevista` anterior à data de referência.
- **Multa** = dias de atraso × R$ 2,00, gravada na devolução.
- **Testes com `mongomock`:** rodam sem banco real, ficam rápidos e servem para CI.
- **Limitação conhecida:** a checagem do limite de 3 empréstimos não é atômica. Dois empréstimos simultâneos do mesmo aluno poderiam passar do limite. Uma solução futura seria uma transação ou um contador no documento do aluno.
