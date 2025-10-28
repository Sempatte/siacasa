## Conjunto de entrenamiento demo: Caja de los Andes

Este directorio almacena los archivos CSV que se cargan desde el panel de administración para poblar el conocimiento del asistente demo de **Caja de los Andes**.

- `caja_de_los_andes_faq.csv` contiene consultas y respuestas alineadas con los casos de prueba CP001–CP032 y CP041.
- Sube este archivo desde el módulo **Entrenamiento → Subir archivo** del panel administrador utilizando el usuario demo.
- Una vez procesado el archivo, la información queda disponible en la base vectorial y el chatbot puede responder sin depender de datos codificados en el código fuente.

> Nota: no modifiques el archivo manualmente en producción. Si necesitas actualizar la información, genera una nueva versión del CSV y cárgala desde el panel para mantener el rastro de versiones.
