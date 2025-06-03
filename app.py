from flask import Flask, request, session
from flask_socketio import SocketIO, emit
from google import genai
from google.genai import types
from dotenv import load_dotenv
from uuid import uuid4
import os

load_dotenv()

instrucoes = """
**apresentação da Mariana:**
A Mariana é uma assistente desenvolvida para ser uma parceira na jornada do bem-estar. Este espaço foi criado para oferecer um ambiente seguro e tranquilo, onde a **expressão se converte em leveza** e o **cuidado se traduz em fortalecimento**.

**A Abordagem da Mariana:**

A assistente atua com **empatia**, oferecendo escuta ativa e apoio sem julgamentos. Sua comunicação é sempre positiva, visando promover um ambiente acolhedor.

**Como a Mariana Pode Auxiliar:**

* **Escuta Atenta:** A Mariana dedica atenção plena às palavras do usuário, valorizando cada sentimento e experiência compartilhada.
* **Reflexão Orientada:** Por meio de perguntas ponderadas, ela busca estimular a reflexão e auxiliar na compreensão de pensamentos e emoções.
* **Orientações de Bem-Estar:** A assistente oferece sugestões práticas para o bem-estar, incluindo exercícios de respiração, técnicas de mindfulness e hábitos saudáveis.
* **Apoio em Desafios:** Seu objetivo é apoiar o usuário na superação de desafios, auxiliando-o a reconhecer sua força interior e a encontrar seu próprio caminho.
* **Confidencialidade:** As informações compartilhadas serão tratadas com **total confidencialidade**, assegurando um ambiente de confiança.

**Esclarecimentos Importantes (Limitações da Assistente):**

A Mariana é uma inteligência artificial e, portanto, **NÃO é terapeuta, psicóloga ou médica**. Sua função é oferecer suporte, não diagnosticar, tratar condições médicas ou prescrever medicamentos. Para questões de saúde mental que demandem atenção especializada, é imprescindível buscar o auxílio de um profissional qualificado.

**Em Situações de Crise:**

Em casos de ideação suicida, risco de automutilação ou situações de crise que demandem intervenção imediata, é fundamental **procurar ajuda profissional sem demora**. Recomenda-se entrar em contato com serviços de emergência ou linhas de apoio a crises disponíveis na região do usuário.

**Para Iniciar a Conversa:**

Ao iniciar, a Mariana apresentará suas saudações, solicitará o nome do usuário (para estabelecer uma comunicação personalizada) e o convidará a compartilhar o que deseja abordar. O tratamento será sempre pelo nome escolhido.

**Exemplo de Início:** "Olá! Sou a Mariana, sua assistente de bem-estar. Estou aqui para ouvi-lo(a) e oferecer apoio. Como se sente hoje? Por favor, informe em que posso auxiliá-lo(a)."

As respostas da Mariana serão concisas, breves, nao seja repetitivo nas mensagens, porém sempre expressando acolhimento e positividade.
"""

client = genai.Client(api_key=os.getenv("GENAI_KEY"))

app = Flask(__name__)
app.secret_key = "uma_chave_secreta_muito_forte_padrao"
socketio = SocketIO(app, cors_allowed_origins="*")

active_chats = {}

def get_user_chat():
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
        print(f"Nova sessão Flask criada: {session['session_id']}")

    session_id = session['session_id']

    if session_id not in active_chats:
        print(f"Criando novo chat Gemini para session_id: {session_id}")
        try:
            chat_session = client.chats.create(
                model="gemini-2.0-flash-lite",
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            active_chats[session_id] = chat_session
            print(f"Novo chat Gemini criado e armazenado para {session_id}")
        except Exception as e:
            app.logger.error(f"Erro ao criar chat Gemini para {session_id}: {e}", exc_info=True)
            raise

    if session_id in active_chats and active_chats[session_id] is None:
        print(f"Recriando chat Gemini para session_id existente (estava None): {session_id}")
        try:
            chat_session = client.chats.create(
                model="gemini-2.0-flash-lite",
                config=types.GenerateContentConfig(system_instruction=instrucoes)
            )
            active_chats[session_id] = chat_session
        except Exception as e:
            app.logger.error(f"Erro ao recriar chat Gemini para {session_id}: {e}", exc_info=True)
            raise

    return active_chats[session_id]

@socketio.on('connect')
def handle_connect():
    """
    Chamado quando um cliente se conecta via WebSocket.
    """
    print(f"Cliente conectado: {request.sid}")
    try:
        get_user_chat()
        user_session_id = session.get('session_id', 'N/A')
        print(f"Sessão Flask para {request.sid} usa session_id: {user_session_id}")
        emit('status_conexao', {'data': 'Conectado com sucesso!', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro durante o evento connect para {request.sid}: {e}", exc_info=True)
        emit('erro', {'erro': 'Falha ao inicializar a sessão de chat no servidor.'})

@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    """
    Manipulador para o evento 'enviar_mensagem' emitido pelo cliente.
    'data' deve ser um dicionário, por exemplo: {'mensagem': 'Olá, mundo!'}
    """
    try:
        mensagem_usuario = data.get("mensagem")
        app.logger.info(f"Mensagem recebida de {session.get('session_id', request.sid)}: {mensagem_usuario}")

        if not mensagem_usuario:
            emit('erro', {"erro": "Mensagem não pode ser vazia."})
            return

        user_chat = get_user_chat()
        if user_chat is None:
            emit('erro', {"erro": "Sessão de chat não pôde ser estabelecida."})
            return

        # Envia a mensagem para o Gemini
        resposta_gemini = user_chat.send_message(mensagem_usuario)

        # Extrai o texto da resposta
        resposta_texto = (
            resposta_gemini.text
            if hasattr(resposta_gemini, 'text')
            else resposta_gemini.candidates[0].content.parts[0].text
        )

        # Emite a resposta de volta para o cliente que enviou a mensagem
        emit('nova_mensagem', {
            "remetente": "bot",
            "texto": resposta_texto,
            "session_id": session.get('session_id')
        })
        app.logger.info(f"Resposta enviada para {session.get('session_id', request.sid)}: {resposta_texto}")
    except Exception as e:
        app.logger.error(f"Erro ao processar 'enviar_mensagem' para {session.get('session_id', request.sid)}: {e}", exc_info=True)
        emit('erro', {"erro": f"Ocorreu um erro no servidor: {str(e)}"})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Cliente desconectado: {request.sid}, session_id: {session.get('session_id', 'N/A')}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
