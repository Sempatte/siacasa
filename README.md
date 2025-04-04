# SIACASA - Sistema de Chatbot Bancario con Análisis de Sentimientos

Este proyecto implementa un sistema avanzado de chatbot con análisis de sentimientos para mejorar la eficiencia y satisfacción en la atención al cliente del sector bancario peruano, como parte de un proyecto de tesis.

## Características

- **Chatbot inteligente**: Utiliza OpenAI GPT-4o para proporcionar respuestas precisas y personalizadas
- **Análisis de sentimientos**: Detecta el estado emocional del usuario para adaptar las respuestas
- **Múltiples interfaces**: Disponible en modo consola y como aplicación web
- **Arquitectura limpia**: Organización del código siguiendo principios de Clean Architecture
- **Facilidad de extensión**: Diseñado para ser fácilmente ampliable con nuevas funcionalidades

## Arquitectura

El proyecto sigue los principios de Clean Architecture con las siguientes capas:

- **Domain**: Contiene las entidades y reglas de negocio
- **Application**: Implementa los casos de uso y define interfaces
- **Infrastructure**: Provee implementaciones concretas de las interfaces
- **Interfaces**: Contiene las interfaces de usuario (CLI y web)

## Requisitos

- Python 3.8 o superior
- API key de OpenAI
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

### Interfaz web (predeterminada)

```bash
python -m bot_siacasa.main
```

Luego, abre tu navegador en http://localhost:5000

### Interfaz de línea de comandos

```bash
python -m bot_siacasa.main --consola
```

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
│   ├── application/         # Capa de aplicación
│   ├── infrastructure/      # Capa de infraestructura
│   └── interfaces/          # Interfaces de usuario
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

Tu Nombre - [Tu Email](mailto:tu.email@example.com)

---

Proyecto desarrollado como parte de tesis en la Universidad Peruana de Ciencias Aplicadas (UPC).