// Aguarda o carregamento completo do DOM antes de executar o script
document.addEventListener('DOMContentLoaded', () => {
    // Variável que armazenará a conexão WebSocket
    let socket = null;

    // Seleciona os elementos da interface do chat
    const chatBox = document.getElementById('chat-box');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const connectionStatus = document.getElementById('connection-status');
    const iniciarBtn = document.getElementById('iniciarBtn');
    const encerrarBtn = document.getElementById('encerrarBtn');

    // Identificador da sessão do usuário
    let userSessionId = null;

    // Função para adicionar uma mensagem no chat (usuário, bot, status ou erro)
    function addMessageToChat(sender, text, type = 'normal') {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message');

        // Define o tipo de mensagem (usuário, bot ou status)
        if (sender.toLowerCase() === 'user') {
            messageElement.classList.add('user-message');
            sender = 'Você';
        } else if (sender.toLowerCase() === 'bot') {
            messageElement.classList.add('bot-message');
            sender = 'mari';
        } else {
            messageElement.classList.add('status-message');
        }

        // Estiliza mensagens de erro ou de status
        if (type === 'error') {
            messageElement.classList.add('error-text');
            sender = 'Erro';
        } else if (type === 'status') {
            messageElement.classList.add('status-text');
            sender = 'Status';
        }

        // Adiciona o nome do remetente e a mensagem no elemento do chat
        const senderSpan = document.createElement('strong');
        senderSpan.textContent = `${sender}: `;
        messageElement.appendChild(senderSpan);

        const textSpan = document.createElement('span');
        textSpan.textContent = text;
        messageElement.appendChild(textSpan);

        // Adiciona a nova mensagem no chat e rola para o fim
        chatBox.appendChild(messageElement);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Habilita ou desabilita o envio de mensagens no chat
    function setChatEnabled(enabled) {
        messageInput.disabled = !enabled;
        sendButton.disabled = !enabled;
    }

    // Desativa o chat inicialmente e informa ao usuário
    setChatEnabled(false);
    connectionStatus.textContent = 'Desconectado';
    connectionStatus.className = 'status-offline';
    addMessageToChat('Status', 'Clique em "Iniciar conversa" para começar.', 'status');

    // Função que inicia a conexão com o servidor
    function iniciarConversa() {
        if (socket && socket.connected) return; // Evita conexões duplicadas

        // Cria a conexão com o servidor Socket.IO
        socket = io('http://localhost:5000');

        // Quando conectado com sucesso
        socket.on('connect', () => {
            console.log('Conectado ao servidor Socket.IO! SID:', socket.id);
            connectionStatus.textContent = 'Conectado';
            connectionStatus.className = 'status-online';
            addMessageToChat('Status', 'Conectado ao servidor de chat.', 'status');
            setChatEnabled(true);
        });

        // Quando desconectado do servidor
        socket.on('disconnect', () => {
            console.log('Desconectado do servidor Socket.IO.');
            connectionStatus.textContent = 'Desconectado';
            connectionStatus.className = 'status-offline';
            addMessageToChat('Status', 'Você foi desconectado.', 'status');
            setChatEnabled(false);
        });

        // Recebe o ID da sessão do usuário ao conectar
        socket.on('status_conexao', (data) => {
            if (data.session_id) {
                userSessionId = data.session_id;
            }
        });

        // Recebe uma nova mensagem do servidor
        socket.on('nova_mensagem', (data) => {
            addMessageToChat(data.remetente, data.texto);
        });

        // Recebe uma mensagem de erro do servidor
        socket.on('erro', (data) => {
            addMessageToChat('Erro', data.erro, 'error');
        });
    }

    // Função que encerra a conversa com o servidor
    function encerrarConversa() {
        if (socket && socket.connected) {
            socket.disconnect();
            setChatEnabled(false);
            addMessageToChat('Status', 'Conversa encerrada pelo usuário.', 'status');
        }
    }

    // Função que envia uma mensagem para o servidor
    function sendMessageToServer() {
        const messageText = messageInput.value.trim(); // Remove espaços extras

        if (messageText === '') return; // Ignora mensagens vazias

        if (socket && socket.connected) {
            addMessageToChat('user', messageText); // Mostra no chat como "Você"
            socket.emit('enviar_mensagem', { mensagem: messageText }); // Envia ao servidor
            messageInput.value = ''; // Limpa o campo de entrada
            messageInput.focus(); // Coloca o foco de volta no campo
        } else {
            addMessageToChat('Erro', 'Não conectado ao servidor.', 'error');
        }
    }

    // Adiciona eventos aos botões de iniciar, encerrar e enviar mensagem
    iniciarBtn.addEventListener('click', iniciarConversa);
    encerrarBtn.addEventListener('click', encerrarConversa);
    sendButton.addEventListener('click', sendMessageToServer);

    // Permite enviar a mensagem pressionando Enter
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessageToServer();
        }
    });
}); // FIM do DOMContentLoaded
