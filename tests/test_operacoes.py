
from app.persistencia import Persistencia


def test_salvar_operacao_pendente(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    sucesso, mensagem = banco.salvar_operacao_pendente(
        "op001",
        "eleitor001",
        "python",
        1,
        1
    )

    assert sucesso is True
    assert mensagem == "Operacao pendente armazenada"

    operacoes = banco.consultar_operacoes()

    assert len(operacoes) == 1
    assert operacoes[0]["estado"] == "pendente"


def test_impedir_operacao_duplicada(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    sucesso, _ = banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    assert sucesso is False


def test_impedir_conflito_de_sequencia(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    sucesso, _ = banco.salvar_operacao_pendente(
        "op002", "eleitor002", "java", 1, 1
    )

    assert sucesso is False


def test_persistencia_da_operacao(tmp_path):
    caminho = str(tmp_path / "teste.db")

    banco = Persistencia(caminho)

    banco.salvar_operacao_pendente(
        "op001", "eleitor001", "python", 1, 1
    )

    novo_banco = Persistencia(caminho)
    operacoes = novo_banco.consultar_operacoes()

    assert len(operacoes) == 1
    assert operacoes[0]["id_operacao"] == "op001"
    assert operacoes[0]["estado"] == "pendente"


def test_repeticao_da_mesma_operacao(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_ou_validar_operacao(
        "op001", "eleitor001", "python", 1, 1
    )

    sucesso, mensagem = banco.salvar_ou_validar_operacao(
        "op001", "eleitor001", "python", 1, 1
    )

    assert sucesso is True
    assert mensagem == "Operacao ja armazenada anteriormente"
    assert len(banco.consultar_operacoes()) == 1


def test_conflito_na_mesma_operacao(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_ou_validar_operacao(
        "op001", "eleitor001", "python", 1, 1
    )

    sucesso, mensagem = banco.salvar_ou_validar_operacao(
        "op001", "eleitor001", "java", 1, 1
    )

    assert sucesso is False
    assert mensagem == "Conflito nos dados da operacao"
