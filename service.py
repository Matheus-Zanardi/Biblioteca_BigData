"""Regras de negócio da biblioteca."""
import re
from datetime import datetime, timedelta

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

PRAZO_DIAS = 7
LIMITE_EMPRESTIMOS = 3
MULTA_POR_DIA = 2.00


# ---------- exceções ----------
class BibliotecaErro(Exception):
    """Base de todos os erros de negócio."""


class LivroIndisponivel(BibliotecaErro): pass
class LimiteEmprestimos(BibliotecaErro): pass
class AlunoComAtraso(BibliotecaErro): pass
class EmprestimoJaDevolvido(BibliotecaErro): pass
class EmprestimoNaoEncontrado(BibliotecaErro): pass
class LivroNaoEncontrado(BibliotecaErro): pass
class AlunoNaoEncontrado(BibliotecaErro): pass
class IsbnDuplicado(BibliotecaErro): pass
class MatriculaDuplicada(BibliotecaErro): pass
class LivroComEmprestimoAberto(BibliotecaErro): pass
class DadoInvalido(BibliotecaErro): pass


def _dia(data=None):
    """Data de hoje (ou a informada) sempre à meia-noite."""
    data = data or datetime.now()
    return datetime(data.year, data.month, data.day)


class Biblioteca:
    def __init__(self, db):
        self.db = db

    # ---------- R1: livros ----------
    def cadastrar_livro(self, isbn, titulo, autor, ano, categoria, exemplares_total):
        if not isbn or not titulo:
            raise DadoInvalido("ISBN e título são obrigatórios.")
        if exemplares_total < 1:
            raise DadoInvalido("exemplares_total deve ser >= 1.")
        livro = {
            "isbn": isbn, "titulo": titulo, "autor": autor, "ano": ano,
            "categoria": categoria, "exemplares_total": exemplares_total,
            "exemplares_disponiveis": exemplares_total,
        }
        try:
            self.db.livros.insert_one(livro)
        except DuplicateKeyError:
            raise IsbnDuplicado(f"ISBN {isbn} já cadastrado.")
        return livro

    def buscar_livro(self, isbn):
        livro = self.db.livros.find_one({"isbn": isbn})
        if not livro:
            raise LivroNaoEncontrado(f"ISBN {isbn} não encontrado.")
        return livro

    def listar_livros(self):
        return list(self.db.livros.find().sort("titulo", 1))

    def atualizar_livro(self, isbn, **campos):
        permitidos = {"titulo", "autor", "ano", "categoria", "exemplares_total"}
        invalidos = set(campos) - permitidos
        if invalidos:
            raise DadoInvalido(f"Campos não editáveis: {', '.join(sorted(invalidos))}")
        livro = self.buscar_livro(isbn)
        update = {}
        if "exemplares_total" in campos:
            delta = campos["exemplares_total"] - livro["exemplares_total"]
            if livro["exemplares_disponiveis"] + delta < 0:
                raise DadoInvalido("Total menor que o número de exemplares emprestados.")
            update["$inc"] = {"exemplares_disponiveis": delta}
        update["$set"] = campos
        self.db.livros.update_one({"isbn": isbn}, update)
        return self.buscar_livro(isbn)

    def remover_livro(self, isbn):
        self.buscar_livro(isbn)
        if self.db.emprestimos.count_documents({"isbn": isbn, "data_devolucao": None}):
            raise LivroComEmprestimoAberto("Livro tem empréstimo em aberto.")
        self.db.livros.delete_one({"isbn": isbn})

    # ---------- R2: alunos ----------
    def cadastrar_aluno(self, matricula, nome, curso, email):
        if not matricula or not nome:
            raise DadoInvalido("Matrícula e nome são obrigatórios.")
        if "@" not in (email or ""):
            raise DadoInvalido("E-mail inválido.")
        aluno = {"matricula": matricula, "nome": nome, "curso": curso, "email": email}
        try:
            self.db.alunos.insert_one(aluno)
        except DuplicateKeyError:
            raise MatriculaDuplicada(f"Matrícula {matricula} já cadastrada.")
        return aluno

    def buscar_aluno(self, matricula):
        aluno = self.db.alunos.find_one({"matricula": matricula})
        if not aluno:
            raise AlunoNaoEncontrado(f"Matrícula {matricula} não encontrada.")
        return aluno

    # ---------- R3: busca ----------
    def buscar_livros(self, termo=None, categoria=None):
        filtro = {}
        if termo:
            rx = {"$regex": re.escape(termo), "$options": "i"}
            filtro["$or"] = [{"titulo": rx}, {"autor": rx}]
        if categoria:
            filtro["categoria"] = {"$regex": f"^{re.escape(categoria)}$", "$options": "i"}
        return list(self.db.livros.find(filtro).sort("titulo", 1))

    # ---------- R4: emprestar ----------
    def emprestar(self, isbn, matricula, hoje=None):
        hoje = _dia(hoje)
        self.buscar_aluno(matricula)
        self.buscar_livro(isbn)

        if self.db.emprestimos.count_documents(
            {"matricula": matricula, "data_devolucao": None, "data_prevista": {"$lt": hoje}}
        ):
            raise AlunoComAtraso("Aluno tem empréstimo atrasado.")
        if self.db.emprestimos.count_documents(
            {"matricula": matricula, "data_devolucao": None}
        ) >= LIMITE_EMPRESTIMOS:
            raise LimiteEmprestimos(f"Limite de {LIMITE_EMPRESTIMOS} empréstimos em aberto.")

        # Atômico: só baixa o estoque se ainda houver exemplar.
        res = self.db.livros.update_one(
            {"isbn": isbn, "exemplares_disponiveis": {"$gt": 0}},
            {"$inc": {"exemplares_disponiveis": -1}},
        )
        if res.modified_count == 0:
            raise LivroIndisponivel("Não há exemplares disponíveis.")

        emp = {
            "isbn": isbn, "matricula": matricula, "data_emprestimo": hoje,
            "data_prevista": hoje + timedelta(days=PRAZO_DIAS),
            "data_devolucao": None, "multa": 0.0,
        }
        self.db.emprestimos.insert_one(emp)
        return emp

    # ---------- R5: devolver ----------
    def devolver(self, emprestimo_id, hoje=None):
        hoje = _dia(hoje)
        if isinstance(emprestimo_id, str):
            try:
                emprestimo_id = ObjectId(emprestimo_id)
            except Exception:
                raise EmprestimoNaoEncontrado("ID inválido.")
        emp = self.db.emprestimos.find_one({"_id": emprestimo_id})
        if not emp:
            raise EmprestimoNaoEncontrado("Empréstimo não encontrado.")
        if emp["data_devolucao"] is not None:
            raise EmprestimoJaDevolvido("Empréstimo já devolvido.")

        dias_atraso = max(0, (hoje - emp["data_prevista"]).days)
        multa = dias_atraso * MULTA_POR_DIA

        # Filtro com data_devolucao nula evita devolução dupla simultânea.
        res = self.db.emprestimos.update_one(
            {"_id": emprestimo_id, "data_devolucao": None},
            {"$set": {"data_devolucao": hoje, "multa": multa}},
        )
        if res.modified_count == 0:
            raise EmprestimoJaDevolvido("Empréstimo já devolvido.")
        self.db.livros.update_one({"isbn": emp["isbn"]}, {"$inc": {"exemplares_disponiveis": 1}})
        return {"dias_atraso": dias_atraso, "multa": multa}

    def listar_emprestimos_abertos(self, matricula=None):
        filtro = {"data_devolucao": None}
        if matricula:
            filtro["matricula"] = matricula
        return list(self.db.emprestimos.find(filtro))

    # ---------- R6: relatórios ----------
    def relatorio_mais_emprestados(self, limite=5):
        return list(self.db.emprestimos.aggregate([
            {"$group": {"_id": "$isbn", "total": {"$sum": 1}}},
            {"$sort": {"total": -1, "_id": 1}},
            {"$limit": limite},
            {"$lookup": {"from": "livros", "localField": "_id", "foreignField": "isbn", "as": "livro"}},
            {"$unwind": "$livro"},
            {"$project": {"_id": 0, "isbn": "$_id", "titulo": "$livro.titulo", "total": 1}},
        ]))

    def relatorio_por_curso(self):
        return list(self.db.emprestimos.aggregate([
            {"$lookup": {"from": "alunos", "localField": "matricula", "foreignField": "matricula", "as": "aluno"}},
            {"$unwind": "$aluno"},
            {"$group": {"_id": "$aluno.curso", "total": {"$sum": 1}}},
            {"$sort": {"total": -1, "_id": 1}},
            {"$project": {"_id": 0, "curso": "$_id", "total": 1}},
        ]))

    def relatorio_atrasados(self, hoje=None):
        hoje = _dia(hoje)
        return list(self.db.emprestimos.aggregate([
            {"$match": {"data_devolucao": None, "data_prevista": {"$lt": hoje}}},
            {"$lookup": {"from": "alunos", "localField": "matricula", "foreignField": "matricula", "as": "aluno"}},
            {"$lookup": {"from": "livros", "localField": "isbn", "foreignField": "isbn", "as": "livro"}},
            {"$unwind": "$aluno"},
            {"$unwind": "$livro"},
            {"$project": {
                "_id": 0, "nome": "$aluno.nome", "livro": "$livro.titulo",
                "dias_atraso": {"$floor": {"$divide": [{"$subtract": [hoje, "$data_prevista"]}, 86400000]}},
            }},
            {"$sort": {"dias_atraso": -1, "nome": 1}},
        ]))

    def relatorio_total_multas(self):
        res = list(self.db.emprestimos.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$multa"}}},
        ]))
        return float(res[0]["total"]) if res else 0.0
