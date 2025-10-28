# Diccionario de configuraciones de bancos
BANK_CONFIGS = {
    "bn": {  # Banco de la Nación
        "bank_name": "Banco de la Nación",
        "greeting": "Hola, soy el asistente virtual del Banco de la Nación. ¿En qué puedo ayudarte hoy?",
        "style": "formal",
        "allowed_domains": ["bn.com.pe", "www.bn.com.pe"]
    },
    "bcp": {  # Banco de Crédito del Perú
        "bank_name": "Banco de Crédito del Perú",
        "greeting": "¡Hola! Soy el asistente virtual del BCP. ¿Cómo puedo ayudarte?",
        "style": "casual",
        "allowed_domains": ["viabcp.com", "www.viabcp.com"]
    },
    "caja_andes": {  # Caja de los Andes (demo)
        "bank_name": "Caja de los Andes",
        "greeting": "Hola, soy el asistente virtual de Caja de los Andes. Estoy listo para ayudarte.",
        "style": "friendly",
        "allowed_domains": ["cajadelosandes.pe", "demo.cajadelosandes.pe"]
    },
    "default": {  # Configuración predeterminada
        "bank_name": "Banco",
        "greeting": "Hola, soy SIACASA, tu asistente bancario virtual. ¿En qué puedo ayudarte?",
        "style": "neutral",
        "allowed_domains": []
    }
}
