// bot_siacasa/interfaces/web/static/js/chat.js

document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const typingIndicator = document.getElementById('typingIndicator');
    const resetButton = document.getElementById('resetButton');
    
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
                    mensaje: message
                })
            });
            
            const data = await response.json();
            
            hideTypingIndicator();
            
            if (data.status === 'success') {
                addMessage(data.respuesta);
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
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
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