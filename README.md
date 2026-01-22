# Bodet Scoreboard Capture - Hóquei em Patins

Aplicação Python para capturar dados do Scorepad Bodet via TCP, com suporte para hóquei em patins.

## Funcionalidades

- **Servidor TCP**: Escuta na porta 4001 (configurável) para receber dados do Scorepad
- **Validação LRC**: Verifica a integridade das mensagens usando Longitudinal Redundancy Check
- **Parsing de Mensagens**: Processa mensagens do protocolo Bodet
- **Output Consola**: Mostra dados recebidos em tempo real
- **Output JSON**: Guarda dados em `matchfacts.json` para integração com OBS/vMix

## Requisitos

- Python 3.6 ou superior
- Scorepad Bodet configurado para enviar dados via TCP
- PC na mesma rede que o Scorepad

## Instalação

1. Clone ou descarregue este repositório
2. Certifique-se de que tem Python 3.6+ instalado
3. Não são necessárias dependências externas (usa apenas biblioteca padrão)

## Configuração

### Configuração do Scorepad Bodet

1. No Scorepad, pressione o botão de menu técnico
2. Introduza o código técnico: **4934**
3. Vá a "Communication Protocols"
4. Crie um novo protocolo:
   - Tipo: **Protocol TV**
   - IP do PC: (IP do computador onde corre esta aplicação)
   - Porta: **4001**
5. Ative o protocolo

### Configuração da Aplicação

Edite o ficheiro `config.ini` se necessário:

```ini
[Server]
host = 0.0.0.0    # IP para escutar (0.0.0.0 = todas as interfaces)
port = 4001       # Porta TCP
```

## Uso

### Execução Básica

```bash
python src/bodet_capture.py
```

A aplicação irá:
1. Iniciar o servidor TCP na porta 4001
2. Aguardar conexão do Scorepad
3. Mostrar mensagens recebidas na consola
4. Guardar dados em `matchfacts.json`

### Output na Consola

Quando receber mensagens, verá algo como:

```
============================================================
BODET SCOREPAD MESSAGE RECEIVED
============================================================
Raw Data (hex): 017f024731318037203430372030312030303031032d
Data Length: 15 bytes
BYTE1: 0x47
BYTE2: 0x31
...
============================================================
```

### Output JSON

Os dados são guardados em `matchfacts.json` no formato:

```json
{
    "score": {
        "home": 0,
        "guest": 0
    },
    "MatchClock": {
        "time": "00:00",
        "period": 1
    },
    "Penalties": {
        "HomeTeam": {
            "Player1": {
                "HPP1-active": 0,
                "HPP1-Time": "00:00"
            },
            ...
        },
        ...
    }
}
```

## Integração com OBS/vMix

### OBS Studio

1. Instale o plugin **URL/API Source** ou **Advanced Scene Switcher**
2. Configure uma fonte que leia `matchfacts.json`
3. Use variáveis de texto para mostrar os dados

### vMix

1. Use a funcionalidade de leitura de ficheiro JSON
2. Configure para ler `matchfacts.json` periodicamente
3. Use os dados nas suas cenas

## Testes

Para testar sem um Scorepad físico, use o script de teste:

```bash
python src/test_messages.py
```

Este script envia mensagens de teste para localhost:4001.

## Protocolo Bodet

O protocolo usa o seguinte formato:

- **SOH** (0x01): Start of Heading
- **Address** (0x7F): Endereço do dispositivo
- **STX** (0x02): Start of Text
- **DADOS**: Dados da mensagem (formato varia por desporto)
- **ETX** (0x03): End of Text
- **LRC**: Longitudinal Redundancy Check (XOR de todos os bytes)

## Desenvolvimento

### Estrutura do Projeto

```
bodet-scoreboard/
├── docs/
│   └── 608264B-Network output and protocols-Scorepad.pdf
├── src/
│   ├── bodet_capture.py      # Servidor TCP principal
│   ├── message_parser.py     # Parser de mensagens
│   └── output_handler.py     # Handler de output
├── config.ini                # Configurações
├── matchfacts.json           # Output JSON
├── requirements.txt
└── README.md
```

### Próximos Passos

- [ ] Implementar parsing específico para hóquei em patins
- [ ] Adicionar suporte para todas as mensagens do protocolo
- [ ] Melhorar tratamento de erros
- [ ] Adicionar logging de mensagens raw para análise

## Notas

- O formato exato das mensagens de hóquei em patins será determinado através de testes com dados reais
- O parser atual mostra dados raw na consola para facilitar a análise
- Consulte o manual Bodet (608264B) para detalhes completos do protocolo

## Licença

Este projeto é baseado no trabalho de [christoph-ernst/bodet-scorepad-parser](https://github.com/christoph-ernst/bodet-scorepad-parser).

## Suporte

Para questões sobre o protocolo Bodet, consulte o manual técnico fornecido pela Bodet.
