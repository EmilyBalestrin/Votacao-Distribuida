import requests


def consultar_no(endereco):
    try:
        resposta = requests.get(
            f"{endereco}/status",
            timeout=3
        )

        resposta.raise_for_status()

        return resposta.json()

    except requests.RequestException as erro:
        return {
            "status": "indisponivel",
            "erro": str(erro)
        }