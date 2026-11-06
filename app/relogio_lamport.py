
import threading


class RelogioLamport:
    def __init__(self):
        self.contador = 0
        self.lock = threading.Lock()

    def obter_valor(self):
        with self.lock:
            return self.contador

    def evento_local(self):
        with self.lock:
            self.contador += 1
            return self.contador

    def enviar_mensagem(self):
        with self.lock:
            self.contador += 1
            return self.contador

    def receber_mensagem(self, valor_recebido):
        with self.lock:
            self.contador = max(
                self.contador,
                valor_recebido
            ) + 1

            return self.contador
