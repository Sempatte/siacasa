/**
 * SIACASA Chatbot Embed Script for {{ bank.bank_name }}
 * Generated: {{ now }}
 */
(function() {
    // Configuración del chatbot
    window.SIACASA_CONFIG = window.SIACASA_CONFIG || {
        botName: "{{ bank.bank_name }}",
        greeting: "{{ bank.greeting }}",
        theme: {
            primaryColor: "#004a87",
            secondaryColor: "#e4002b"
        },
        apiEndpoint: "{{ api_url }}api/mensaje"
    };
    
    // Cargar el archivo de widget
    const script = document.createElement('script');
    script.src = "{{ api_url }}static/js/widget.js";
    script.async = true;
    
    // Manejar errores de carga
    script.onerror = function() {
        console.error('SIACASA Chatbot: Error al cargar el widget');
    };
    
    // Añadir el script al documento
    document.head.appendChild(script);
    
    // Registrar la carga exitosa
    console.log('SIACASA Chatbot: Iniciando carga para {{ bank.bank_name }}');
})();