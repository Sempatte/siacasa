# SIACASA - Sistema Inteligente de Chatbot Bancario con Análisis de Sentimientos

Este proyecto implementa un sistema avanzado de chatbot con análisis de sentimientos para mejorar la eficiencia y satisfacción en la atención al cliente del sector bancario peruano, como parte de un proyecto de tesis.

## Características

- **Chatbot inteligente**: Utiliza OpenAI GPT-3.5 para proporcionar respuestas precisas y personalizadas
- **Análisis de sentimientos**: Detecta el estado emocional del usuario para adaptar las respuestas
- **Múltiples interfaces**: Disponible como aplicación web y como widget integrable
- **Soporte para formato Markdown**: Muestra texto enriquecido con negritas, listas numeradas y otros formatos
- **Persistencia de conversaciones**: Mantiene el historial para ofrecer respuestas contextualizadas
- **Arquitectura limpia**: Organización del código siguiendo principios de Clean Architecture
- **Facilidad de extensión**: Diseñado para ser fácilmente ampliable con nuevas funcionalidades

## Arquitectura

El proyecto sigue los principios de Clean Architecture con las siguientes capas:

- **Domain**: Contiene las entidades y reglas de negocio
- **Application**: Implementa los casos de uso y define interfaces
- **Infrastructure**: Provee implementaciones concretas de las interfaces
- **Interfaces**: Contiene las interfaces de usuario (web y widget)

## Requisitos

- Python 3.8 o superior
- API key de OpenAI (solicitar token a [u201816293@upc.edu.pe](mailto:u201816293@upc.edu.pe))
- Dependencias listadas en `requirements.txt`

## Instalación

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/siacasa.git
   cd siacasa
   ```

2. Crear y activar un entorno virtual:
   ```bash
   # En macOS/Linux
   python3 -m venv venv
   source venv/bin/activate

   # En Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   ```bash
   # Copiar el archivo de ejemplo
   cp .env.example .env
   
   # Editar el archivo .env y agregar tu API key de OpenAI
   # OPENAI_API_KEY=tu_api_key_aqui
   ```

## Uso

### Iniciar el servidor de SIACASA

```bash
python -m bot_siacasa.main
```

Por defecto, el servidor se iniciará en `http://localhost:3200`

### Acceder a la interfaz web

Abre tu navegador en `http://localhost:3200` para acceder a la interfaz de chat dedicada.

## Integración en Sitios Web (Widget)

### Método Simple de Integración

Para integrar el chatbot SIACASA en cualquier sitio web, simplemente añada el siguiente código antes de cerrar la etiqueta `</body>`:

```html
<!-- Configuración básica del chatbot -->
<script>
  window.SIACASA_CONFIG = {
    botName: "Asistente Virtual",
    botSubtitle: "Banco de la Nación",
    apiEndpoint: "http://servidor.com:3200/api/mensaje",
    theme: {
      primaryColor: "#004a87",  // Color principal
      secondaryColor: "#e4002b" // Color secundario
    }
  };
</script>

<!-- Script de inicialización del chatbot -->
<script>
  document.addEventListener('DOMContentLoaded', function() {
    // Crear contenedor para el chatbot
    const container = document.createElement('div');
    container.id = 'siacasa-chatbot-container';
    container.style.position = 'fixed';
    container.style.bottom = '20px';
    container.style.right = '20px';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    
    // Actualizar configuración
    if (window.SIACASA_CONFIG) {
      window.SIACASA_CONFIG.containerSelector = '#siacasa-chatbot-container';
    }
    
    // Cargar script del chatbot
    const script = document.createElement('script');
    script.src = "http://servidor.com:3200/api/embed/bn.js";
    document.body.appendChild(script);
  });
</script>
```

Reemplace `servidor.com:3200` con la dirección correcta de su servidor SIACASA.

### Opciones de Configuración del Widget

El widget puede personalizarse mediante el objeto `SIACASA_CONFIG`:

