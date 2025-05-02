/**
 * admin_panel/static/js/support.js
 * 
 * JavaScript para la funcionalidad del módulo de soporte
 */

(function() {
    'use strict';
    
    // Comprobar si estamos en una página de soporte
    const isSupportPage = document.querySelector('.support-page') !== null;
    if (!isSupportPage) return;
    
    // Variables globales
    let socket = null;
    let reconnectInterval = null;
    let pendingTickets = [];
    let assignedTickets = [];
    let notificationSound = null;
    
    // Inicializar cuando el DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        // Inicializar componentes
        initializeUI();
        loadSoundEffects();
        
        // Inicializar WebSocket si estamos en la página de chat en vivo
        if (document.querySelector('.live-chat-page')) {
            initializeWebSocket();
        }
        
        // Actualizar tickets periódicamente
        if (document.querySelector('.support-dashboard')) {
            setInterval(updateTicketLists, 30000); // Cada 30 segundos
        }
    });
    
    /**
     * Inicializa los elementos de la interfaz de usuario
     */
    function initializeUI() {
        // Inicializar tooltips de Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Inicializar popover de Bootstrap
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
        
        // Inicializar plantillas de respuesta
        initializeResponseTemplates();
        
        // Inicializar formulario de chat
        initializeChatForm();
        
        // Inicializar notificaciones de desktop
        requestNotificationPermission();
    }
    
    /**
     * Carga los efectos de sonido
     */
    function loadSoundEffects() {
        // Crear elemento de audio para notificaciones
        notificationSound = new Audio('/static/sounds/alert.wav');
        
        // Precargar sonido
        notificationSound.load();
    }
    
    /**
     * Inicializa las plantillas de respuesta rápida
     */
    function initializeResponseTemplates() {
        const templateItems = document.querySelectorAll('.response-template-item');
        const messageInput = document.getElementById('messageInput');
        
        if (!templateItems || !messageInput) return;
        
        templateItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Obtener texto de la plantilla
                const templateText = this.getAttribute('data-template');
                
                // Insertar en el input
                messageInput.value = templateText;
                messageInput.focus();
            });
        });
    }
    
    /**
     * Inicializa el formulario de chat
     */
    function initializeChatForm() {
        const messageForm = document.getElementById('messageForm');
        const messageInput = document.getElementById('messageInput');
        
        if (!messageForm || !messageInput) return;
        
        // Auto-resize del textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Enviar con Ctrl+Enter
        messageInput.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                messageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
    
    /**
     * Inicializa la conexión WebSocket
     */
    function initializeWebSocket() {
        // Obtener información del WebSocket de los atributos data
        const chatContainer = document.querySelector('.live-chat-container');
        if (!chatContainer) return;
        
        const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsHost = chatContainer.getAttribute('data-ws-host');
        const wsPort = chatContainer.getAttribute('data-ws-port');
        const ticketId = chatContainer.getAttribute('data-ticket-id');
        const agentId = chatContainer.getAttribute('data-agent-id');
        const agentName = chatContainer.getAttribute('data-agent-name');
        
        if (!wsHost || !wsPort || !ticketId || !agentId) {
            console.error('Faltan datos para la conexión WebSocket');
            return;
        }
        
        const wsUrl = `${wsProtocol}${wsHost}:${wsPort}`;
        
        // Conectar WebSocket
        connectWebSocket(wsUrl, ticketId, agentId, agentName);
    }
    
    /**
     * Conecta al servidor WebSocket
     */
    function connectWebSocket(url, ticketId, agentId, agentName) {
        try {
            socket = new WebSocket(url);
            
            socket.onopen = function() {
                console.log('WebSocket conectado');
                
                // Limpiar intervalo de reconexión
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
                
                // Suscribirse al ticket
                socket.send(JSON.stringify({
                    type: 'subscribe_ticket',
                    ticket_id: ticketId,
                    role: 'agent'
                }));
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data, ticketId, agentId, agentName);
            };
            
            socket.onclose = function() {
                console.log('WebSocket desconectado');
                
                // Intentar reconectar
                if (!reconnectInterval) {
                    reconnectInterval = setInterval(function() {
                        console.log('Intentando reconectar WebSocket...');
                        connectWebSocket(url, ticketId, agentId, agentName);
                    }, 5000);
                }
            };
            
            socket.onerror = function(error) {
                console.error('Error en WebSocket:', error);
            };
        } catch (error) {
            console.error('Error al conectar WebSocket:', error);
        }
    }
    
    /**
     * Maneja mensajes recibidos por el WebSocket
     */
    function handleWebSocketMessage(data, ticketId, agentId, agentName) {
        // Verificar tipo de mensaje
        switch (data.type) {
            case 'welcome':
                console.log('Conexión exitosa al WebSocket', data);
                break;
                
            case 'subscription_confirmed':
                console.log('Suscripción confirmada al ticket', data);
                break;
                
            case 'chat_message':
                // Procesar mensaje de chat
                handleChatMessage(data, agentId);
                break;
                
            case 'typing':
                // Procesar indicador de escritura
                handleTypingIndicator(data);
                break;
                
            case 'error':
                console.error('Error en el WebSocket:', data.message);
                break;
                
            default:
                console.log('Mensaje no manejado:', data);
                break;
        }
    }
    
    /**
     * Maneja mensajes de chat recibidos
     */
    function handleChatMessage(data, currentAgentId) {
        // Ignorar mensajes propios
        if (data.sender_id === currentAgentId) return;
        
        // Obtener contenedor de mensajes
        const chatHistory = document.getElementById('chatHistory');
        if (!chatHistory) return;
        
        // Crear elemento de mensaje
        const messageBlock = document.createElement('div');
        
        // Determinar tipo de mensaje
        let messageClass = '';
        let avatarClass = '';
        let avatarIcon = '';
        let senderName = data.sender_name || 'Desconocido';
        
        if (data.sender_type === 'user') {
            messageClass = 'message-user';
            avatarClass = 'bg-light text-dark';
            avatarIcon = 'fas fa-user';
            senderName = 'Usuario';
        } else if (data.is_internal) {
            messageClass = 'message-internal';
            avatarClass = 'bg-warning text-dark';
            avatarIcon = 'fas fa-exclamation-triangle';
        } else {
            messageClass = 'message-agent';
            avatarClass = 'bg-primary text-white';
            avatarIcon = 'fas fa-headset';
        }
        
        // Formatear hora
        const timestamp = new Date(data.timestamp);
        const timeString = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Construir HTML del mensaje
        messageBlock.className = `message-block ${messageClass} mb-3`;
        messageBlock.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="message-avatar ${avatarClass}">
                    <i class="${avatarIcon}"></i>
                </div>
                
                <div class="message-content ms-3 flex-grow-1">
                    <div class="message-header d-flex justify-content-between align-items-center mb-1">
                        <div class="message-sender fw-bold">
                            ${senderName}
                            ${data.is_internal ? '<span class="badge bg-warning ms-2">Nota interna</span>' : ''}
                        </div>
                        <div class="message-time small text-muted">
                            ${timeString}
                        </div>
                    </div>
                    
                    <div class="message-body p-3 rounded">
                        ${data.content.replace(/\n/g, '<br>')}
                    </div>
                </div>
            </div>
        `;
        
        // Añadir mensaje al chat
        chatHistory.appendChild(messageBlock);
        
        // Scroll hacia abajo
        scrollChatToBottom();
        
        // Reproducir sonido de notificación
        if (notificationSound) {
            notificationSound.play().catch(error => {
                console.log('No se pudo reproducir el sonido de notificación', error);
            });
        }
        
        // Mostrar notificación de escritorio
        if (data.sender_type === 'user') {
            showDesktopNotification('Nuevo mensaje', `El usuario ha enviado un mensaje: "${data.content.substring(0, 50)}${data.content.length > 50 ? '...' : ''}"`);
        }
    }
    
    /**
     * Maneja el indicador de escritura
     */
    function handleTypingIndicator(data) {
        // Solo procesar indicadores de usuario
        if (data.sender_type !== 'user') return;
        
        // Obtener indicador de escritura
        const typingIndicator = document.getElementById('typingIndicator');
        if (!typingIndicator) return;
        
        // Mostrar u ocultar según corresponda
        if (data.is_typing) {
            typingIndicator.classList.remove('d-none');
            scrollChatToBottom();
        } else {
            typingIndicator.classList.add('d-none');
        }
    }
    
    /**
     * Actualiza las listas de tickets
     */
    function updateTicketLists() {
        // Actualizar tickets pendientes
        fetch('/support/api/tickets/pending')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updatePendingTickets(data.tickets);
                }
            })
            .catch(error => {
                console.error('Error al actualizar tickets pendientes:', error);
            });
        
        // Actualizar tickets asignados
        fetch('/support/api/tickets/assigned')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateAssignedTickets(data.tickets);
                }
            })
            .catch(error => {
                console.error('Error al actualizar tickets asignados:', error);
            });
    }
    
    /**
     * Actualiza la lista de tickets pendientes
     */
    function updatePendingTickets(tickets) {
        const pendingTicketsContainer = document.getElementById('pendingTickets');
        if (!pendingTicketsContainer) return;
        
        // Comparar con la lista actual para detectar nuevos tickets
        const newTickets = tickets.filter(ticket => {
            return !pendingTickets.some(existingTicket => existingTicket.id === ticket.id);
        });
        
        // Actualizar lista interna
        pendingTickets = tickets;
        
        // Mostrar notificaciones para nuevos tickets
        if (newTickets.length > 0) {
            // Reproducir sonido de notificación
            if (notificationSound) {
                notificationSound.play().catch(error => {
                    console.log('No se pudo reproducir el sonido de notificación', error);
                });
            }
            
            // Mostrar notificación de escritorio
            showDesktopNotification(
                'Nuevos tickets pendientes',
                `Hay ${newTickets.length} nuevo${newTickets.length > 1 ? 's' : ''} ticket${newTickets.length > 1 ? 's' : ''} pendiente${newTickets.length > 1 ? 's' : ''}`
            );
            
            // Actualizar contador
            const pendingCounter = document.getElementById('pendingCounter');
            if (pendingCounter) {
                pendingCounter.textContent = tickets.length;
            }
            
            // Actualizar lista en la interfaz
            renderTicketList(pendingTicketsContainer, tickets, 'pending');
        }
    }
    
    /**
     * Actualiza la lista de tickets asignados
     */
    function updateAssignedTickets(tickets) {
        const assignedTicketsContainer = document.getElementById('assignedTickets');
        if (!assignedTicketsContainer) return;
        
        // Comparar con la lista actual para detectar cambios
        const ticketsChanged = tickets.length !== assignedTickets.length || 
            tickets.some(ticket => {
                const existingTicket = assignedTickets.find(t => t.id === ticket.id);
                return !existingTicket || existingTicket.estado !== ticket.estado;
            });
        
        // Actualizar lista interna
        assignedTickets = tickets;
        
        // Actualizar contador
        const assignedCounter = document.getElementById('assignedCounter');
        if (assignedCounter) {
            assignedCounter.textContent = tickets.length;
        }
        
        // Actualizar lista en la interfaz si hay cambios
        if (ticketsChanged) {
            renderTicketList(assignedTicketsContainer, tickets, 'assigned');
        }
    }
    
    /**
     * Renderiza una lista de tickets
     */
    function renderTicketList(container, tickets, type) {
        // Limpiar contenedor
        container.innerHTML = '';
        
        // Verificar si hay tickets
        if (tickets.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="mb-3">
                        <i class="fas fa-${type === 'pending' ? 'check-circle' : 'inbox'} fa-3x text-muted"></i>
                    </div>
                    <h5 class="text-muted">No hay tickets ${type === 'pending' ? 'pendientes' : 'asignados'}</h5>
                    <p class="text-muted">
                        ${type === 'pending' 
                            ? '¡Todos los tickets han sido atendidos!' 
                            : 'Puedes tomar tickets pendientes de la lista de la izquierda'}
                    </p>
                </div>
            `;
            return;
        }
        
        // Crear tabla
        const table = document.createElement('div');
        table.className = 'table-responsive';
        table.innerHTML = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Usuario</th>
                        <th>${type === 'pending' ? 'Creado' : 'Estado'}</th>
                        <th>${type === 'pending' ? 'Prioridad' : 'Asignado'}</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody id="${type}TicketsList">
                </tbody>
            </table>
        `;
        
        container.appendChild(table);
        
        // Obtener tbody
        const tbody = document.getElementById(`${type}TicketsList`);
        
        // Añadir tickets
        tickets.forEach(ticket => {
            const tr = document.createElement('tr');
            
            // Formatear fechas
            const creationDate = new Date(ticket.fecha_creacion);
            const assignmentDate = ticket.fecha_asignacion ? new Date(ticket.fecha_asignacion) : null;
            
            // Crear HTML según tipo
            if (type === 'pending') {
                tr.innerHTML = `
                    <td><a href="/support/tickets/${ticket.id}" class="fw-bold">#${ticket.id.substring(0, 8)}</a></td>
                    <td>${ticket.usuario_nombre || 'Usuario ' + ticket.usuario_id.substring(0, 8)}</td>
                    <td>${formatDate(creationDate)}</td>
                    <td>
                        ${getPriorityBadge(ticket.prioridad)}
                    </td>
                    <td>
                        <div class="btn-group">
                            <a href="/support/tickets/${ticket.id}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-eye"></i>
                            </a>
                            <a href="/support/tickets/${ticket.id}/live-chat" class="btn btn-sm btn-success">
                                <i class="fas fa-comments"></i> Atender
                            </a>
                        </div>
                    </td>
                `;
            } else {
                tr.innerHTML = `
                    <td><a href="/support/tickets/${ticket.id}" class="fw-bold">#${ticket.id.substring(0, 8)}</a></td>
                    <td>${ticket.usuario_nombre || 'Usuario ' + ticket.usuario_id.substring(0, 8)}</td>
                    <td>
                        ${getStatusBadge(ticket.estado)}
                    </td>
                    <td>${assignmentDate ? formatDate(assignmentDate) : '-'}</td>
                    <td>
                        <div class="btn-group">
                            <a href="/support/tickets/${ticket.id}" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-eye"></i>
                            </a>
                            <a href="/support/tickets/${ticket.id}/live-chat" class="btn btn-sm btn-primary">
                                <i class="fas fa-comments"></i> Chat
                            </a>
                        </div>
                    </td>
                `;
            }
            
            tbody.appendChild(tr);
        });
    }
    
    /**
     * Formatea una fecha
     */
    function formatDate(date) {
        return date.toLocaleString();
    }
    
    /**
     * Obtiene un badge HTML para el estado
     */
    function getStatusBadge(status) {
        switch (status) {
            case 'pending':
                return '<span class="badge bg-warning">Pendiente</span>';
            case 'assigned':
                return '<span class="badge bg-info">Asignado</span>';
            case 'active':
                return '<span class="badge bg-primary">Activo</span>';
            case 'resolved':
                return '<span class="badge bg-success">Resuelto</span>';
            case 'closed':
                return '<span class="badge bg-secondary">Cerrado</span>';
            default:
                return '<span class="badge bg-secondary">' + status + '</span>';
        }
    }
    
    /**
     * Obtiene un badge HTML para la prioridad
     */
    function getPriorityBadge(priority) {
        switch (priority) {
            case 5:
                return '<span class="badge bg-danger">Urgente</span>';
            case 4:
                return '<span class="badge bg-warning">Alta</span>';
            case 3:
                return '<span class="badge bg-primary">Media</span>';
            case 2:
                return '<span class="badge bg-info">Baja</span>';
            case 1:
            default:
                return '<span class="badge bg-secondary">Normal</span>';
        }
    }
    
    /**
     * Solicita permiso para mostrar notificaciones de escritorio
     */
    function requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('Este navegador no soporta notificaciones de escritorio');
            return;
        }
        
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
    
    /**
     * Muestra una notificación de escritorio
     */
    function showDesktopNotification(title, message) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const notification = new Notification(title, {
            body: message,
            icon: '/static/img/bn_logo.png'
        });
        
        // Cerrar automáticamente después de 5 segundos
        setTimeout(function() {
            notification.close();
        }, 5000);
        
        // Enfocar ventana al hacer clic
        notification.onclick = function() {
            window.focus();
            this.close();
        };
    }
    
    /**
     * Hace scroll al final del chat
     */
    function scrollChatToBottom() {
        const chatHistory = document.getElementById('chatHistory');
        if (chatHistory) {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    }
    
    // Exponer funciones útiles globalmente
    window.supportApp = {
        updateTicketLists,
        scrollChatToBottom
    };
})();