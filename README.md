# Sistema de Empréstimo de Livros

## Integrantes do Grupo
- Augusto Fisco Milreu - RM98245
- David Denunci - RM98603
- Fernando Popolili - RM99919
- Matheus Zanardi - RM98832
- Pedro Gava - RM551043


Backend em Python + MongoDB para a biblioteca da faculdade.

## Como rodar

```bash
docker compose up -d            # sobe o MongoDB
pip install -r requirements.txt
python main.py                  # menu no terminal
pytest                          # testes (não precisam do Mongo)
```

Para usar o MongoDB Atlas, defina a variável de ambiente:
`MONGO_URI="mongodb+srv://usuario:senha@cluster.mongodb.net"`.

## Estrutura

| Arquivo | Papel |
|---|---|
| `db.py` | conexão e índices |
| `service.py` | regras de negócio e exceções |
| `main.py` | menu de terminal |
| `tests/` | pytest (1+ teste por requisito de R1 a R6) |

## Decisões da equipe

- **Índices únicos** em `livros.isbn` e `alunos.matricula`: o próprio banco impede duplicatas, e o `DuplicateKeyError` vira `IsbnDuplicado` / `MatriculaDuplicada`.
- **Estoque atômico:** `update_one({isbn, exemplares_disponiveis: {$gt: 0}}, {$inc: -1})`. Se nada for modificado, lança `LivroIndisponivel`. Dois empréstimos simultâneos nunca deixam o estoque negativo.
- **Devolução única:** o update filtra `data_devolucao: None`; devolver de novo lança `EmprestimoJaDevolvido`.
- **Data como parâmetro:** `emprestar`, `devolver` e `relatorio_atrasados` aceitam `hoje`, o que permite testar atrasos sem esperar. As datas são normalizadas para meia-noite (contagem em dias inteiros).
- **Ordem das validações no empréstimo:** atraso → limite de 3 → estoque. O estoque é a última checagem, para não baixá-lo se uma regra anterior falhar.
- **Atrasado** = sem `data_devolucao` e `data_prevista` anterior à data de referência.
- **Multa** = dias de atraso × R$ 2,00, gravada na devolução.
- **Testes com `mongomock`**: rodam sem banco real, ficam rápidos e servem para CI.
- **Limitação conhecida:** a checagem do limite de 3 empréstimos não é atômica. Dois empréstimos simultâneos do mesmo aluno poderiam passar do limite. Uma solução futura seria uma transação ou um contador no documento do aluno.
