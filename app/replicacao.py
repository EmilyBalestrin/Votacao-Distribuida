
import requests


def enviar_operacao(id_origem, enderecos_nos, operacao):
    resultados = {}

    for id_no, endereco in enderecos_nos.items():

        # Nao envia para o proprio servidor
        if id_no == id_origem:
            continue

        try:
            resposta = requests.post(
                f"{endereco}/replicacao/receber",
                json={
                    "origem": id_origem,
                    "operacao": operacao
                },
                timeout=3
            )

            resultados[str(id_no)] = {
                "sucesso": resposta.status_code == 200,
                "codigo_http": resposta.status_code
            }

            print(
                f"[Replicacao] No {id_no}: "
                f"HTTP {resposta.status_code}",
                flush=True
            )

        except requests.RequestException as erro:
            resultados[str(id_no)] = {
                "sucesso": False,
                "erro": str(erro)
            }

            print(
                f"[Replicacao] Falha ao comunicar "
                f"com No {id_no}: {erro}",
                flush=True
            )

    return resultados
