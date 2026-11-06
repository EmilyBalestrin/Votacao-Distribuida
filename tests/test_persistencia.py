
from app.persistencia import Persistencia


def test_salvar_voto(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    sucesso, _ = banco.salvar_voto("eleitor001", "python")

    assert sucesso is True


def test_impedir_voto_duplicado(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_voto("eleitor001", "python")

    sucesso, mensagem = banco.salvar_voto(
        "eleitor001", "java"
    )

    assert sucesso is False
    assert mensagem == "Este eleitor ja registrou um voto"


def test_contagem_de_votos(tmp_path):
    banco = Persistencia(str(tmp_path / "teste.db"))

    banco.salvar_voto("eleitor001", "python")
    banco.salvar_voto("eleitor002", "java")
    banco.salvar_voto("eleitor003", "python")

    resultado = banco.consultar_votos()

    assert resultado["total_votos"] == 3
    assert resultado["resultados"]["python"] == 2
    assert resultado["resultados"]["java"] == 1


def test_votos_permanecem_apos_reabrir_banco(tmp_path):
    caminho = str(tmp_path / "teste.db")

    banco = Persistencia(caminho)
    banco.salvar_voto("eleitor001", "python")

    # Simula outra instancia abrindo o mesmo banco
    novo_banco = Persistencia(caminho)

    resultado = novo_banco.consultar_votos()

    assert resultado["total_votos"] == 1
    assert resultado["resultados"]["python"] == 1
