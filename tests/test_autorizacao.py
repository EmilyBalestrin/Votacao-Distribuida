
from app.persistencia import Persistencia


def test_registrar_autorizacao(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    sucesso, mensagem = banco.registrar_autorizacao(1, 3)

    assert sucesso is True
    assert mensagem == "Autorizacao registrada"

    estado = banco.consultar_autorizacao()

    assert estado["mandato"] == 1
    assert estado["candidato"] == 3


def test_rejeitar_proposta_antiga(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.registrar_autorizacao(5, 3)

    sucesso, mensagem = banco.registrar_autorizacao(4, 2)

    assert sucesso is False
    assert mensagem == "Proposta de lideranca antiga"

    estado = banco.consultar_autorizacao()

    assert estado["mandato"] == 5
    assert estado["candidato"] == 3


def test_autorizacao_repetida(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.registrar_autorizacao(2, 3)

    sucesso, mensagem = banco.registrar_autorizacao(2, 3)

    assert sucesso is True
    assert mensagem == "Autorizacao ja registrada"


def test_comparar_candidatos_no_mesmo_mandato(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.registrar_autorizacao(5, 2)

    sucesso, _ = banco.registrar_autorizacao(5, 3)

    assert sucesso is True

    sucesso, _ = banco.registrar_autorizacao(5, 1)

    assert sucesso is False

    estado = banco.consultar_autorizacao()

    assert estado == {
        "mandato": 5,
        "candidato": 3
    }


def test_autorizacao_persistida(tmp_path):
    caminho = str(tmp_path / "teste.db")

    banco = Persistencia(caminho)
    banco.registrar_autorizacao(7, 2)

    # Reabre o mesmo banco em outra instancia
    novo_banco = Persistencia(caminho)

    estado = novo_banco.consultar_autorizacao()

    assert estado["mandato"] == 7
    assert estado["candidato"] == 2

    # Uma proposta antiga continua sendo rejeitada
    sucesso, _ = novo_banco.registrar_autorizacao(6, 3)

    assert sucesso is False
