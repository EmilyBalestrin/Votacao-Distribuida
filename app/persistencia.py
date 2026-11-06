
import os
import sqlite3
import threading


class Persistencia:
    def __init__(self, caminho_banco):
        self.caminho_banco = caminho_banco
        self.lock = threading.Lock()

        pasta = os.path.dirname(caminho_banco)

        if pasta:
            os.makedirs(pasta, exist_ok=True)

        self.criar_tabelas()

    def conectar(self):
        return sqlite3.connect(self.caminho_banco)

    def criar_tabelas(self):
        with self.conectar() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS estado_eleicao (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    mandato INTEGER NOT NULL
                )
            """)

            conexao.execute("""
                INSERT OR IGNORE INTO estado_eleicao
                (id, mandato)
                VALUES (1, 0)
            """)

    def obter_mandato(self):
        with self.lock:
            with self.conectar() as conexao:
                resultado = conexao.execute(
                    "SELECT mandato FROM estado_eleicao WHERE id = 1"
                ).fetchone()

                return resultado[0]

    def atualizar_mandato(self, novo_mandato):
        if type(novo_mandato) is not int or novo_mandato < 0:
            raise ValueError("Mandato invalido")

        with self.lock:
            with self.conectar() as conexao:
                conexao.execute("""
                    UPDATE estado_eleicao
                    SET mandato = ?
                    WHERE id = 1 AND mandato < ?
                """, (novo_mandato, novo_mandato))

                resultado = conexao.execute(
                    "SELECT mandato FROM estado_eleicao WHERE id = 1"
                ).fetchone()

                return resultado[0]
