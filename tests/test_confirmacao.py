
from app.persistencia import Persistencia


def test_confirmar_operacao_pendente(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    sucesso, mensagem = banco.confirmar_operacao_local("op001")

    assert sucesso is True
    assert mensagem == "Operacao confirmada localmente"

    operacoes = banco.consultar_operacoes()
    votos = banco.consultar_votos()

    assert operacoes[0]["estado"] == "confirmada"
    assert votos["total_votos"] == 1
    assert votos["resultados"]["python"] == 1


def test_confirmacao_repetida(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    banco.confirmar_operacao_local("op001")

    sucesso, mensagem = banco.confirmar_operacao_local("op001")

    assert sucesso is True
    assert mensagem == "Operacao ja confirmada"
    assert banco.consultar_votos()["total_votos"] == 1


def test_confirmar_operacao_inexistente(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    sucesso, mensagem = banco.confirmar_operacao_local(
        "op-inexistente"
    )

    assert sucesso is False
    assert mensagem == "Operacao nao encontrada"
    assert banco.consultar_votos()["total_votos"] == 0


def test_impedir_segundo_voto_do_eleitor(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    banco.salvar_operacao_pendente(
        "op002", "eleitor001", "java", 1, 2
    )

    banco.confirmar_operacao_local("op001")

    sucesso, mensagem = banco.confirmar_operacao_local("op002")

    assert sucesso is False
    assert mensagem == "Eleitor ja possui voto registrado"

    operacoes = banco.consultar_operacoes()
    votos = banco.consultar_votos()

    assert operacoes[1]["estado"] == "pendente"
    assert votos["total_votos"] == 1
    assert votos["resultados"]["python"] == 1
    assert votos["resultados"]["java"] == 0
