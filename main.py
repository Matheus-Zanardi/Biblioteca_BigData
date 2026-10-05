"""Menu de terminal."""
from datetime import datetime

from db import criar_indices, get_db
from service import Biblioteca, BibliotecaErro

MENU = """
=== BIBLIOTECA ===
 1 Cadastrar livro        7 Buscar livros (título/autor/categoria)
 2 Buscar livro por ISBN  8 Emprestar livro
 3 Listar livros          9 Devolver livro
 4 Atualizar livro       10 Relatórios
 5 Remover livro         11 Empréstimos em aberto de um aluno
 6 Cadastrar aluno       12 Buscar aluno
 0 Sair
"""


def ler_data(msg):
    txt = input(f"{msg} (AAAA-MM-DD, vazio = hoje): ").strip()
    return datetime.strptime(txt, "%Y-%m-%d") if txt else None


def mostrar_livros(livros):
    for l in livros:
        print(f"{l['isbn']} | {l['titulo']} | {l['autor']} | {l['categoria']} | "
              f"{l['exemplares_disponiveis']}/{l['exemplares_total']}")
    if not livros:
        print("Nada encontrado.")


def relatorios(bib, hoje):
    print("\n-- Top 5 mais emprestados")
    for r in bib.relatorio_mais_emprestados():
        print(f"{r['titulo']}: {r['total']}")
    print("\n-- Empréstimos por curso")
    for r in bib.relatorio_por_curso():
        print(f"{r['curso']}: {r['total']}")
    print("\n-- Atrasados")
    for r in bib.relatorio_atrasados(hoje):
        print(f"{r['nome']} | {r['livro']} | {r['dias_atraso']} dia(s)")
    print(f"\n-- Total em multas: R$ {bib.relatorio_total_multas():.2f}")


def executar(bib, op):
    if op == "1":
        bib.cadastrar_livro(input("ISBN: "), input("Título: "), input("Autor: "),
                            int(input("Ano: ")), input("Categoria: "), int(input("Exemplares: ")))
        print("Livro cadastrado.")
    elif op == "2":
        mostrar_livros([bib.buscar_livro(input("ISBN: "))])
    elif op == "3":
        mostrar_livros(bib.listar_livros())
    elif op == "4":
        isbn = input("ISBN: ")
        campo = input("Campo (titulo/autor/ano/categoria/exemplares_total): ")
        valor = input("Novo valor: ")
        if campo in ("ano", "exemplares_total"):
            valor = int(valor)
        bib.atualizar_livro(isbn, **{campo: valor})
        print("Livro atualizado.")
    elif op == "5":
        bib.remover_livro(input("ISBN: "))
        print("Livro removido.")
    elif op == "6":
        bib.cadastrar_aluno(input("Matrícula: "), input("Nome: "), input("Curso: "), input("E-mail: "))
        print("Aluno cadastrado.")
    elif op == "7":
        mostrar_livros(bib.buscar_livros(input("Termo (vazio = todos): ") or None,
                                         input("Categoria (vazio = todas): ") or None))
    elif op == "8":
        emp = bib.emprestar(input("ISBN: "), input("Matrícula: "), ler_data("Data do empréstimo"))
        print(f"Emprestado. ID: {emp['_id']} | devolver até {emp['data_prevista']:%d/%m/%Y}")
    elif op == "9":
        r = bib.devolver(input("ID do empréstimo: "), ler_data("Data da devolução"))
        print(f"Devolvido. Atraso: {r['dias_atraso']} dia(s) | Multa: R$ {r['multa']:.2f}")
    elif op == "10":
        relatorios(bib, ler_data("Data de referência"))
    elif op == "11":
        for e in bib.listar_emprestimos_abertos(input("Matrícula: ")):
            print(f"{e['_id']} | {e['isbn']} | prevista {e['data_prevista']:%d/%m/%Y}")
    elif op == "12":
        a = bib.buscar_aluno(input("Matrícula: "))
        print(f"{a['matricula']} | {a['nome']} | {a['curso']} | {a['email']}")
    else:
        print("Opção inválida.")


def main():
    db = get_db()
    criar_indices(db)
    bib = Biblioteca(db)
    while True:
        print(MENU)
        op = input("Opção: ").strip()
        if op == "0":
            break
        try:
            executar(bib, op)
        except BibliotecaErro as e:
            print(f"Erro: {e}")
        except ValueError:
            print("Erro: valor inválido.")


if __name__ == "__main__":
    main()
