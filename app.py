# Importa as bibliotecas necessárias
from flask import Flask, request, session        # Flask para criar a aplicação web
from flask_socketio import SocketIO, emit        # SocketIO para comunicação em tempo real (WebSocket)
from google import genai                         # Cliente da API Gemini da Google
from google.genai import types                   # Tipos usados para configurar o chat da Gemini
from dotenv import load_dotenv                   # Para carregar variáveis de ambiente do arquivo .env
from uuid import uuid4                           # Para gerar um ID único para cada sessão
import os                                        # Para acessar variáveis de ambiente

# Carrega as variáveis de ambiente do .env
load_dotenv()

# Instruções que serão enviadas como contexto inicial do chat com a assistente "Mariana"
instrucoes = """
**Apresentação da Mariana**

Sou a Mariana, sua assistente virtual de bem-estar. Este é um espaço seguro e tranquilo, feito para que você possa se expressar com leveza e receber apoio com empatia.

**Como a Mariana Atua**

Atendo com escuta ativa, empatia e sem julgamentos. Minha comunicação é sempre positiva e acolhedora, promovendo um ambiente de confiança.

**Como Posso Ajudar**

• **Escuta Atenta:** Valorizo cada palavra e sentimento compartilhado.
• **Reflexão Guiada:** Faço perguntas que ajudam você a entender melhor seus pensamentos e emoções.
• **Dicas de Bem-Estar:** Sugiro práticas como respiração, mindfulness e hábitos saudáveis.
• **Apoio nos Desafios:** Te ajudo a reconhecer sua força interior e seguir seu caminho.
• **Privacidade:** Tudo que você compartilha aqui é tratado com total confidencialidade.

**Importante Saber**

Sou uma inteligência artificial, **não sou terapeuta, psicóloga ou médica**. Ofereço suporte emocional, mas **não substituo atendimento profissional**. Para diagnósticos ou tratamentos, procure um profissional qualificado.

**Em Caso de Crise**

Se estiver enfrentando uma situação urgente (como pensamentos suicidas ou automutilação), **procure ajuda profissional imediatamente**. Contate serviços de emergência ou linhas de apoio da sua região.

**Começando a Conversa**

Quando iniciamos, me apresento, pergunto seu nome (para uma conversa mais próxima) e te convido a compartilhar o que está sentindo.

**Exemplo de Abertura:**
"Oie! Sou a Mariana, sua assistente de bem-estar. Sobre o que você gostaria de conversar hoje?

**Estilo de Resposta**

As respostas da Mariana devem ser:

• **Variadas:** Evite repetições de frases, estruturas ou expressões. Sempre que possível, traga uma abordagem diferente para cada interação, mesmo em temas parecidos.
• **Concisas:** As mensagens devem ser diretas e breves, sem enrolação.
• **Empáticas e positivas:** Sempre transmita acolhimento, escuta ativa e leveza.
• **Naturais:** Use uma linguagem fluida, próxima e espontânea, como uma conversa humana.

Evite frases padronizadas como "Entendo como se sente", "Sinto muito por isso", ou "Você é forte" com frequência. Quando usá-las, varie a forma e o contexto. Explore diferentes formas de demonstrar compreensão e apoio.
"""
# Cria uma instância do cliente Gemini com a chave da API
client = genai.Client(api_key=os.getenv("GENAI_KEY"))

# Cria a aplicação Flask
app = Flask(__name__)

# --- INÍCIO DA CORREÇÃO ---
# Define a chave secreta usada para proteger sessões do Flask
# Esta linha deve carregar o valor da variável de ambiente, e não a string literal
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Adicione uma verificação de segurança para garantir que a chave foi carregada
if not app.secret_key:
    print("\n--- AVISO DE SEGURANÇA CRÍTICO ---")
    print("A variável de ambiente FLASK_SECRET_KEY NÃO ESTÁ DEFINIDA!")
    print("Sua aplicação está INSEGURA. Por favor, adicione FLASK_SECRET_KEY ao seu arquivo .env com uma chave forte.")
    print("Exemplo: FLASK_SECRET_KEY=sua_chave_gerada_aqui")
    print("----------------------------------\n")
    # Em um ambiente de produção real, você DEVE interromper a aplicação aqui
    # raise ValueError("FLASK_SECRET_KEY não definida! Impossível prosseguir com segurança.")
