// bot_siacasa/interfaces/web/static/js/chat.js

document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const typingIndicator = document.getElementById('typingIndicator');
    const resetButton = document.getElementById('resetButton');
    
    // Generar o recuperar ID de usuario
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    // Recuperar ID de usuario existente o crear uno nuevo
    let sessionId = localStorage.getItem('siacasa_session_id');
    if (!sessionId) {
        sessionId = generateUUID();
        localStorage.setItem('siacasa_session_id', sessionId);
    }
    console.log("Usando ID de sesión:", sessionId);
    
    // Función para añadir mensaje al chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', isUser ? 'user-message' : 'bot-message');
        
        const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div>${message}</div>
                <div class="message-time">${currentTime}</div>
            </div>
        `;
        
        // Insertar antes del indicador de escritura
        chatMessages.insertBefore(messageDiv, typingIndicator);
        
        // Scroll al final
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Función para mostrar indicador de escritura
    function showTypingIndicator() {
        typingIndicator.style.display = 'flex';
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Función para ocultar indicador de escritura
    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
    }
    
    // Función para enviar mensaje al backend
    async function sendMessage(message) {
        try {
            showTypingIndicator();
            
            const response = await fetch('/api/mensaje', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mensaje: message,
                    usuario_id: sessionId  // IMPORTANTE: Enviar ID de usuario
                })
            });
            
            const data = await response.json();
            
            hideTypingIndicator();
            
            if (data.status === 'success') {
                addMessage(data.respuesta);
                
                // Si la respuesta incluye un usuario_id, guardarlo
                if (data.usuario_id) {
                    localStorage.setItem('siacasa_session_id', data.usuario_id);
                    sessionId = data.usuario_id;
                    console.log("ID de usuario actualizado:", sessionId);
                }
            } else {
                addMessage('Lo siento, ocurrió un error al procesar tu mensaje. Por favor, inténtalo de nuevo.');
                console.error('Error:', data.error);
            }
        } catch (error) {
            hideTypingIndicator();
            addMessage('Lo siento, no pude conectarme al servidor. Por favor, verifica tu conexión.');
            console.error('Error:', error);
        }
    }
    
    // Función para reiniciar la conversación
    async function resetConversation() {
        try {
            const response = await fetch('/api/reiniciar', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    usuario_id: sessionId  // Incluir ID de usuario también en el reinicio
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Generar nuevo ID de sesión
                sessionId = generateUUID();
                localStorage.setItem('siacasa_session_id', sessionId);
                console.log("Nuevo ID de sesión generado:", sessionId);
                
                // Limpiar mensajes
                while (chatMessages.firstChild) {
                    chatMessages.removeChild(chatMessages.firstChild);
                }
                
                // Agregar de nuevo el indicador de escritura
                chatMessages.appendChild(typingIndicator);
                
                // Mensaje de bienvenida
                addMessage('¡Hola! Soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte hoy?');
            } else {
                console.error('Error al reiniciar conversación:', data.error);
            }
        } catch (error) {
            console.error('Error al reiniciar conversación:', error);
        }
    }
    
    // Evento para enviar mensaje
    function handleSendMessage() {
        const message = userInput.value.trim();
        
        if (message) {
            addMessage(message, true);
            userInput.value = '';
            sendMessage(message);
        }
    }
    
    // Click en botón enviar
    sendButton.addEventListener('click', handleSendMessage);
    
    // Click en botón reiniciar
    if (resetButton) {
        resetButton.addEventListener('click', resetConversation);
    }
    
    // Presionar Enter para enviar
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    });
    
    // Enfoque en el input al cargar
    userInput.focus();
});