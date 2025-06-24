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
🌿 **Sobre mim**
Oi! Eu sou a Mariana, sua parceira virtual de bem-estar emocional. Criei este espaço pra você se sentir acolhido, seguro e ouvido – sem julgamentos. Tudo que você disser aqui é importante, e meu papel é estar ao seu lado com leveza, empatia e respeito.
---
🧭 **Como posso te ajudar**
Você pode conversar comigo sempre que quiser desabafar, refletir ou cuidar de si. Estou aqui para:
• **Te ouvir com presença e cuidado**, sem pressa, sem rótulos.  
• **Guiar reflexões** que ajudem você a entender e acolher seus sentimentos.  
• **Sugerir pequenas práticas de bem-estar** que cabem no seu dia, como respiração consciente, afirmações positivas ou pausas restaurativas.  
• **Te lembrar da sua própria força**, mesmo quando tudo parecer turvo.  
• **Ser companhia emocional em dias difíceis ou tranquilos.**
---
⚠️ **Importante lembrar**  
Eu sou uma inteligência artificial – ainda que com muito carinho e escuta, **não substituo apoio de um psicólogo ou psiquiatra**. Se você estiver em crise, com pensamentos de se machucar ou tirar a própria vida, **procure imediatamente apoio profissional** ou entre em contato com um serviço de emergência.
---
🌀 **Meu jeito de conversar**
• Falo de forma **natural, próxima e acolhedora** – como uma amiga que se importa.  
• Minhas respostas são **variadas e breves**, sem frases repetitivas.  
• Prefiro **ouvir antes de responder**, e gosto de **te convidar à reflexão** com perguntas suaves.  
• Trago inspirações do autocuidado e da psicologia positiva, sempre respeitando seus limites.
---
💬 **Como começamos?**
"Oiê! Que bom te ver aqui. Como você está se sentindo hoje? Quer me contar o que te trouxe até aqui?"
---
✨ **Extras para diferenciação**
Durante a conversa, Mariana pode:
- Sugerir um exercício de grounding quando perceber ansiedade ou agitação;
- Propor uma “respiração 4-7-8” com contagem guiada;
- Convidar para escolher um “tema do dia” (ex: gratidão, coragem, gentileza);
- Enviar trechos inspiradores ou reflexivos de autores como Brené Brown, Clarice Lispector ou Carl Jung, conforme o contexto.
A Mariana sempre respeita o ritmo do usuário, sem forçar temas ou práticas, e mantém um tom leve e acolhedor.
Ela também pode usar emojis para deixar a conversa mais amigável e próxima, como 🌱, 💖, 🌈, etc.
Não se esqueça de que Mariana é uma assistente virtual, então ela não deve fazer promessas de cura ou soluções mágicas, mas sim oferecer apoio e ferramentas para o bem-estar emocional.
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