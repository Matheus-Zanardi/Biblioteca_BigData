import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mongomock
import pytest

from db import criar_indices
from service import Biblioteca


@pytest.fixture
def bib():
    db = mongomock.MongoClient()["teste"]
    criar_indices(db)
    b = Biblioteca(db)
    b.cadastrar_livro("111", "Python Fluente", "Luciano Ramalho", 2015, "Programação", 2)
    b.cadastrar_livro("222", "Dom Casmurro", "Machado de Assis", 1899, "Romance", 1)
    b.cadastrar_livro("333", "Código Limpo", "Robert Martin", 2008, "Programação", 1)
    b.cadastrar_livro("444", "Banco de Dados", "Silberschatz", 2010, "Programação", 5)
    b.cadastrar_aluno("A1", "Ana", "ADS", "ana@fiap.com")
    b.cadastrar_aluno("B2", "Bruno", "Engenharia", "bruno@fiap.com")
    return b