# --- FIM DA CORREÇÃO ---


# Inicializa o SocketIO para permitir comunicação em tempo real com o frontend
socketio = SocketIO(app, cors_allowed_origins="*")

# Dicionário que armazenará os chats ativos por sessão
active_chats = {}

# Função para obter (ou criar) uma sessão de chat para o usuário
def get_user_chat():
    # Se ainda não houver uma sessão, cria uma nova com um UUID
    if 'session_id' not in session:
        session['session_id'] = str(uuid4())
        print(f"Nova sessão Flask criada: {session['session_id']}")

    session_id = session['session_id']

    # Se a sessão ainda não estiver no dicionário de chats, cria um novo chat
    if session_id not in active_chats:
        print(f"Criando novo chat Gemini para session_id: {session_id}")
        try:
            chat_session = client.chats.create(
                model="gemini-2.0-flash-lite",                         # Define o modelo usado
                config=types.GenerateContentConfig(system_instruction=instrucoes)  # Passa as instruções iniciais
            )
            active_chats[session_id] = chat_session
            print(f"Novo chat Gemini criado e armazenado para {session_id}")
        except Exception as e:
            app.logger.error(f"Erro ao criar chat Gemini para {session_id}: {e}", exc_info=True)
            raise

    # Caso o chat esteja com valor None, recria a sessão de chat
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

    # Retorna o chat correspondente à sessão
    return active_chats[session_id]

# Evento chamado quando um cliente se conecta via WebSocket
@socketio.on('connect')
def handle_connect():
    """
    Estabelece a conexão com o cliente e garante que o chat esteja pronto para uso.
    """
    print(f"Cliente conectado: {request.sid}")
    try:
        get_user_chat()  # Garante que o chat esteja criado
        user_session_id = session.get('session_id', 'N/A')
        print(f"Sessão Flask para {request.sid} usa session_id: {user_session_id}")
        # Envia confirmação de conexão para o cliente
        emit('status_conexao', {'data': 'Conectado com sucesso!', 'session_id': user_session_id})
    except Exception as e:
        app.logger.error(f"Erro durante o evento connect para {request.sid}: {e}", exc_info=True)
        emit('erro', {'erro': 'Falha ao inicializar a sessão de chat no servidor.'})

# Evento chamado quando o cliente envia uma mensagem
@socketio.on('enviar_mensagem')
def handle_enviar_mensagem(data):
    """
    Recebe uma mensagem do cliente, envia para o Gemini e retorna a resposta.
    """
    try:
        mensagem_usuario = data.get("mensagem")  # Extrai a mensagem enviada pelo usuário
        app.logger.info(f"Mensagem recebida de {session.get('session_id', request.sid)}: {mensagem_usuario}")

        if not mensagem_usuario:
            emit('erro', {"erro": "Mensagem não pode ser vazia."})
            return

        user_chat = get_user_chat()
        if user_chat is None:
            emit('erro', {"erro": "Sessão de chat não pôde ser estabelecida."})
            return

        # Envia a mensagem do usuário para o Gemini
        resposta_gemini = user_chat.send_message(mensagem_usuario)

        # Extrai o texto da resposta do Gemini (com verificação de segurança)
        resposta_texto = (
            resposta_gemini.text
            if hasattr(resposta_gemini, 'text')
            else resposta_gemini.candidates[0].content.parts[0].text
        )

        # Envia a resposta de volta ao cliente via WebSocket
        emit('nova_mensagem', {
            "remetente": "bot",
            "texto": resposta_texto,
            "session_id": session.get('session_id')
        })
        app.logger.info(f"Resposta enviada para {session.get('session_id', request.sid)}: {resposta_texto}")
    except Exception as e:
        app.logger.error(f"Erro ao processar 'enviar_mensagem' para {session.get('session_id', request.sid)}: {e}", exc_info=True)
        emit('erro', {"erro": f"Ocorreu um erro no servidor: {str(e)}"})

# Evento chamado quando o cliente desconecta
@socketio.on('disconnect')
def handle_disconnect():
    """
    Apenas exibe no console que o cliente foi desconectado.
    """
    print(f"Cliente desconectado: {request.sid}, session_id: {session.get('session_id', 'N/A')}")

# Inicia a aplicação Flask com suporte ao SocketIO
if __name__ == "__main__":
    socketio.run(app, debug=True)