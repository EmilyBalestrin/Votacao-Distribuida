# Sistema de Votação Distribuída

Projeto acadêmico desenvolvido para a disciplina de **Sistemas Distribuídos**, com o objetivo de implementar uma enquete que utiliza múltiplos servidores para receber e registrar votos, detectar falhas e recuperar dados após a indisponibilidade temporária de um nó.

A enquete apresenta três opções: **Python, Java e JavaScript**. Cada eleitor é identificado por um código informado na interface, utilizado para impedir votos duplicados nos cenários testados.

## 1. Objetivo

Demonstrar, por meio de uma aplicação simples, conceitos de sistemas distribuídos: comunicação entre processos, descoberta de serviços, eleição de líder, detecção de falhas, relógios lógicos, replicação, persistência, quórum e recuperação de dados.

## 2. Tecnologias utilizadas

- **Python e Flask:** serviços HTTP e interface web.
- **Requests:** comunicação REST entre os nós.
- **SQLite:** armazenamento persistente local de mandatos, operações e votos.
- **Docker e Docker Compose:** execução e configuração dos três servidores.
- **HTML, CSS e JavaScript:** formulário de votação e visualização de resultados.
- **Pytest:** testes automatizados dos componentes.

## 3. Arquitetura

O sistema é composto por três serviços (`no1`, `no2` e `no3`) configurados no Docker Compose. Eles compartilham uma rede Docker e utilizam os nomes dos serviços para se comunicar, sem depender de endereços IP fixos escritos no código.

| Serviço | Endereço no computador | Endereço interno no Docker |
|---|---|---|
| Nó 1 | `http://localhost:5001` | `http://no1:5000` |
| Nó 2 | `http://localhost:5002` | `http://no2:5000` |
| Nó 3 | `http://localhost:5003` | `http://no3:5000` |

Cada nó possui armazenamento SQLite próprio, mantido em um volume Docker separado. Em condições normais, o Nó 3 tende a ser o líder por possuir o maior identificador no algoritmo Bully.

### Componentes principais

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Rotas HTTP e integração entre os componentes |
| `app/comunicacao.py` | Consultas REST entre os servidores |
| `app/heartbeat.py` | Monitoramento periódico da disponibilidade dos nós |
| `app/eleicao.py` | Eleição de líder pelo algoritmo Bully |
| `app/relogio_lamport.py` | Manutenção do relógio lógico |
| `app/votacao.py` | Regras básicas de validação dos votos |
| `app/persistencia.py` | Operações e votos persistidos no SQLite |
| `app/replicacao.py` | Envio de operações para os outros nós |
| `app/recuperacao.py` | Consulta e comparação dos estados entre as réplicas |
| `app/templates/enquete.html` | Interface de votação e consulta dos resultados |

## 4. Funcionamento da votação

1. O eleitor acessa `/enquete`, informa um identificador e seleciona uma linguagem.
2. A solicitação é enviada para `/votar` no nó acessado.
3. Se o nó não for o líder conhecido, ele encaminha a solicitação ao líder por HTTP.
4. O líder verifica a disponibilidade de uma maioria dos nós, cria uma operação **pendente** com identificador e sequência e a salva no SQLite.
5. A operação é replicada para os demais servidores; no fluxo testado, a confirmação prossegue quando existe uma maioria de réplicas e as verificações preliminares de liderança são atendidas.
6. Os servidores participantes registram o voto confirmado no SQLite. A interface recebe a resposta e consulta os resultados.

A tabela de operações diferencia os estados `pendente` e `confirmada`. A contagem apresentada por `/resultados` utiliza os votos confirmados no banco **local** de cada servidor.

### Eleição, heartbeat e relógio lógico

- **Heartbeat:** identifica quando servidores deixam de responder e quando retornam.
- **Bully:** elege um novo líder entre os participantes que se comunicam, utilizando o identificador dos nós como prioridade.
- **Lamport:** incrementa relógios lógicos durante o envio e o recebimento de mensagens de replicação, auxiliando a observar a ordem causal dos eventos. Os valores podem coincidir entre nós e não representam tempo físico.

### Replicação e recuperação

As operações são identificadas por `id_operacao` e possuem eleitor, opção, mandato, sequência e estado. O sistema reconhece retransmissões idênticas para evitar inserir a mesma operação duas vezes.

Nos testes controlados de queda de **um** servidor, os outros dois continuam processando votos após a estabilização da liderança. Quando o nó desligado retorna, a rotina de recuperação compara seus registros com duas cópias confirmadas e idênticas dos demais servidores e recupera os registros elegíveis. Operações conflitantes não devem ser sobrescritas automaticamente.

