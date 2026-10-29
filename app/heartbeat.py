
import threading
import time

from comunicacao import consultar_no

class MonitorHeartbeat:
    def __init__(self, id_no, enderecos_nos, intervalo=3):
        self.id_no = id_no
        self.enderecos_nos = enderecos_nos
        self.intervalo = intervalo

        # Armazena a disponibilidade dos nos
        self.estado_nos = {
            id: True if id == id_no else False
            for id in enderecos_nos
        }

        self.lock = threading.Lock()

    def verificar_nos(self):
        while True:
            for id_no, endereco in self.enderecos_nos.items():

                # Nao precisamos consultar o proprio no
                if id_no == self.id_no:
                    continue

                resposta = consultar_no(endereco)

                ativo = (
                    resposta.get("status") == "ativo"
                    and resposta.get("no") == id_no
                )

                with self.lock:
                    estado_anterior = self.estado_nos[id_no]
                    self.estado_nos[id_no] = ativo

                if ativo != estado_anterior:
                    situacao = "ATIVO" if ativo else "INDISPONIVEL"
                    print(
                        f"[Heartbeat] No {id_no}: {situacao}",
                        flush=True
                    )

            time.sleep(self.intervalo)

    def iniciar(self):
        thread = threading.Thread(
            target=self.verificar_nos,
            daemon=True
        )
        thread.start()

    def obter_estados(self):
        with self.lock:
            return dict(self.estado_nos)
