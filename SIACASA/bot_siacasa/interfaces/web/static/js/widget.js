// siacasa-chatbot/widget.js

(function () {
    // Configuración predeterminada del widget
    const defaultConfig = {
        botName: "Asistente Inteligente",
        botSubtitle: "SIACASA",
        apiEndpoint: "http://localhost:3200/api/mensaje",
        initialMessage:
            "Hola, soy tu asistente virtual. ¿En qué puedo ayudarte hoy? :)",
        theme: {
            primaryColor: "#004a87",
            secondaryColor: "#e4002b",
            textColor: "#333333",
            fontFamily:
                "'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        },
    };

    // Crear el objeto final de configuración con fusión de objetos anidados
    const userConfig = window.SIACASA_CONFIG || {};
    const config = {
        ...defaultConfig,
        ...userConfig,
        theme: {
            ...defaultConfig.theme,
            ...(userConfig.theme || {}),
        },
    };

    console.log("Configuración final del widget:", config);
    const theme = config.theme;
    const processedMessageIds = new Set();

    // Iconos profesionales con Feather Icons
    const iconSet = {
        chat: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
        send: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>`,
        close: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
        bot: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>`,
    };

    // Variables globales
    let sessionId;
    let socket = null;
    let activeTicketId = null;
    let lastMessageTimestamp = 0;
    let activityTimeout = null;
    let currentSessionId = null;
    let messagesContainer;
    let typingIndicator;

    // Constantes
    const INACTIVITY_TIMEOUT = 15 * 60 * 1000; // 15 minutos
    const POLLING_INTERVAL = 5000; // 5 segundos
    const serverHost = window.location.hostname;
    const serverPort = 3200;

    // ======== CARGADORES DE BIBLIOTECAS ========

    /**
     * Carga dinámicamente una biblioteca externa
     * @param {string} url - URL de la biblioteca
     * @param {Object} options - Opciones adicionales (integrity, crossOrigin)
     * @returns {Promise} - Promesa que se resuelve cuando la biblioteca está cargada
     */
    function loadLibrary(url, options = {}) {
        return new Promise((resolve, reject) => {
            // Verificar si ya está cargada
            if (options.checkGlobal && window[options.checkGlobal]) {
                resolve(window[options.checkGlobal]);
                return;
            }

            const script = document.createElement("script");
            script.src = url;

            if (options.integrity) {
                script.integrity = options.integrity;
                script.crossOrigin = options.crossOrigin || "anonymous";
            }

            script.onload = () => {
                console.log(`Biblioteca cargada: ${url}`);
                if (options.checkGlobal) {
                    resolve(window[options.checkGlobal]);
                } else {
                    resolve();
                }
            };

            script.onerror = (error) => {
                console.error(`Error al cargar biblioteca: ${url}`, error);
                if (options.fallbackUrl) {
                    console.log(`Intentando con fallback: ${options.fallbackUrl}`);
                    const fallbackScript = document.createElement("script");
                    fallbackScript.src = options.fallbackUrl;
                    fallbackScript.onload = () => {
                        if (options.checkGlobal) {
                            resolve(window[options.checkGlobal]);
                        } else {
                            resolve();
                        }
                    };
                    fallbackScript.onerror = () =>
                        reject(new Error(`No se pudo cargar ${url} ni su fallback`));
                    document.head.appendChild(fallbackScript);
                } else {
                    reject(error);
                }
            };

            document.head.appendChild(script);
        });
    }

    // Función para cargar las bibliotecas necesarias
    async function loadDependencies() {
        try {
            // Cargar bibliotecas en paralelo
            const [marked, DOMPurify, io] = await Promise.all([
                loadLibrary("https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js", {
                    checkGlobal: "marked",
                }),
                loadLibrary(
                    "https://cdnjs.cloudflare.com/ajax/libs/dompurify/2.4.5/purify.min.js",
                    {
                        checkGlobal: "DOMPurify",
                    }
                ),
                loadLibrary("https://cdn.socket.io/4.7.4/socket.io.min.js", {
                    checkGlobal: "io",
                    integrity:
                        "sha384-Gr6Lu2Ajx28mzwyVR8CFkULdCU7kMlZ9UthllibdOSo6qAiN+yXNHqtgdTvFXMT4",
                    crossOrigin: "anonymous",
                    fallbackUrl: "https://cdn.socket.io/4.6.0/socket.io.min.js",
                }),
            ]);

            // Configuración de marked
            if (marked) {
                marked.setOptions({
                    breaks: true,
                    gfm: true,
                    headerIds: false,
                    mangle: false,
                });
            }

            return { marked, DOMPurify, io };
        } catch (error) {
            console.warn("No se pudieron cargar todas las dependencias", error);
            // Devolver las bibliotecas que se hayan cargado con éxito
            return {
                marked: window.marked,
                DOMPurify: window.DOMPurify,
                io: window.io,
            };
        }
    }

    // ======== GESTIÓN DE ESTILOS ========

    /**
     * Añade los estilos del widget al documento
     */
    function addStyles() {
        const styles = document.createElement("style");
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
                background: linear-gradient(135deg, ${theme.primaryColor
            }, ${adjustColor(theme.primaryColor, 50)});
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

    // ======== UTILIDADES ========

    /**
     * Función para ajustar colores
     * @param {string} hex - Color en formato hexadecimal
     * @param {number} amount - Cantidad a ajustar
     * @returns {string} - Color ajustado
     */
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

    /**
     * Genera un UUID para la sesión
     * @returns {string} - UUID generado
     */
    function generateUUID() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
            /[xy]/g,
            function (c) {
                const r = (Math.random() * 16) | 0;
                const v = c === "x" ? r : (r & 0x3) | 0x8;
                return v.toString(16);
            }
        );
    }

    /**
     * Formatea la hora actual
     * @returns {string} - Hora formateada
     */
    function formatTime() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, "0");
        const ampm = hours >= 12 ? "PM" : "AM";
        hours = hours % 12;
        hours = hours ? hours : 12; // La hora '0' debe ser '12'
        return `${hours}:${minutes} ${ampm}`;
    }

    /**
     * Determina el código de banco según el dominio actual
     * @returns {string} - Código de banco
     */
    function getBankCode() {
        const currentDomain = window.location.hostname;

        if (
            currentDomain.includes("bn.com.pe") ||
            currentDomain.includes("localhost")
        ) {
            return "bn";
        } else if (currentDomain.includes("viabcp.com")) {
            return "bcp";
        }

        return "default";
    }

    // ======== PROCESAMIENTO DE MARKDOWN ========

    /**
     * Procesa un mensaje con formato Markdown
     * @param {string} message - Mensaje a procesar
     * @returns {string} - Mensaje procesado con HTML
     */
    async function processMarkdown(message) {
        try {
            // Intentar usar marked y DOMPurify si están disponibles
            if (window.marked && window.DOMPurify) {
                // Mejorar detección de listas numeradas
                let enhancedMessage = message.replace(
                    /(\d+\.\s)([^\n]+)(?!\n)/g,
                    function (match) {
                        return match + "\n";
                    }
                );

                // Procesar el mensaje con marked
                const html = window.marked.parse(enhancedMessage);

                // Sanitizar el HTML resultante
                return window.DOMPurify.sanitize(html);
            } else {
                // Fallback a versión simple
                return processMarkdownSimple(message);
            }
        } catch (error) {
            console.error("Error al procesar Markdown:", error);
            return processMarkdownSimple(message);
        }
    }

    /**
     * Versión simple de procesamiento de Markdown sin dependencias externas
     * @param {string} text - Texto con formato markdown
     * @return {string} - HTML formateado
     */
    function processMarkdownSimple(text) {
        if (!text) return "";

        // Paso 1: Escapar caracteres HTML para prevenir inyecciones
        let processed = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

        // Paso 2: Mejorar el procesamiento de listas numeradas
        let inList = false;
        let processedLines = processed.split("\n").map((line) => {
            const listMatch = line.match(/^(\d+)\.\s+(.*)/);
            if (listMatch) {
                const [_, number, content] = listMatch;

                // Iniciar lista si es el primer elemento
                if (number === "1" && !inList) {
                    inList = true;
                    return `<ol><li>${content}</li>`;
                } else if (inList) {
                    // Continuar lista existente
                    return `<li>${content}</li>`;
                }
            } else if (inList && line.trim() === "") {
                // Finalizar lista al encontrar línea en blanco
                inList = false;
                return "</ol>";
            }

            // Si no es parte de una lista, devolver línea original
            return line;
        });

        // Cerrar lista si terminó el texto y aún estamos en una lista
        if (inList) {
            processedLines.push("</ol>");
        }

        processed = processedLines.join("\n");

        // Paso 3: Procesar texto en negrita (**texto**)
        processed = processed.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

        // Paso 4: Procesar texto en cursiva (*texto*)
        processed = processed.replace(/\*([^*]+)\*/g, "<em>$1</em>");

        // Paso 5: Procesar saltos de línea
        processed = processed.replace(/\n/g, "<br>");

        return processed;
    }

    // ======== ELEMENTOS DEL WIDGET ========

    /**
     * Crea los elementos del widget
     * @returns {HTMLElement} - Elemento del widget
     */
    function createChatWidget() {
        // Contenedor principal
        const widget = document.createElement("div");
        widget.id = "siacasa-widget";
        widget.className = "siacasa-widget siacasa-widget--closed";

        // Botón de chat (visible cuando está cerrado)
        const chatButton = document.createElement("button");
        chatButton.className = "siacasa-widget__button";
        chatButton.innerHTML = `
            <span class="siacasa-widget__icon">
                ${iconSet.chat}
            </span>
            <span class="siacasa-widget__label">Asistente</span>
        `;

        // Panel de chat (oculto inicialmente)
        const chatPanel = document.createElement("div");
        chatPanel.className = "siacasa-widget__panel";
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

    // ======== MANEJO DE SESIÓN ========

    /**
     * Inicializa el control de sesiones
     */
    function initSessionHandling() {
        // Recuperar ID de usuario existente o crear uno nuevo
        sessionId = localStorage.getItem("siacasa_session_id");
        if (!sessionId) {
            sessionId = generateUUID();
            localStorage.setItem("siacasa_session_id", sessionId);
        }
        console.log("Usando ID de sesión:", sessionId);

        // Configurar reinicio de temporizador de inactividad en cada acción del usuario
        document.addEventListener("click", resetInactivityTimer);
        document.addEventListener("keypress", resetInactivityTimer);

        // Manejar cierre de página
        window.addEventListener("beforeunload", handleBeforeUnload);
    }

    /**
     * Resetea el temporizador de inactividad
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
                fetch(config.apiEndpoint.replace("/mensaje", "/finalizar-sesion"), {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        usuario_id: sessionId,
                    }),
                })
                    .then((response) => response.json())
                    .then((data) => {
                        console.log("Sesión finalizada por inactividad:", currentSessionId);
                        currentSessionId = null;
                    })
                    .catch((error) => {
                        console.error("Error al finalizar sesión por inactividad:", error);
                    });
            }
        }, INACTIVITY_TIMEOUT);
    }

    /**
     * Maneja el evento beforeunload para finalizar la sesión
     */
    function handleBeforeUnload() {
        if (sessionId && currentSessionId) {
            const data = JSON.stringify({
                usuario_id: sessionId,
            });

            // Crear un Blob con el tipo MIME correcto
            const blob = new Blob([data], {
                type: "application/json",
            });

            // Usar sendBeacon con el Blob
            navigator.sendBeacon(
                config.apiEndpoint.replace("/mensaje", "/finalizar-sesion"),
                blob
            );

            console.log("Sesión finalizada al cerrar página:", currentSessionId);
        }
    }

    // ======== SOCKET.IO ========

    /**
     * Inicializa la conexión Socket.IO
     */
    function initSocketConnection() {
        try {
            // Verificar si io está definido
            if (typeof io === "undefined") {
                console.warn("La biblioteca Socket.IO no está disponible");
                return;
            }

            // Construir la URL del servidor Socket.IO
            const socketUrl = `${window.location.protocol}//${serverHost}:${serverPort}`;
            console.log(`Conectando a Socket.IO: ${socketUrl}`);

            // Inicializar Socket.IO
            socket = io(socketUrl, {
                transports: ["websocket", "polling"],
                reconnection: true,
                reconnectionAttempts: 5,
                reconnectionDelay: 1000,
                timeout: 20000,
            });
            console.log('Socket.IO inicializado:', socket);
            // Configurar eventos
            setupSocketEvents();
        } catch (error) {
            console.error("Error al inicializar Socket.IO:", error);
        }
    }

    /**
     * Configura los eventos de Socket.IO
     */
    function setupSocketEvents() {
        console.log('Configurando eventos Socket.IO');
        if (!socket) return;

        socket.on("connect", () => {
            console.log("Conectado a Socket.IO con ID:", socket.id);

            // Si hay un ticket activo, suscribirse inmediatamente
            if (activeTicketId) {
                console.log(`Suscripción al ticket: ${activeTicketId}`);
                socket.emit("subscribe_ticket", {
                    ticket_id: activeTicketId,
                    role: "user",
                });
            }
            console.log("Estado de conexión:", socket.connected ? "Conectado" : "Desconectado");

            // Guardar que estamos conectados
            sessionStorage.setItem('socketConnected', 'true');

            // Si hay un ticket activo, suscribirse inmediatamente después de reconexión
            if (activeTicketId) {
                console.log(`Suscripción al ticket: ${activeTicketId}`);
                setTimeout(() => {
                    socket.emit("subscribe_ticket", {
                        ticket_id: activeTicketId,
                        role: "user",
                    });
                }, 500); // Pequeño retraso para asegurar que la conexión esté estable
            }

            // Suscribirse como usuario
            console.log(`Suscripción como usuario: ${sessionId}`);
            setTimeout(() => {
                socket.emit("subscribe_user", {
                    user_id: sessionId,
                });
            }, 300); // Retraso aún mayor para esta operación
        });

        socket.on("disconnect", () => {
            console.log("Desconectado de Socket.IO");
        });

        socket.on("connect_error", (error) => {
            console.error("Error de conexión Socket.IO:", error);
        });

    

        // Manejador para mensajes de chat generales
        socket.on('chat_message', function(data) {
            console.log('Mensaje recibido por socket:', data);
            
            // Si el mensaje es de un agente y no es interno, mostrarlo en el chat
            if (data.sender_type === 'agent' && !data.is_internal) {
                hideTypingIndicator();
                addMessageToChat(
                    data.content, 
                    'assistant', 
                    data.sender_name || 'Agente',
                    new Date(data.timestamp)
                );
            }
        });

        // Manejador para mensajes directos
        socket.on('direct_message', function (data) {
            console.log('Mensaje directo recibido:', data);

            // Si el mensaje es de un agente y no es interno, mostrarlo en el chat
            if (data.sender_type === 'agent' && !data.is_internal) {
                hideTypingIndicator();
                addMessageToChat(
                    data.content, 
                    'assistant', 
                    data.sender_name || 'Agente',
                    new Date(data.timestamp)
                );
            }
        });

        // Manejador para mensajes del widget
        socket.on('widget_message', function(data) {
            console.log('Mensaje de widget recibido:', data);
            
            // Verificar si este mensaje es para este usuario
            if (data.user_id === sessionId) {
                console.log("Mensaje recibido del agente:", data.message);
                
                // Si el mensaje no es interno, mostrarlo en el chat
                if (data.message && !data.message.is_internal) {
                    hideTypingIndicator();
                    addMessageToChat(
                        data.message.content, 
                        'assistant', 
                        data.message.sender_name || 'Agente',
                        new Date(data.message.timestamp)
                    );
                }
            }
        });


        

        socket.on("typing", (data) => {
            if (data.sender_type === "agent" && data.is_typing) {
                showTypingIndicator();
            } else {
                hideTypingIndicator();
            }
        });

        socket.on('agent_connected', function (data) {
            console.log('Agente conectado al ticket:', data);
            // Opcionalmente mostrar mensaje al usuario
            addMessageToChat('Un agente se ha conectado a la conversación.', false, 'Agente', new Date(data.message.timestamp));
        });

        socket.on('error', function (error) {
            console.error('Error en Socket.IO:', error);
        });

        socket.on('reconnect', function () {
            console.log('Socket.IO reconectado');

            // Volver a suscribirse al ticket si teníamos uno activo
            if (activeTicketId) {
                console.log('Volviendo a suscribirse al ticket:', activeTicketId);
                socket.emit('subscribe_ticket', {
                    ticket_id: activeTicketId,
                    role: 'user'
                });
            }

            // También volver a suscribirse como usuario
            socket.emit('subscribe_user', {
                user_id: sessionId
            });
        });

    }

    // ======== FUNCIONES PRINCIPALES ========


    /**
     * Añade un mensaje al chat
     * @param {string} content - Contenido del mensaje
     * @param {string|boolean} role - Rol del mensaje ('user', 'assistant') o booleano (true=user, false=assistant)
     * @param {string} senderName - Nombre del remitente (opcional)
     * @param {Date} timestamp - Marca de tiempo (opcional)
     */
    async function addMessageToChat(content, role, senderName, timestamp) {
        try {
            // Determinar el rol correcto (manejar tanto string como boolean)
            let messageRole = role;
            if (typeof role === 'boolean') {
                messageRole = role ? 'user' : 'assistant';
            }

            // Obtener el contenedor de mensajes
            const messagesContainer = document.getElementById('siacasaMessages');
            if (!messagesContainer) {
                console.error('Contenedor de mensajes no encontrado');
                return;
            }

            // Crear elemento para el mensaje
            const messageElement = document.createElement('div');
            messageElement.className = `siacasa-message siacasa-message--${messageRole === 'user' ? 'user' : 'bot'}`;

            // Formatear fecha si existe, o usar hora actual
            const time = timestamp ? new Date(timestamp) : new Date();
            const timeFormatted = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            // Determinar nombre del remitente si no se proporciona
            const name = senderName || (messageRole === 'user' ? 'Tú' : config.botName);

            // Procesar markdown si el mensaje es del bot
            let processedContent = content;
            if (messageRole === 'assistant' || messageRole === 'bot' || messageRole === false) {
                if (window.marked && window.DOMPurify) {
                    processedContent = window.DOMPurify.sanitize(window.marked.parse(content));
                } else {
                    processedContent = processMarkdownSimple(content);
                }
            }

            // Estructura del mensaje
            messageElement.innerHTML = `
                ${processedContent}
                <div class="siacasa-message__time">${timeFormatted}</div>
            `;

            // Añadir al contenedor
            messagesContainer.appendChild(messageElement);

            // Scroll al final del chat
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

        } catch (error) {
            console.error('Error al añadir mensaje al chat:', error);
        }
    }

    /**
     * Función para ocultar el indicador de escritura
     */
    function hideTypingIndicator() {
        const typingIndicator = document.getElementById('siacasaTyping');
        if (typingIndicator) {
            typingIndicator.style.display = 'none';
        }
    }

    /**
     * Función para mostrar el indicador de escritura
     */
    function showTypingIndicator() {
        const typingIndicator = document.getElementById('siacasaTyping');
        if (typingIndicator) {
            typingIndicator.style.display = 'flex';
            // Asegurar que se vea al hacer scroll
            const messagesContainer = document.getElementById('siacasaMessages');
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    }

    /**
     * Envía un mensaje al backend
     * @param {string} message - Mensaje a enviar
     */
    async function sendMessage(message) {
        try {
            showTypingIndicator();

            // Determinar banco según dominio
            const bankCode = getBankCode();

            // Intentar enviar por Socket.IO primero si está disponible
            if (socket && socket.connected && activeTicketId) {
                console.log("Enviando mensaje por Socket.IO");
                socket.emit("chat_message", {
                    ticket_id: activeTicketId,
                    content: message,
                    sender_id: sessionId,
                    sender_type: "user",
                });

                // El mensaje del agente será recibido por el evento 'chat_message'
                return;
            }

            // Fallback a método HTTP si Socket.IO no está disponible
            const response = await fetch(config.apiEndpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    mensaje: message,
                    usuario_id: sessionId,
                    bank_code: bankCode,
                }),
            });

            const data = await response.json();

            hideTypingIndicator();

            if (data.status === "success") {
                await addMessageToChat(data.respuesta, 'assistant', data.sender_name, new Date(data.timestamp));

                // Si la respuesta incluye un ID de usuario, actualizarlo
                if (data.usuario_id) {
                    sessionId = data.usuario_id;
                    localStorage.setItem("siacasa_session_id", sessionId);
                }

                // Si hay un ticket asignado, guardarlo
                if (data.ticket_id && !activeTicketId) {
                    activeTicketId = data.ticket_id;
                    console.log(`Ticket ID asignado: ${activeTicketId}`);
                    localStorage.setItem("siacasa_active_ticket", activeTicketId);
                    // Suscribirse al ticket si Socket.IO está disponible
                    if (socket && socket.connected) {
                        socket.emit("subscribe_ticket", {
                            ticket_id: activeTicketId,
                            role: "user",
                        });
                    }
                }
            } else {
                throw new Error(data.error || "Error desconocido");
            }
        } catch (error) {
            console.error("Error en la comunicación con el chatbot:", error);
            hideTypingIndicator();
            await addMessageToChat(
                "Lo siento, ha ocurrido un error en la comunicación. Por favor, intenta de nuevo más tarde.",
                'assistant',
                'Asistente',
                new Date()
            );
        }
    }

    /**
     * Realiza polling para nuevos mensajes
     */
    function pollForNewMessages() {
        if (!sessionId || !activeTicketId) return;

        // Solo hacer polling si Socket.IO no está disponible
        if (socket && socket.connected) return;

        console.log(
            `Realizando polling de mensajes. Último mensaje: ${lastMessageTimestamp}`
        );

        fetch(
            `/api/mensajes?usuario_id=${sessionId}&ticket_id=${activeTicketId}&ultimo_mensaje=${lastMessageTimestamp}`
        )
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Error de servidor: ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                if (
                    data.status === "success" &&
                    data.mensajes &&
                    Array.isArray(data.mensajes)
                ) {
                    console.log(
                        `Polling: ${data.mensajes.length} mensajes nuevos encontrados`
                    );

                    data.mensajes.forEach(async (msg) => {
                        // Solo procesar mensajes que no hemos mostrado antes
                        const msgTimestamp = new Date(msg.timestamp).getTime();
                        if (msgTimestamp > lastMessageTimestamp) {
                            if (msg.sender_type === "agent") {
                                await addMessageToChat(msg.content, false);
                            }

                            // Actualizar timestamp del último mensaje
                            lastMessageTimestamp = msgTimestamp;
                        }
                    });
                }
            })
            .catch((error) => {
                console.warn("Error en polling de mensajes:", error);
            });
    }

    // ======== INICIALIZACIÓN ========

    /**
     * Inicializa el widget
     */
    async function initWidget() {
        try {
            // Recuperar o generar sessionId
            sessionId = localStorage.getItem("siacasa_session_id");
            if (!sessionId) {
                sessionId = generateUUID();
                localStorage.setItem("siacasa_session_id", sessionId);
            }

            // Recuperar ticket activo si existe
            activeTicketId = localStorage.getItem("siacasa_active_ticket");
            if (activeTicketId) {
                console.log(`Recuperado ticket activo: ${activeTicketId}`);
            }

            // Añadir estilos
            addStyles();

            // Crear y añadir el widget al DOM
            const widget = createChatWidget();
            document.body.appendChild(widget);

            // Obtener elementos del DOM
            messagesContainer = document.getElementById("siacasaMessages");
            typingIndicator = document.getElementById("siacasaTyping");
            const chatButton = widget.querySelector(".siacasa-widget__button");
            const closeButton = widget.querySelector(".siacasa-widget__close");
            const backButton = widget.querySelector(".siacasa-widget__back");
            const sendButton = document.getElementById("siacasaSend");
            const inputField = document.getElementById("siacasaInput");

            // Clave única para localStorage basada en el usuario y el día
            const todayKey = new Date().toISOString().split("T")[0]; // Formato: YYYY-MM-DD
            const storageKey = `siacasa_greeted_${sessionId}_${todayKey}`;

            // Verificar si ya se mostró el mensaje inicial hoy para esta sesión
            const wasGreetedToday = localStorage.getItem(storageKey);

            if (!wasGreetedToday) {
                // Añadir mensaje inicial del bot
                await addMessageToChat(config.initialMessage, false);
                // Guardar en localStorage que ya se mostró el mensaje
                localStorage.setItem(storageKey, "true");
            } else {
                // Verificar si hay mensajes anteriores en el historial
                const hasMessages = messagesContainer.children.length > 0;
                // Si no hay mensajes (primera vez que se abre), mostrar mensaje inicial
                if (!hasMessages) {
                    await addMessageToChat(config.initialMessage, false);
                }
            }

            // Abrir chat
            chatButton.addEventListener("click", () => {
                widget.classList.remove("siacasa-widget--closed");
                // Focus en el input cuando se abre el chat
                setTimeout(() => inputField.focus(), 300);
            });

            // Cerrar chat
            closeButton.addEventListener("click", () => {
                widget.classList.add("siacasa-widget--closed");
            });

            // Botón atrás (igual que cerrar en versión móvil)
            backButton.addEventListener("click", () => {
                widget.classList.add("siacasa-widget--closed");
            });

            // Manejar envío de mensaje
            function handleSendMessage() {
                const message = inputField.value.trim();
                if (!message) return;

                // Añadir mensaje del usuario
                addMessageToChat(message, 'user', 'Tú', new Date());

                // Limpiar campo de entrada
                inputField.value = "";

                // Ajustar altura del input a su tamaño por defecto
                inputField.style.height = 'auto';

                // Enviar mensaje al backend
                sendMessage(message);

                // Reiniciar temporizador de inactividad
                resetInactivityTimer();
            }

            // Eventos de envío
            sendButton.addEventListener("click", handleSendMessage);

            inputField.addEventListener("keypress", (e) => {
                if (e.key === "Enter") {
                    handleSendMessage();
                }
            });

            // Inicializar manejo de sesión
            initSessionHandling();

            // Cargar Socket.IO y luego inicializar la conexión
            try {
                loadLibrary("https://cdn.socket.io/4.6.0/socket.io.min.js", {
                    checkGlobal: "io",
                    integrity:
                        "sha384-c79GN5VsunZvi+Q/WObgk2in0CbZsHnjEqvFxC5DxHn9lTfNce2WW6h2pH6u/kF+",
                    fallbackUrl: "https://cdn.socket.io/4.6.0/socket.io.min.js",
                })
                    .then(() => {
                        initSocketConnection();
                    })
                    .catch((err) => {
                        console.warn(
                            "No se pudo cargar Socket.IO, usando polling fallback"
                        );
                    });
            } catch (error) {
                console.warn("Error al cargar Socket.IO:", error);
            }

            // Iniciar polling para nuevos mensajes
            setInterval(pollForNewMessages, POLLING_INTERVAL);

            // Exponer funciones útiles al ámbito global para debugging o extensibilidad
            window.__siacasa_widget = {
                addMessageToChat,
                showTypingIndicator,
                hideTypingIndicator,
                sendMessage,
            };

            // Disparar evento de widget cargado
            const widgetLoadedEvent = new CustomEvent("siacasa-widget-loaded");
            window.dispatchEvent(widgetLoadedEvent);

            console.log("Widget inicializado correctamente");
        } catch (error) {
            console.error("Error al inicializar el widget:", error);
        }
    }

    // Esperar a que el DOM esté cargado por completo
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initWidget);
    } else {
        // Pequeño retraso para asegurar que todo esté configurado
        setTimeout(initWidget, 100);
    }
})();
