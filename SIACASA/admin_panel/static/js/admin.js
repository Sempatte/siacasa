/**
 * admin.js - Funciones JavaScript para el panel de administración SIACASA
 * 
 * Este archivo contiene las funcionalidades principales para el panel de administración
 * incluyendo gráficos, animaciones y efectos visuales.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Variables globales
    const body = document.body;
    const sidebarToggle = document.getElementById('sidebar-toggle');

    // Funciones para sidebar
    initSidebar();
    
    // Inicializar tooltips de Bootstrap
    initTooltips();
    
    // Comprobar si es pantalla pequeña para colapsar sidebar
    checkScreenSize();
    
    // Event listeners para ventana
    window.addEventListener('resize', checkScreenSize);

    /**
     * Inicializa el comportamiento del sidebar
     */
    function initSidebar() {
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', function() {
                body.classList.toggle('sidebar-collapsed');
                
                // Guardar estado en localStorage
                localStorage.setItem('sidebarCollapsed', body.classList.contains('sidebar-collapsed'));
            });
        }
        
        // Restaurar estado del sidebar desde localStorage
        const sidebarState = localStorage.getItem('sidebarCollapsed');
        if (sidebarState === 'true') {
            body.classList.add('sidebar-collapsed');
        }
    }
    
    /**
     * Inicializa los tooltips de Bootstrap
     */
    function initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    /**
     * Verifica el tamaño de la pantalla y colapsa el sidebar en pantallas pequeñas
     */
    function checkScreenSize() {
        if (window.innerWidth < 992) {
            body.classList.add('sidebar-collapsed');
        } else {
            // En pantallas grandes, restaurar preferencias del usuario
            const sidebarState = localStorage.getItem('sidebarCollapsed');
            if (sidebarState === 'true') {
                body.classList.add('sidebar-collapsed');
            } else if (sidebarState === 'false') {
                body.classList.remove('sidebar-collapsed');
            }
        }
    }
    
    /**
     * Inicializa efectos visuales para cards y elementos
     */
    function initVisualEffects() {
        // Animación para tarjetas dashboard al entrar en viewport
        const dashboardCards = document.querySelectorAll('.dashboard-card');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate__animated', 'animate__fadeInUp');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });
        
        dashboardCards.forEach(card => {
            observer.observe(card);
        });
    }
    
    // Comprobar si existe algún chart en la página
    if (document.querySelector('[data-chart]')) {
        // Cargar Chart.js dinámicamente para ahorrar recursos
        loadChartJs();
    }
    
    /**
     * Carga Chart.js dinámicamente
     */
    function loadChartJs() {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
        script.onload = initializeCharts;
        document.head.appendChild(script);
    }
    
    /**
     * Inicializa todos los gráficos en la página
     */
    function initializeCharts() {
        const chartElements = document.querySelectorAll('[data-chart]');
        
        chartElements.forEach(element => {
            const type = element.getAttribute('data-chart');
            const dataUrl = element.getAttribute('data-chart-url');
            
            if (dataUrl) {
                // Cargar datos desde URL
                fetch(dataUrl)
                    .then(response => response.json())
                    .then(data => {
                        createChart(element, type, data);
                    })
                    .catch(error => {
                        console.error('Error al cargar datos para el gráfico:', error);
                    });
            } else {
                // Datos embebidos en el atributo data-chart-data
                const dataString = element.getAttribute('data-chart-data');
                if (dataString) {
                    try {
                        const data = JSON.parse(dataString);
                        createChart(element, type, data);
                    } catch (error) {
                        console.error('Error al parsear datos del gráfico:', error);
                    }
                }
            }
        });
    }
    
    /**
     * Crea un gráfico con Chart.js
     */
    function createChart(element, type, data) {
        const ctx = element.getContext('2d');
        
        // Configuración común
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            family: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
                            size: 12
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    padding: 10,
                    titleFont: {
                        family: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
                        size: 14
                    },
                    bodyFont: {
                        family: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
                        size: 13
                    },
                    cornerRadius: 6
                }
            }
        };
        
        // Configuración específica según tipo de gráfico
        switch(type) {
            case 'line':
                options.scales = {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                };
                break;
                
            case 'bar':
                options.scales = {
                    y: {
                        beginAtZero: true,
                        grid: {
                            drawBorder: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                };
                break;
                
            case 'pie':
            case 'doughnut':
                options.cutout = '50%';
                break;
        }
        
        // Crear el gráfico
        new Chart(ctx, {
            type: type,
            data: data,
            options: options
        });
    }
    
    // Inicializar formularios de datos
    /**
     * Inicializa el comportamiento de formularios
     */
    function initForms() {
        // Prevenir envío doble de formularios
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                // Verificar si es un formulario de chat y si estamos usando Socket.IO
                const isChatForm = form.id === 'messageForm';
                const isSocketAvailable = window.socket && window.socket.connected;
                
                // Si es un formulario de chat y Socket.IO está disponible, manejar de forma especial
                if (isChatForm && isSocketAvailable) {
                    e.preventDefault();
                    
                    // Obtener datos del mensaje
                    const messageInput = document.getElementById('messageInput');
                    const message = messageInput.value.trim();
                    const isInternal = document.getElementById('internalMessage')?.checked || false;
                    
                    if (!message) return;
                    
                    // Obtener información del ticket y del agente
                    const ticketId = form.getAttribute('data-ticket-id');
                    const agentId = form.getAttribute('data-agent-id');
                    const agentName = form.getAttribute('data-agent-name');
                    
                    if (!ticketId || !agentId) {
                        console.error("Falta información de ticket o agente");
                        return;
                    }
                    
                    // Obtener botón submit
                    const submitBtn = form.querySelector('button[type="submit"]');
                    const originalText = submitBtn.innerHTML;
                    
                    // Cambiar botón a "Procesando..."
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Procesando...';
                    
                    // Emitir evento de mensaje a través de Socket.IO
                    window.socket.emit('chat_message', {
                        ticket_id: ticketId,
                        content: message,
                        sender_id: agentId,
                        sender_name: agentName,
                        sender_type: 'agent',
                        is_internal: isInternal
                    });
                    
                    // Escuchar confirmación de mensaje enviado
                    window.socket.once('message_sent', function(data) {
                        // Restaurar botón
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                        
                        // Limpiar formulario
                        messageInput.value = '';
                        if (document.getElementById('internalMessage')) {
                            document.getElementById('internalMessage').checked = false;
                        }
                        
                        // Hacer scroll hasta el final de la conversación
                        if (window.scrollChatToBottom) {
                            window.scrollChatToBottom();
                        }
                    });
                    
                    // Manejar errores - agregar un timeout por si no llega la confirmación
                    setTimeout(() => {
                        // Si el botón sigue deshabilitado después de 5 segundos, restaurarlo
                        if (submitBtn.disabled) {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = originalText;
                            console.warn("No se recibió confirmación del servidor. El mensaje podría no haberse enviado.");
                            
                            // Mostrar mensaje de error
                            const errorMsg = document.createElement('div');
                            errorMsg.className = 'alert alert-warning alert-dismissible fade show mt-2';
                            errorMsg.innerHTML = `
                                <strong>Advertencia:</strong> No se pudo confirmar el envío del mensaje. Por favor, inténtalo de nuevo.
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            `;
                            form.appendChild(errorMsg);
                            
                            // Eliminar el mensaje después de 5 segundos
                            setTimeout(() => {
                                if (errorMsg.parentNode) {
                                    errorMsg.parentNode.removeChild(errorMsg);
                                }
                            }, 5000);
                        }
                    }, 5000);
                    
                    return;
                }
                
                // Verificar si el formulario ya está en proceso de envío (para formularios normales)
                if (this.dataset.submitting === 'true') {
                    e.preventDefault();
                    return;
                }
                
                // Marcar formulario como enviando
                this.dataset.submitting = 'true';
                
                // Obtener botón submit
                const submitButtons = this.querySelectorAll('button[type="submit"], input[type="submit"]');
                
                // Desactivar botones y mostrar indicador de carga
                submitButtons.forEach(button => {
                    const originalText = button.innerHTML;
                    button.disabled = true;
                    
                    // Guardar texto original para restaurarlo en caso de error
                    button.dataset.originalText = originalText;
                    
                    // Cambiar texto por spinner
                    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Procesando...';
                });
                
                // Si el formulario es un upload de archivos, mostrar el progreso
                if (this.enctype === 'multipart/form-data') {
                    showUploadProgress(this);
                }
            });
        });
    }
    /**
     * Muestra progreso de subida de archivos
     */
    function showUploadProgress(form) {
        // Buscar el elemento de progreso
        const progressElement = form.querySelector('.upload-progress');
        
        if (!progressElement) {
            return;
        }
        
        // Mostrar el elemento de progreso
        progressElement.style.display = 'block';
        
        // Actualizar progreso cada 500ms (simulación)
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.floor(Math.random() * 10);
            
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
            }
            
            progressElement.querySelector('.progress-bar').style.width = progress + '%';
            progressElement.querySelector('.progress-value').textContent = progress + '%';
        }, 500);
    }
    
    // Inicializar notificaciones
    initNotifications();
    
    /**
     * Inicializa sistema de notificaciones
     */
    function initNotifications() {
        // Comprobar nuevas notificaciones cada minuto
        setInterval(checkNotifications, 60000);
        
        // Primera comprobación al cargar la página
        checkNotifications();
        
        function checkNotifications() {
            // Obtener contador de notificaciones
            const notificationBadge = document.querySelector('.notification-badge');
            
            if (!notificationBadge) {
                return;
            }
            
            // Hacer petición al servidor
            fetch('/api/notifications')
                .then(response => response.json())
                .then(data => {
                    // Actualizar contador
                    if (data.count > 0) {
                        notificationBadge.textContent = data.count;
                        notificationBadge.style.display = 'inline-block';
                        
                        // Si hay nuevas notificaciones, mostrar notificación emergente
                        if (data.new > 0 && Notification.permission === 'granted') {
                            new Notification('SIACASA', {
                                body: `Tienes ${data.new} nuevas notificaciones`,
                                icon: '/static/img/bn_logo.png'
                            });
                        }
                    } else {
                        notificationBadge.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error al comprobar notificaciones:', error);
                });
        }
    }
    
    // Inicializar efectos visuales
    initVisualEffects();
});