| Parámetro | Tipo | Descripción | Valor por defecto |
|-----------|------|-------------|-------------------|
| `botName` | String | Nombre del asistente | "Asistente Inteligente" |
| `botSubtitle` | String | Subtítulo o descripción | "SIACASA" |
| `apiEndpoint` | String | URL del endpoint de la API | "http://localhost:3200/api/mensaje" |
| `initialMessage` | String | Mensaje inicial del bot | "Hola, soy tu asistente virtual. ¿En qué puedo ayudarte hoy?" |
| `theme.primaryColor` | String (hex) | Color principal del widget | "#004a87" |
| `theme.secondaryColor` | String (hex) | Color secundario | "#e4002b" |
| `theme.textColor` | String (hex) | Color del texto | "#333333" |
| `theme.fontFamily` | String | Tipografía | "'Inter', 'Segoe UI', Roboto, sans-serif" |

### Consideraciones Importantes

1. **Cross-Origin (CORS)**: Asegúrese de que su servidor SIACASA esté configurado para permitir solicitudes desde el dominio donde se integra el widget.

2. **Soporte de Markdown**: El widget procesa automáticamente el formato Markdown en las respuestas del chatbot:
   - Texto en **negrita** usando `**texto**`
   - Listas numeradas usando `1. Primer punto`, `2. Segundo punto`, etc.
   - Texto en *cursiva* usando `*texto*`

3. **Persistencia de sesión**: El widget mantiene un ID de sesión único por usuario almacenado en `localStorage` para preservar el contexto de la conversación.

4. **Adaptabilidad**: El widget es responsive y se adapta a dispositivos móviles.

5. **Personalización**: Se pueden añadir estilos CSS adicionales para personalizar aún más la apariencia del widget.

## Estructura de directorios

```
SIACASA/
├── .env                     # Variables de entorno
├── .gitignore               # Archivos a ignorar
├── README.md                # Documentación
├── requirements.txt         # Dependencias
├── bot_siacasa/             # Paquete principal
│   ├── __init__.py
│   ├── main.py              # Punto de entrada
│   ├── domain/              # Capa de dominio
│   │   ├── entities/        # Entidades del dominio
│   │   │   ├── conversacion.py
│   │   │   ├── mensaje.py
│   │   │   ├── usuario.py
│   │   │   └── analisis_sentimiento.py
│   ├── application/         # Capa de aplicación
│   │   ├── interfaces/      # Interfaces de aplicación
│   │   │   ├── ia_provider_interface.py
│   │   │   └── repository_interface.py
│   │   ├── use_cases/       # Casos de uso
│   │   │   ├── procesar_mensaje_use_case.py
│   │   │   └── analizar_sentimiento_use_case.py
│   ├── infrastructure/      # Capa de infraestructura
│   │   ├── ai/              # Implementaciones de IA
│   │   │   └── openai_provider.py
│   │   ├── repositories/    # Implementaciones de repositorios
│   │   │   ├── memory_repository.py
│   │   │   └── sqlite_repository.py
│   └── interfaces/          # Interfaces de usuario
│       └── web/             # Interfaz web
│           ├── web_app.py
│           ├── static/
│           │   ├── js/
│           │   │   └── widget.js     # Widget embebible
│           └── templates/
└── tests/                   # Pruebas
```

## Contribuciones

1. Haz un fork del proyecto
2. Crea una rama para tu funcionalidad: `git checkout -b feature/nueva-funcionalidad`
3. Haz commit de tus cambios: `git commit -m 'Añadir nueva funcionalidad'`
4. Empuja a la rama: `git push origin feature/nueva-funcionalidad`
5. Envía un pull request

## Licencia

Este proyecto está licenciado bajo [MIT License](LICENSE).

## Autor

Sebastián De La Torre - [u201816293@upc.edu.pe](mailto:u201816293@upc.edu.pe)
Sebastian Moreyra

---

Proyecto desarrollado como parte de tesis en la Universidad Peruana de Ciencias Aplicadas (UPC).
