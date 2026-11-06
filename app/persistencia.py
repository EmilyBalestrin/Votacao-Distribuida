
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
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS votos
                (eleitor TEXT PRIMARY KEY,
                 opcao TEXT NOT NULL,
                 CHECK (opcao IN ('python', 'java', 'javascript'))
                    )
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
    
    def salvar_voto(self, eleitor, opcao):
        if not isinstance(eleitor, str) or not eleitor.strip():
            return False, "Identificador do eleitor invalido"

        if not isinstance(opcao, str) or opcao not in (
            "python", "java", "javascript"
        ):
            return False, "Opcao de voto invalida"

        eleitor = eleitor.strip()

        with self.lock:
            try:
                with self.conectar() as conexao:
                    conexao.execute(
                        "INSERT INTO votos (eleitor, opcao) VALUES (?, ?)",
                        (eleitor, opcao)
                    )

                return True, "Voto armazenado com sucesso"

            except sqlite3.IntegrityError:
                return False, "Este eleitor ja registrou um voto"

    def consultar_votos(self):
        with self.lock:
            with self.conectar() as conexao:
                registros = conexao.execute(
                    "SELECT opcao, COUNT(*) FROM votos GROUP BY opcao"
                ).fetchall()

        resultados = {
            "python": 0,
            "java": 0,
            "javascript": 0
        }

        for opcao, quantidade in registros:
            resultados[opcao] = quantidade

        return {
            "total_votos": sum(resultados.values()),
            "resultados": resultados
        }