A interface verifica periodicamente a disponibilidade: se não houver maioria suficiente, o botão de votação é desabilitado e aparece um aviso de suspensão. Quando a comunicação é restabelecida, a interface volta a permitir novas tentativas.

## 5. Como executar

### Pré-requisitos

- Docker Desktop com Docker Compose funcional.
- Navegador web.
- Python e Pytest apenas para executar os testes fora dos contêineres.

Na pasta raiz do projeto, execute:

```powershell
docker compose up --build -d
```

Verifique o estado dos serviços:

```powershell
docker compose ps
```

Acesse a enquete em um dos endereços:

- `http://localhost:5001/enquete`
- `http://localhost:5002/enquete`
- `http://localhost:5003/enquete`

Para visualizar os logs:

```powershell
docker compose logs --tail=80 no1 no2 no3
```

Para interromper os contêineres sem remover os volumes:

```powershell
docker compose down
```

> **Atenção:** não utilize `docker compose down -v` durante os testes se desejar preservar os bancos SQLite.

## 6. Rotas utilizadas na demonstração

| Método | Rota | Finalidade |
|---|---|---|
| GET | `/enquete` | Interface web |
| POST | `/votar` | Recebe ou encaminha solicitação de voto |
| GET | `/resultados` | Consulta resultados confirmados no nó |
| GET | `/status` | Estado do servidor |
| GET | `/nos` | Monitoramento de participantes |
| GET | `/lider` | Estado da liderança Bully |
| GET | `/relogio` | Valor do relógio lógico |
| GET | `/operacoes` | Operações persistidas no nó |
| GET | `/votacao/quorum` | Disponibilidade de maioria |
| GET | `/recuperacao/comparar` | Diagnóstico de diferenças entre réplicas |
| POST | `/recuperacao/sincronizar-confirmadas` | Recuperação controlada de operações confirmadas elegíveis |

Existem também rotas internas e experimentais para eleição, replicação, autorização e recuperação. Elas foram desenvolvidas para a comunicação entre servidores e para os testes acadêmicos; não devem ser expostas diretamente em produção.

## 7. Testes

Execute os testes automatizados na pasta raiz, com o ambiente Python configurado:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

### Cenários manuais avaliados

1. **Três nós disponíveis:** registrar voto e verificar sua presença nas três réplicas.
2. **Queda do líder (Nó 3):** verificar eleição do Nó 2 e votação com os dois nós remanescentes.
3. **Queda de um seguidor (Nó 1 ou Nó 2):** votar com os dois nós ativos e conferir recuperação após o retorno.
4. **Apenas um nó disponível:** verificar bloqueio da votação pela interface e pelo backend.
5. **Voto duplicado:** verificar rejeição de uma nova operação do mesmo eleitor.
6. **Relógio de Lamport:** conferir os contadores antes e depois da replicação.

Exemplo de simulação da queda do Nó 3:

```powershell
docker compose stop no3
```

Após verificar a eleição e realizar o teste de votação pelos Nós 1 e 2, religue:

```powershell
docker compose start no3
```

A recuperação automática deve ser verificada pelas operações, pelos resultados e pelos logs do servidor recuperado. Os dados persistentes de testes anteriores podem produzir diferenças entre os totais até que os registros elegíveis sejam reconciliados.

## 8. Limitações conhecidas

Esta implementação é um **protótipo acadêmico** e não um sistema eleitoral de produção.

- O Bully e a verificação de servidores ativos **não constituem, sozinhos, um protocolo de consenso**.
- Embora existam testes de promessas de liderança persistidas e de quórum, essas verificações não oferecem ainda todas as garantias de exclusão de líderes antigos durante partições de rede.
- A confirmação é aplicada em bancos SQLite individuais. Se houver falha durante a própria confirmação, podem ocorrer estados parciais que a recuperação disponível não resolve em todos os cenários.
- A sincronização automática foi testada sobretudo com a queda controlada de um nó por vez e com duas cópias confirmadas e idênticas.
- O relógio de Lamport ajuda a registrar causalidade, mas não substitui coordenação ou consenso para definir uma ordem global e segura de votos.
- O identificador de eleitor fornecido na interface não constitui autenticação de identidade.
- Os resultados de `/resultados` são locais e podem ficar temporariamente desatualizados em um nó que acabou de retornar.

## 9. Organização da entrega

O projeto inclui o código-fonte, a configuração Docker Compose, os testes e esta documentação. As decisões de arquitetura, os cenários de falha e as limitações serão detalhados no artigo/relatório da disciplina.
