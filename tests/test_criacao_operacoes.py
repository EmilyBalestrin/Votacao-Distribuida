
from app.persistencia import Persistencia


def test_criar_operacao_automaticamente(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    sucesso, mensagem, operacao = banco.criar_operacao_voto(
        "eleitor001", "python", 1
    )

    assert sucesso is True
    assert mensagem == "Operacao criada"
    assert operacao["id_operacao"]
    assert operacao["sequencia"] == 1
    assert operacao["estado"] == "pendente"

    registros = banco.consultar_operacoes()

    assert len(registros) == 1
    assert registros[0]["id_operacao"] == operacao["id_operacao"]


def test_gerar_sequencia_automatica(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    _, _, primeira = banco.criar_operacao_voto(
        "eleitor001", "python", 1
    )

    _, _, segunda = banco.criar_operacao_voto(
        "eleitor002", "java", 1
    )

    assert primeira["sequencia"] == 1
    assert segunda["sequencia"] == 2
    assert primeira["id_operacao"] != segunda["id_operacao"]


def test_impedir_operacao_repetida_do_eleitor(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.criar_operacao_voto(
        "eleitor001", "python", 1
    )

    sucesso, mensagem, operacao = banco.criar_operacao_voto(
        "eleitor001", "java", 1
    )

    assert sucesso is False
    assert mensagem == "Este eleitor ja possui uma operacao"
    assert operacao is None
    assert len(banco.consultar_operacoes()) == 1


def test_operacao_nao_contabiliza_voto(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.criar_operacao_voto(
        "eleitor001", "python", 1
    )

    resultados = banco.consultar_votos()

    assert resultados["total_votos"] == 0


def test_sequencia_por_mandato(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    _, _, primeira = banco.criar_operacao_voto(
        "eleitor001", "python", 1
    )

    _, _, segunda = banco.criar_operacao_voto(
        "eleitor002", "java", 2
    )

    assert primeira["sequencia"] == 1
    assert segunda["sequencia"] == 1
    assert primeira["mandato"] != segunda["mandato"]
