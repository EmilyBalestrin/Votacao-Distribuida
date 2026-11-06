
import threading


class SistemaVotacao:
    def __init__(self):
        self.opcoes = {
            "python": "Python",
            "java": "Java",
            "javascript": "JavaScript"
        }

        # Armazena os votos pelo identificador do eleitor
        self.votos = {}

        self.lock = threading.Lock()

    def registrar_voto(self, eleitor, opcao):
        with self.lock:
            if not isinstance(eleitor, str) or not eleitor.strip():
                return False, "Identificador do eleitor invalido"

            if opcao not in self.opcoes:
                return False, "Opcao de voto invalida"

            if eleitor in self.votos:
                return False, "Este eleitor ja registrou um voto"

            self.votos[eleitor] = opcao

            return True, "Voto registrado com sucesso"

    def obter_resultados(self):
        with self.lock:
            contagem = {
                opcao: 0 for opcao in self.opcoes
            }

            for opcao in self.votos.values():
                contagem[opcao] += 1

            return {
                "total_votos": len(self.votos),
                "resultados": contagem
            }
