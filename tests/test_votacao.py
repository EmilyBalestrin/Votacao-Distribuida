
from app.votacao import SistemaVotacao


def test_registro_de_voto():
    votacao = SistemaVotacao()

    sucesso, mensagem = votacao.registrar_voto(
        "eleitor001",
        "python"
    )

    assert sucesso is True
    assert mensagem == "Voto registrado com sucesso"


def test_voto_duplicado():
    votacao = SistemaVotacao()

    votacao.registrar_voto("eleitor001", "python")

    sucesso, mensagem = votacao.registrar_voto(
        "eleitor001",
        "java"
    )

    assert sucesso is False
    assert mensagem == "Este eleitor ja registrou um voto"


def test_opcao_invalida():
    votacao = SistemaVotacao()

    sucesso, _ = votacao.registrar_voto(
        "eleitor001",
        "invalida"
    )

    assert sucesso is False


def test_contagem_de_votos():
    votacao = SistemaVotacao()

    votacao.registrar_voto("eleitor001", "python")
    votacao.registrar_voto("eleitor002", "java")
    votacao.registrar_voto("eleitor003", "python")

    resultado = votacao.obter_resultados()

    assert resultado["total_votos"] == 3
    assert resultado["resultados"]["python"] == 2
    assert resultado["resultados"]["java"] == 1
    assert resultado["resultados"]["javascript"] == 0
