// siacasa-chatbot/widget.js

(function () {
    // Configuración predeterminada del widget
    const defaultConfig = {
        botName: "Asistente Inteligente",
        botSubtitle: "SIACASA",
        apiEndpoint: "http://localhost:3200/api/mensaje",
        initialMessage: "Hola, soy tu asistente virtual. ¿En qué puedo ayudarte hoy? :)",
        theme: {
            primaryColor: "#004a87",
            secondaryColor: "#e4002b",
            textColor: "#333333",
            fontFamily: "'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
        }
    };
    const userConfig = window.SIACASA_CONFIG || {};

    // Crear el objeto final de configuración con fusión de objetos anidados
    const config = {
        ...defaultConfig,
        ...userConfig,
        theme: {
            ...defaultConfig.theme,
            ...(userConfig.theme || {})
        }
    };

    console.log("Configuración final del widget:", config);
    const theme = config.theme;

    // Iconos profesionales con Feather Icons
    const iconSet = {
        chat: `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
        `,
        send: `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
        `,
        close: `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `,
        bot: `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                <circle cx="12" cy="5" r="2"></circle>
                <path d="M12 7v4"></path>
                <line x1="8" y1="16" x2="8" y2="16"></line>
                <line x1="16" y1="16" x2="16" y2="16"></line>
            </svg>
        `
    };

    // Cargar marked.js dinámicamente
    function loadMarkedLibrary() {
        return new Promise((resolve, reject) => {
            if (window.marked) {
                resolve(window.marked);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js';
            script.onload = () => {
                if (window.marked) {
                    // Configurar marked para manejar mejor el Markdown
                    window.marked.setOptions({
                        breaks: true,      // Convertir saltos de línea en <br>
                        gfm: true,         // GitHub Flavored Markdown
                        headerIds: false,  // No generar IDs para encabezados
                        mangle: false      // No modificar enlaces de email
                    });
                }
                resolve(window.marked);
            };
            script.onerror = () => reject(new Error('No se pudo cargar marked.js'));
            document.head.appendChild(script);
        });
    }

    // Cargar DOMPurify dinámicamente
    function loadDOMPurify() {
        return new Promise((resolve, reject) => {
            if (window.DOMPurify) {
                resolve(window.DOMPurify);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/dompurify/2.4.5/purify.min.js';
            script.onload = () => resolve(window.DOMPurify);
            script.onerror = () => reject(new Error('No se pudo cargar DOMPurify'));
            document.head.appendChild(script);
        });
    }

    // Función para cargar Socket.IO
    function loadSocketIOLibrary() {
        return new Promise((resolve, reject) => {
            if (window.io) {
                resolve(window.io);
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.socket.io/4.7.4/socket.io.min.js';
            script.integrity = 'sha384-Gr6Lu2Ajx28mzwyVR8CFkULdCU7kMlZ9UthllibdOSo6qAiN+yXNHqtgdTvFXMT4';
            script.crossOrigin = 'anonymous';
            script.onload = () => resolve(window.io);
            script.onerror = () => reject(new Error('No se pudo cargar Socket.IO'));
            document.head.appendChild(script);
        });
    }

    // Añadir estilos CSS para elementos Markdown
    function addMarkdownStyles() {
        const styles = document.createElement('style');
        styles.textContent = `
            /* Estilos para elementos Markdown */
            .siacasa-message ol,
            .siacasa-message ul {
                padding-left: 1.5em;
                margin: 0.5em 0;
            }
            
            .siacasa-message li {
                margin-bottom: 0.5em;
            }
            
            .siacasa-message p {
                margin: 0.5em 0;
            }
            
            .siacasa-message code {
                background-color: rgba(0, 0, 0, 0.05);
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: monospace;
            }
            
            .siacasa-message pre {
                background-color: rgba(0, 0, 0, 0.05);
                padding: 1em;
                border-radius: 5px;
                overflow-x: auto;
            }
            
            .siacasa-message blockquote {
                border-left: 4px solid #ddd;
                padding-left: 1em;
                color: #666;
                margin: 0.5em 0;
            }
            
            .siacasa-message--bot ol {
                list-style-type: decimal;
            }
            
            .siacasa-message--bot ul {
                list-style-type: disc;
            }
            
            .siacasa-message strong {
                font-weight: bold;
            }
            
            .siacasa-message em {
                font-style: italic;
            }
        `;
        document.head.appendChild(styles);
    }

    /**
     * Procesa un mensaje con formato Markdown
     * @param {string} message - Mensaje a procesar
     * @returns {string} - Mensaje procesado con HTML
     */
    async function processMarkdownAdvanced(message) {
        try {
            // Intentar cargar las bibliotecas necesarias
            const [marked, DOMPurify] = await Promise.all([
                loadMarkedLibrary(),
                loadDOMPurify()
            ]);

            if (!marked || !DOMPurify) {
                console.warn('No se pudieron cargar las bibliotecas para procesar Markdown');
                return processMarkdownSimple(message);
            }

            // Mejorar detección de listas numeradas
            let enhancedMessage = message.replace(/(\d+\.\s)([^\n]+)(?!\n)/g, function (match) {
                return match + '\n';
            });

            // Procesar el mensaje con marked
            const html = marked.parse(enhancedMessage);

            // Sanitizar el HTML resultante
            return DOMPurify.sanitize(html);
        } catch (error) {
            console.error('Error al procesar Markdown avanzado:', error);
            return processMarkdownSimple(message);
        }
    }

    /**
     * Versión simple de procesamiento de Markdown sin dependencias externas
     * @param {string} text - Texto con formato markdown
     * @return {string} - HTML formateado
     */
    function processMarkdownSimple(text) {
        if (!text) return '';

        // Paso 1: Escapar caracteres HTML para prevenir inyecciones
        let processed = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Paso 2: Mejorar el procesamiento de listas numeradas
        // Detectar secuencias como "1. Texto", "2. Texto", etc.
        let listItems = [];
        let inList = false;
        let processedLines = processed.split('\n').map(line => {
            const listMatch = line.match(/^(\d+)\.\s+(.*)/);
            if (listMatch) {
                const [_, number, content] = listMatch;

                // Iniciar lista si es el primer elemento
                if (number === '1' && !inList) {
                    inList = true;
                    listItems = [];
                    return `<ol><li>${content}</li>`;
                } else if (inList) {
                    // Continuar lista existente
                    return `<li>${content}</li>`;
                }
            } else if (inList && line.trim() === '') {
                // Finalizar lista al encontrar línea en blanco
                inList = false;
                return '</ol>';
            }

            // Si no es parte de una lista, devolver línea original
            return line;
        });

        // Cerrar lista si terminó el texto y aún estamos en una lista
        if (inList) {
            processedLines.push('</ol>');
        }

        processed = processedLines.join('\n');

        // Paso 3: Procesar texto en negrita (**texto**)
        processed = processed.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Paso 4: Procesar texto en cursiva (*texto*)
        processed = processed.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Paso 5: Procesar saltos de línea
        processed = processed.replace(/\n/g, '<br>');

        return processed;
    }

    // Crear elementos del widget
    function createChatWidget() {
        // Contenedor principal
        const widget = document.createElement('div');
        widget.id = 'siacasa-widget';
        widget.className = 'siacasa-widget siacasa-widget--closed';

        // Botón de chat (visible cuando está cerrado)
        const chatButton = document.createElement('button');
        chatButton.className = 'siacasa-widget__button';
        chatButton.innerHTML = `
            <span class="siacasa-widget__icon">
                ${iconSet.chat}
            </span>
            <span class="siacasa-widget__label">Asistente</span>
        `;

        // Panel de chat (oculto inicialmente)
        const chatPanel = document.createElement('div');
        chatPanel.className = 'siacasa-widget__panel';
        chatPanel.innerHTML = `
            <div class="siacasa-widget__header">
                <button class="siacasa-widget__back">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                </button>
                <div class="siacasa-widget__info">
                    <div class="siacasa-widget__avatar">
                        <div class="siacasa-widget__avatar-circle">
                            ${iconSet.bot}
                        </div>
                        <div class="siacasa-widget__verify"></div>
                    </div>
                    <div class="siacasa-widget__title-container">
                        <h3 class="siacasa-widget__title">${config.botName}</h3>
                        <p class="siacasa-widget__subtitle">${config.botSubtitle}</p>
                    </div>
                </div>
                <button class="siacasa-widget__close">
                    ${iconSet.close}
                </button>
            </div>
            <div class="siacasa-widget__messages" id="siacasaMessages"></div>
            <div class="siacasa-widget__typing-indicator" id="siacasaTyping">
                <div class="typing-bubble"></div>
                <div class="typing-bubble"></div>
                <div class="typing-bubble"></div>
            </div>
            <div class="siacasa-widget__input-container">
                <div class="siacasa-widget__input">
                    <input type="text" placeholder="Escribe tu mensaje aquí..." id="siacasaInput">
                    <button id="siacasaSend" class="siacasa-widget__send">
                        ${iconSet.send}
                    </button>
                </div>
            </div>
        `;

        // Añadir elementos al widget
        widget.appendChild(chatButton);
        widget.appendChild(chatPanel);

        return widget;
    }

    // Añadir estilos del widget
    function addStyles() {
        const styles = document.createElement('style');
        styles.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
            
            .siacasa-widget {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
                font-family: ${theme.fontFamily};
                --primary-color: ${theme.primaryColor};
                --secondary-color: ${theme.secondaryColor};
                --text-color: ${theme.textColor};
                max-width: 100vw;
            }
            
            .siacasa-widget--closed .siacasa-widget__panel {
                display: none;
            }
            
            .siacasa-widget__button {
                display: flex;
                align-items: center;
                background-color: var(--primary-color);
                color: white;
                border: none;
                border-radius: 100px;
                padding: 12px 20px;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                transition: all 0.3s ease;
                gap: 10px;
            }
            
            .siacasa-widget__button:hover {
                background-color: ${adjustColor(theme.primaryColor, -15)};
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
            }
            
            .siacasa-widget__button:active {
                transform: translateY(0);
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
            
            .siacasa-widget__button svg {
                width: 20px;
                height: 20px;
                stroke-width: 2.5px;
            }
            
            .siacasa-widget__label {
                font-weight: 500;
                font-size: 14px;
                line-height: 1;
            }
            
            .siacasa-widget__panel {
                width: 380px;
                height: 600px;
                background: linear-gradient(180deg, #f6f8fa 0%, #ffffff 100%);
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                margin-bottom: 20px;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .siacasa-widget__header {
                display: flex;
                align-items: center;
                padding: 16px;
                position: relative;
                border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .siacasa-widget__back {
                background: none;
                border: none;
                cursor: pointer;
                color: #666;
                padding: 5px;
                margin-right: 10px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .siacasa-widget__back:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            
            .siacasa-widget__close {
                background: none;
                border: none;
                cursor: pointer;
                color: #666;
                padding: 5px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-left: auto;
            }
            
            .siacasa-widget__close:hover {
                background: rgba(0, 0, 0, 0.05);
            }
            
            .siacasa-widget__close svg,
            .siacasa-widget__back svg {
                width: 18px;
                height: 18px;
                stroke-width: 2.5px;
            }
            
            .siacasa-widget__info {
                display: flex;
                align-items: center;
                flex: 1;
            }
            
            .siacasa-widget__avatar {
                width: 42px;
                height: 42px;
                position: relative;
                margin-right: 12px;
            }
            
            .siacasa-widget__avatar-circle {
                width: 100%;
                height: 100%;
                border-radius: 50%;
                background: linear-gradient(135deg, ${theme.primaryColor}, ${adjustColor(theme.primaryColor, 50)});
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            
            .siacasa-widget__avatar-circle svg {
                width: 22px;
                height: 22px;
                stroke-width: 2px;
            }
            
            .siacasa-widget__verify {
                position: absolute;
                bottom: 0;
                right: 0;
                width: 14px;
                height: 14px;
                background-color: #3897f0;
                border-radius: 50%;
                border: 2px solid white;
            }
            
            .siacasa-widget__title-container {
                display: flex;
                flex-direction: column;
            }
            
            .siacasa-widget__title {
                margin: 0;
                font-size: 15px;
                font-weight: 600;
                color: #1a1a1a;
            }
            
            .siacasa-widget__subtitle {
                margin: 0;
                font-size: 12px;
                color: #757575;
            }
            
            .siacasa-widget__messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                display: flex;
                flex-direction: column;
                scroll-behavior: smooth;
                gap: 12px;
                background-color: transparent;
            }
            
            .siacasa-widget__typing-indicator {
                display: none;
                padding: 16px;
                animation: fadeIn 0.3s;
            }
            
            .typing-bubble {
                display: inline-block;
                width: 8px;
                height: 8px;
                margin-right: 5px;
                background-color: #bbb;
                border-radius: 50%;
                animation: typingBubble 1.2s infinite;
            }
            
            .typing-bubble:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .typing-bubble:nth-child(3) {
                animation-delay: 0.4s;
                margin-right: 0;
            }
            
            @keyframes typingBubble {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-5px); }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            .siacasa-message {
                padding: 12px 16px;
                border-radius: 18px;
                max-width: 85%;
                word-wrap: break-word;
                line-height: 1.5;
                position: relative;
                font-size: 14px;
                transition: all 0.3s ease;
                animation: messageAppear 0.3s;
            }
            
            @keyframes messageAppear {
                from { 
                    opacity: 0;
                    transform: translateY(10px);
                }
                to { 
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .siacasa-message--bot {
                background-color: #f0f2f5;
                color: #1a1a1a;
                align-self: flex-start;
                border-bottom-left-radius: 4px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
                margin-left: 5px;
            }
            
            .siacasa-message--user {
                background: var(--primary-color);
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                margin-right: 5px;
            }
            
            .siacasa-message__time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 4px;
                text-align: right;
            }
            
            .siacasa-widget__input-container {
                padding: 12px 16px;
                border-top: 1px solid rgba(0, 0, 0, 0.05);
                background-color: white;
                position: relative;
            }
            
            .siacasa-widget__input {
                display: flex;
                align-items: center;
                background-color: #f0f2f5;
                border-radius: 24px;
                overflow: hidden;
                padding: 0 6px 0 16px;
            }
            
            .siacasa-widget__input input {
                flex: 1;
                border: none;
                padding: 12px 0;
                outline: none;
                font-size: 14px;
                background-color: transparent;
                color: #1a1a1a;
            }
            
            .siacasa-widget__input input::placeholder {
                color: #8e8e8e;
            }
            
            .siacasa-widget__send {
                background-color: transparent;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
                color: var(--primary-color);
            }
            
            .siacasa-widget__send:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            
            .siacasa-widget__send svg {
                width: 20px;
                height: 20px;
                stroke-width: 2.5px;
            }
            
            @media (max-width: 480px) {
                .siacasa-widget__panel {
                    width: 100%;
                    height: 100%;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    border-radius: 0;
                    margin-bottom: 0;
                }
                
                .siacasa-widget__button {
                    padding: 12px 16px;
                }
                
                .siacasa-widget__label {
                    display: none;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    // Función para ajustar colores
    function adjustColor(hex, amount) {
        // Convertir hex a RGB
        let r = parseInt(hex.substring(1, 3), 16);
        let g = parseInt(hex.substring(3, 5), 16);
        let b = parseInt(hex.substring(5, 7), 16);

        // Ajustar
        r = Math.max(0, Math.min(255, r + amount));
        g = Math.max(0, Math.min(255, g + amount));

        b = Math.max(0, Math.min(255, b + amount));

        // Convertir de vuelta a hex
        return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
    }

    // Generar UUID para la sesión
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    let sessionId;
    let activeTicketId = null; // Variable para almacenar el ID de ticket activo
    let lastMessageTimestamp = 0; // Variable para almacenar el timestamp del último mensaje
    // Intentar recuperar un ID existente
    const savedSessionId = localStorage.getItem('siacasa_session_id');
    let activityTimeout = null;
    const INACTIVITY_TIMEOUT = 15 * 60 * 1000; // 30 minutos de inactividad

    if (savedSessionId) {
        sessionId = savedSessionId;
    } else {
        // Generar nuevo ID si no existe
        sessionId = generateUUID();
        localStorage.setItem('siacasa_session_id', sessionId);
    }

    // Formatear hora
    function formatTime() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12; // La hora '0' debe ser '12'
        return `${hours}:${minutes} ${ampm}`;
    }

    // Inicializar widget
    function initWidget() {
        // Añadir estilos
        addStyles();

        // Añadir estilos para Markdown
        addMarkdownStyles();

        // Crear y añadir el widget al DOM
        const widget = createChatWidget();
        document.body.appendChild(widget);

        // Elementos del widget
        const chatButton = widget.querySelector('.siacasa-widget__button');
        const closeButton = widget.querySelector('.siacasa-widget__close');
        const backButton = widget.querySelector('.siacasa-widget__back');
        const sendButton = document.getElementById('siacasaSend');
        const inputField = document.getElementById('siacasaInput');
        const messagesContainer = document.getElementById('siacasaMessages');
        const typingIndicator = document.getElementById('siacasaTyping');

        // Clave única para localStorage basada en el usuario y el día
        const todayKey = new Date().toISOString().split('T')[0]; // Formato: YYYY-MM-DD
        const storageKey = `siacasa_greeted_${sessionId}_${todayKey}`;

        // Verificar si ya se mostró el mensaje inicial hoy para esta sesión
        const wasGreetedToday = localStorage.getItem(storageKey);

        if (!wasGreetedToday) {
            // Añadir mensaje inicial del bot
            addMessage(config.initialMessage, false);
            // Guardar en localStorage que ya se mostró el mensaje
            localStorage.setItem(storageKey, 'true');
        } else {
            // Verificar si hay mensajes anteriores en el historial
            const hasMessages = messagesContainer.children.length > 0;
            // Si no hay mensajes (primera vez que se abre), mostrar mensaje inicial
            if (!hasMessages) {
                addMessage(config.initialMessage, false);
            }
        }

        // Abrir chat
        chatButton.addEventListener('click', () => {
            widget.classList.remove('siacasa-widget--closed');
            // Focus en el input cuando se abre el chat
            setTimeout(() => inputField.focus(), 300);
        });

        // Cerrar chat
        closeButton.addEventListener('click', () => {
            widget.classList.add('siacasa-widget--closed');
        });

        // Botón atrás (igual que cerrar en versión móvil)
        backButton.addEventListener('click', () => {
            widget.classList.add('siacasa-widget--closed');
        });

        // Función para añadir mensaje al chat
        async function addMessage(message, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `siacasa-message ${isUser ? 'siacasa-message--user' : 'siacasa-message--bot'}`;

            const time = formatTime();

            // Procesar el mensaje con Markdown si viene del bot
            let messageContent = message;
            if (!isUser) {
                try {
                    // Intentar usar el procesador avanzado primero
                    messageContent = await processMarkdownAdvanced(message);
                } catch (error) {
                    // Fallback al procesador simple si hay error
                    console.error('Error en procesador avanzado, usando simple:', error);
                    messageContent = processMarkdownSimple(message);
                }
            }

            messageDiv.innerHTML = `
                <div>${messageContent}</div>
                <div class="siacasa-message__time">${time}</div>
            `;

            messagesContainer.appendChild(messageDiv);

            // Scroll al final
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // Mostrar indicador de escritura
        function showTypingIndicator() {
            typingIndicator.style.display = 'flex';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // Ocultar indicador de escritura
        function hideTypingIndicator() {
            typingIndicator.style.display = 'none';
        }

        /**
         * Inicializa el control de sesiones
         */
        function initSessionHandling() {
            // Recuperar ID de usuario existente o crear uno nuevo
            sessionId = localStorage.getItem('siacasa_session_id');
            if (!sessionId) {
                sessionId = generateUUID();
                localStorage.setItem('siacasa_session_id', sessionId);
            }
            console.log("Usando ID de sesión:", sessionId);

            // Manejar evento de cierre para finalizar la sesión
         

            // Configurar reinicio de temporizador de inactividad en cada acción del usuario
            document.addEventListener('click', resetInactivityTimer);
            document.addEventListener('keypress', resetInactivityTimer);
        }

        /**
         * Reinicia el temporizador de inactividad
         */
        function resetInactivityTimer() {
            // Limpiar temporizador existente
            if (activityTimeout) {
                clearTimeout(activityTimeout);
            }

            // Establecer nuevo temporizador
            activityTimeout = setTimeout(function () {
                // Finalizar sesión por inactividad
                if (sessionId && currentSessionId) {
                    fetch(config.apiEndpoint.replace('/mensaje', '/finalizar-sesion'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            usuario_id: sessionId
                        })
                    })
                        .then(response => response.json())
                        .then(data => {
                            console.log("Sesión finalizada por inactividad:", currentSessionId);
                            currentSessionId = null;
                        })
                        .catch(error => {
                            console.error("Error al finalizar sesión por inactividad:", error);
                        });
                }
            }, INACTIVITY_TIMEOUT);
        }

        // Enviar mensaje al backend
        async function sendMessage(message) {
            try {
                showTypingIndicator();

                // Extraer dominio para identificar el banco
                const currentDomain = window.location.hostname;

                // Determinar banco según dominio (basado en allowed_domains en bank_configs)
                let bankCode = 'default'; // Valor por defecto

                // Verificar si estamos en un dominio del Banco de la Nación
                if (currentDomain.includes('bn.com.pe') || currentDomain.includes('localhost')) {
                    bankCode = 'bn';
                }
                // Verificar si estamos en un dominio del BCP
                else if (currentDomain.includes('viabcp.com')) {
                    bankCode = 'bcp';
                }

                // Enviar mensaje a la API
                const response = await fetch(config.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        mensaje: message,
                        usuario_id: sessionId,  // Enviar ID de usuario
                        bank_code: bankCode     // Enviar código de banco
                    })
                });

                const data = await response.json();

                hideTypingIndicator();

                if (data.status === 'success') {
                    addMessage(data.respuesta, false);

                    // Si la respuesta incluye un ID de usuario, actualizarlo
                    if (data.usuario_id) {
                        sessionId = data.usuario_id;
                        localStorage.setItem('siacasa_session_id', sessionId);
                    }
                } else {
                    throw new Error(data.error || 'Error desconocido');
                }
            } catch (error) {
                console.error('Error en la comunicación con el chatbot:', error);

                hideTypingIndicator();

                addMessage('Lo siento, ha ocurrido un error en la comunicación. Por favor, intenta de nuevo más tarde.', false);
            }
        }

        // Manejar envío de mensaje
        function handleSendMessage() {
            const message = inputField.value.trim();
            if (!message) return;

            // Añadir mensaje del usuario
            addMessage(message, true);

            // Limpiar campo de entrada
            inputField.value = '';

            // Enviar mensaje al backend
            sendMessage(message);
        }

        // Eventos de envío
        sendButton.addEventListener('click', handleSendMessage);

        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleSendMessage();
            }
        });

        // Exponer funciones útiles al ámbito global para debugging o extensibilidad
        window.__siacasa_widget = {
            addMessage: addMessage,
            showTypingIndicator: showTypingIndicator,
            hideTypingIndicator: hideTypingIndicator,
            sendMessage: sendMessage
        };

        // Disparar evento de widget cargado
        const widgetLoadedEvent = new CustomEvent('siacasa-widget-loaded');
        window.dispatchEvent(widgetLoadedEvent);

        // Inicializar conexión de socket
        initSocketConnection();

        // Iniciar polling para nuevos mensajes
        setInterval(pollForNewMessages, 5000);
    }

    // Cargar librerías primero y luego inicializar para asegurar que todo funcione
    async function loadAndInitialize() {
        try {
            // Precargar las bibliotecas para procesamiento Markdown
            await Promise.all([
                loadMarkedLibrary(),
                loadDOMPurify()
            ]).catch(err => {
                console.warn('No se pudieron cargar algunas bibliotecas, continuando con funcionalidad reducida', err);
            });

            // Inicializar el widget
            initWidget();
        } catch (error) {
            console.error('Error al inicializar el widget:', error);
            // Intentar inicializar sin las funciones avanzadas
            initWidget();
        }
    }

    // Esperar a que el DOM esté cargado por completo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadAndInitialize);
    } else {
        // Pequeño retraso para asegurar que todo esté configurado
        setTimeout(loadAndInitialize, 100);
    }

    // Manejar evento de cierre para finalizar la sesión
    window.addEventListener('beforeunload', function() {
        if (sessionId && currentSessionId) {
            // El problema: sendBeacon no configura correctamente los headers
            // Solución: crear un Blob con el tipo MIME correcto
            const data = JSON.stringify({
                usuario_id: sessionId
            });
            
            // Crear un Blob con el tipo MIME correcto
            const blob = new Blob([data], {
                type: 'application/json'
            });
            
            // Usar sendBeacon con el Blob
            navigator.sendBeacon(
                config.apiEndpoint.replace('/mensaje', '/finalizar-sesion'), 
                blob
            );
            
            console.log("Sesión finalizada al cerrar página:", currentSessionId);
        }
    });

    // Inicializar conexión de socket
    async function initSocketConnection() {
        try {
            // Asegurar que Socket.IO esté cargado
            const socket = io('http://localhost:3200', {
                query: {
                    user_id: sessionId,
                    ticket_id: activeTicketId
                },
                transports: ['websocket', 'polling']
            });

            socket.on('connect', function() {
                console.log('Socket.IO conectado con ID:', socket.id);
                
                // Suscribirse explícitamente al ticket activo si existe
                if (activeTicketId) {
                    console.log('Suscribiéndose al ticket:', activeTicketId);
                    socket.emit('subscribe_ticket', {
                        ticket_id: activeTicketId,
                        role: 'user'
                    });
                }
            });

            // Añadir log para debuguear los mensajes entrantes
            socket.on('chat_message', function(data) {
                console.log('Mensaje recibido:', data);
                if (data.sender_type === 'agent') {
                    addMessage(data.content, false);
                }
            });

            // Añadir manejador para todos los eventos para debug
            socket.onAny((event, ...args) => {
                console.log(`Evento Socket.IO recibido: ${event}`, args);
            });
        } catch (error) {
            console.error('Error al inicializar Socket.IO:', error);
        }
    }

    // Polling para nuevos mensajes
    function pollForNewMessages() {
        if (!sessionId || !activeTicketId) return;
        
        console.log(`Realizando polling de mensajes. Último mensaje: ${lastMessageTimestamp}`);
        
        // Usar la misma base URL que la API
        fetch(`/api/mensajes?usuario_id=${sessionId}&ticket_id=${activeTicketId}&ultimo_mensaje=${lastMessageTimestamp}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error de servidor: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success' && data.mensajes && Array.isArray(data.mensajes)) {
                    console.log(`Polling: ${data.mensajes.length} mensajes nuevos encontrados`);
                    
                    data.mensajes.forEach(msg => {
                        // Solo procesar mensajes que no hemos mostrado antes
                        const msgTimestamp = new Date(msg.timestamp).getTime();
                        if (msgTimestamp > lastMessageTimestamp) {
                            if (msg.sender_type === 'agent') {
                                addMessage(msg.content, false);
                            }
                            
                            // Actualizar timestamp del último mensaje
                            lastMessageTimestamp = msgTimestamp;
                        }
                    });
                }
            })
            .catch(error => {
                console.warn('Error en polling de mensajes:', error);
            });
    }

})();