"""Conexão com o MongoDB e criação dos índices."""
import os

from pymongo import ASCENDING, MongoClient

URI_PADRAO = "mongodb://localhost:27017"
NOME_BANCO = "biblioteca"


def get_db(uri=None, nome=NOME_BANCO):
    uri = uri or os.getenv("MONGO_URI", URI_PADRAO)
    return MongoClient(uri)[nome]


def criar_indices(db):
    db.livros.create_index([("isbn", ASCENDING)], unique=True)
    db.alunos.create_index([("matricula", ASCENDING)], unique=True)
    db.emprestimos.create_index([("matricula", ASCENDING), ("data_devolucao", ASCENDING)])
    db.emprestimos.create_index([("isbn", ASCENDING), ("data_devolucao", ASCENDING)])
