from datetime import datetime, timedelta

import pytest

from service import *

D0 = datetime(2026, 10, 1)


# R1
def test_r1_isbn_unico(bib):
    with pytest.raises(IsbnDuplicado):
        bib.cadastrar_livro("111", "Outro", "X", 2000, "Y", 1)


def test_r1_crud(bib):
    assert bib.buscar_livro("111")["titulo"] == "Python Fluente"
    assert len(bib.listar_livros()) == 4
    bib.atualizar_livro("111", titulo="Python Fluente 2ed", exemplares_total=3)
    l = bib.buscar_livro("111")
    assert l["titulo"] == "Python Fluente 2ed" and l["exemplares_disponiveis"] == 3
    bib.remover_livro("111")
    with pytest.raises(LivroNaoEncontrado):
        bib.buscar_livro("111")


def test_r1_nao_remove_com_emprestimo_aberto(bib):
    bib.emprestar("111", "A1", D0)
    with pytest.raises(LivroComEmprestimoAberto):
        bib.remover_livro("111")


# R2
def test_r2_aluno(bib):
    assert bib.buscar_aluno("A1")["nome"] == "Ana"
    with pytest.raises(MatriculaDuplicada):
        bib.cadastrar_aluno("A1", "Outra", "ADS", "o@x.com")
    with pytest.raises(DadoInvalido):
        bib.cadastrar_aluno("C3", "Carlos", "ADS", "email-invalido")


# R3
def test_r3_busca(bib):
    assert [l["isbn"] for l in bib.buscar_livros("PYTHON")] == ["111"]
    assert [l["isbn"] for l in bib.buscar_livros("machado")] == ["222"]
    titulos = [l["titulo"] for l in bib.buscar_livros(categoria="programação")]
    assert titulos == sorted(titulos) and len(titulos) == 3


# R4
def test_r4_emprestar(bib):
    emp = bib.emprestar("111", "A1", D0)
    assert emp["data_prevista"] == D0 + timedelta(days=7)
    assert bib.buscar_livro("111")["exemplares_disponiveis"] == 1


def test_r4_sem_exemplar(bib):
    bib.emprestar("222", "A1", D0)
    with pytest.raises(LivroIndisponivel):
        bib.emprestar("222", "B2", D0)
    assert bib.buscar_livro("222")["exemplares_disponiveis"] == 0


def test_r4_limite_3(bib):
    for isbn in ("111", "222", "333"):
        bib.emprestar(isbn, "A1", D0)
    with pytest.raises(LimiteEmprestimos):
        bib.emprestar("444", "A1", D0)


def test_r4_aluno_com_atraso(bib):
    bib.emprestar("111", "A1", D0)
    with pytest.raises(AlunoComAtraso):
        bib.emprestar("444", "A1", D0 + timedelta(days=8))


# R5
def test_r5_devolucao_no_prazo(bib):
    emp = bib.emprestar("111", "A1", D0)
    r = bib.devolver(emp["_id"], D0 + timedelta(days=7))
    assert r["multa"] == 0
    assert bib.buscar_livro("111")["exemplares_disponiveis"] == 2


def test_r5_multa_por_atraso(bib):
    emp = bib.emprestar("111", "A1", D0)
    r = bib.devolver(emp["_id"], D0 + timedelta(days=10))  # 3 dias de atraso
    assert r["dias_atraso"] == 3 and r["multa"] == 6.0


def test_r5_devolver_duas_vezes(bib):
    emp = bib.emprestar("111", "A1", D0)
    bib.devolver(emp["_id"], D0 + timedelta(days=1))
    with pytest.raises(EmprestimoJaDevolvido):
        bib.devolver(emp["_id"], D0 + timedelta(days=2))
    assert bib.buscar_livro("111")["exemplares_disponiveis"] == 2


# R6
def test_r6_relatorios(bib):
    e1 = bib.emprestar("111", "A1", D0)
    bib.devolver(e1["_id"], D0 + timedelta(days=9))      # multa 4.00
    bib.emprestar("111", "B2", D0)
    bib.emprestar("333", "A1", D0 + timedelta(days=9))

    top = bib.relatorio_mais_emprestados()
    assert top[0]["isbn"] == "111" and top[0]["total"] == 2

    cursos = {c["curso"]: c["total"] for c in bib.relatorio_por_curso()}
    assert cursos == {"ADS": 2, "Engenharia": 1}

    atrasados = bib.relatorio_atrasados(D0 + timedelta(days=10))
    assert atrasados == [{"nome": "Bruno", "livro": "Python Fluente", "dias_atraso": 3}]

    assert bib.relatorio_total_multas() == 4.0
