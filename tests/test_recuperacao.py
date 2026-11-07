
from app.recuperacao import comparar_estados


def criar_operacao(
    id_operacao="op001",
    opcao="python",
    estado="pendente",
    sequencia=1
):
    return {
        "id_operacao": id_operacao,
        "eleitor": "eleitor001",
        "opcao": opcao,
        "mandato": 1,
        "sequencia": sequencia,
        "estado": estado
    }


def test_operacoes_iguais():
    operacao = criar_operacao()

    coleta = {
        "estados": {
            "1": [operacao],
            "2": [operacao],
            "3": [operacao]
        },
        "erros": {}
    }

    resultado = comparar_estados(coleta)

    assert resultado["total_operacoes_identificadas"] == 1
    assert resultado["operacoes_ausentes"] == []
    assert resultado["conflitos"] == []
    assert resultado["estados_diferentes"] == []


def test_identificar_operacao_ausente():
    operacao = criar_operacao()

    coleta = {
        "estados": {
            "1": [operacao],
            "2": [],
            "3": [operacao]
        },
        "erros": {}
    }

    resultado = comparar_estados(coleta)

    assert len(resultado["operacoes_ausentes"]) == 1
    assert resultado["operacoes_ausentes"][0] == {
        "id_operacao": "op001",
        "presentes_em": ["1", "3"],
        "ausentes_em": ["2"]
    }


def test_identificar_conflito_de_dados():
    coleta = {
        "estados": {
            "1": [criar_operacao(opcao="python")],
            "2": [criar_operacao(opcao="java")],
            "3": []
        },
        "erros": {}
    }

    resultado = comparar_estados(coleta)

    assert any(
        conflito["tipo"] == "dados_divergentes"
        for conflito in resultado["conflitos"]
    )


def test_identificar_estados_diferentes():
    coleta = {
        "estados": {
            "1": [criar_operacao(estado="confirmada")],
            "2": [criar_operacao(estado="pendente")],
            "3": [criar_operacao(estado="confirmada")]
        },
        "erros": {}
    }

    resultado = comparar_estados(coleta)

    assert len(resultado["estados_diferentes"]) == 1


def test_identificar_conflito_de_posicao():
    coleta = {
        "estados": {
            "1": [criar_operacao(id_operacao="op001")],
            "2": [criar_operacao(id_operacao="op002")],
            "3": []
        },
        "erros": {}
    }

    resultado = comparar_estados(coleta)

    assert any(
        conflito["tipo"] == "conflito_de_posicao"
        for conflito in resultado["conflitos"]
    )


def test_no_indisponivel_nao_e_ausencia():
    coleta = {
        "estados": {
            "1": [criar_operacao()],
            "3": [criar_operacao()]
        },
        "erros": {
            "2": "Servidor indisponivel"
        }
    }

    resultado = comparar_estados(coleta)

    assert resultado["operacoes_ausentes"] == []
    assert resultado["nos_indisponiveis"] == ["2"]
