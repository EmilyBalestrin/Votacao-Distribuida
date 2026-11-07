
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

            conexao.execute("""
                            CREATE TABLE IF NOT EXISTS operacoes
                            (id_operacao TEXT PRIMARY KEY,
                            eleitor TEXT NOT NULL,
                            opcao TEXT NOT NULL,
                            mandato INTEGER NOT NULL,
                            sequencia INTEGER NOT NULL,
                            estado TEXT NOT NULL DEFAULT 'pendente',

                            CHECK (opcao IN ('python', 'java','javascript')),
                            CHECK(mandato >= 0),
                            CHECK(sequencia > 0),
                            CHECK(estado IN ('pendente','confirmada')),
                            UNIQUE(mandato, sequencia)
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


    def salvar_operacao_pendente(
        self,
        id_operacao,
        eleitor,
        opcao,
        mandato,
        sequencia
    ):
        if (
            not isinstance(id_operacao, str)
            or not id_operacao.strip()
            or not isinstance(eleitor, str)
            or not eleitor.strip()
            or opcao not in ("python", "java", "javascript")
            or type(mandato) is not int
            or mandato < 0
            or type(sequencia) is not int
            or sequencia <= 0
        ):
            return False, "Dados da operacao invalidos"

        with self.lock:
            try:
                with self.conectar() as conexao:
                    conexao.execute("""
                        INSERT INTO operacoes (
                            id_operacao,
                            eleitor,
                            opcao,
                            mandato,
                            sequencia,
                            estado
                        )
                        VALUES (?, ?, ?, ?, ?, 'pendente')
                    """, (
                        id_operacao,
                        eleitor.strip(),
                        opcao,
                        mandato,
                        sequencia
                    ))

                return True, "Operacao pendente armazenada"

            except sqlite3.IntegrityError:
                return False, "Operacao duplicada ou conflitante"


    def consultar_operacoes(self):
        with self.lock:
            with self.conectar() as conexao:
                registros = conexao.execute("""
                    SELECT
                        id_operacao,
                        eleitor,
                        opcao,
                        mandato,
                        sequencia,
                        estado
                    FROM operacoes
                    ORDER BY mandato, sequencia
                """).fetchall()

        return [
            {
                "id_operacao": registro[0],
                "eleitor": registro[1],
                "opcao": registro[2],
                "mandato": registro[3],
                "sequencia": registro[4],
                "estado": registro[5]
            }
            for registro in registros
        ]

##metodo para salvar ou validar uma operação, garantindo que não haja duplicidade ou conflito de dados - idempotência
    def salvar_ou_validar_operacao(
        self, id_operacao, eleitor, opcao, mandato, sequencia
    ):
        # Primeiro tenta registrar a operacao normalmente
        sucesso, mensagem = self.salvar_operacao_pendente(
            id_operacao, eleitor, opcao, mandato, sequencia
        )

        if sucesso:
            return True, "Operacao armazenada"

        # Se houve falha, verifica se ela ja existe
        with self.lock:
            with self.conectar() as conexao:
                registro = conexao.execute("""
                    SELECT eleitor, opcao, mandato, sequencia
                    FROM operacoes
                    WHERE id_operacao = ?
                """, (id_operacao,)).fetchone()

        if registro is None:
            return False, mensagem

        dados_esperados = (
            eleitor.strip() if isinstance(eleitor, str) else eleitor,
            opcao,
            mandato,
            sequencia
        )

        if registro == dados_esperados:
            return True, "Operacao ja armazenada anteriormente"

        return False, "Conflito nos dados da operacao"
