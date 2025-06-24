import matplotlib
matplotlib.use('Agg') # Forzar un backend no interactivo para compatibilidad en macOS
import pandas as pd
import matplotlib.pyplot as plt
import os

def generar_grafico_categorias(ruta_csv, archivo_salida):
    """
    Genera un gráfico de pie para visualizar la distribución de categorías de consulta,
    excluyendo 'escalacion_humana' y destacando las porciones más pequeñas.

    Args:
        ruta_csv (str): La ruta al archivo CSV.
        archivo_salida (str): El nombre del archivo de imagen para guardar el gráfico.
    """
    try:
        # 1. Cargar el conjunto de datos desde el CSV
        df = pd.read_csv(ruta_csv)

        # 2. Filtrar para excluir 'escalacion_humana' ya que es una acción, no una categoría de consulta.
        df_filtrado = df[df['categoria'] != 'escalacion_humana'].copy()

        # 3. Contar los valores en la columna 'categoria' del DataFrame filtrado
        conteo_categorias = df_filtrado['categoria'].value_counts()

        # 4. Preparar los datos para el gráfico y mejorar las etiquetas para el informe
        etiquetas = [etiqueta.replace('_', ' ').capitalize() for etiqueta in conteo_categorias.index]
        valores = conteo_categorias.values
        
        # 5. Lógica para "explotar" (resaltar) únicamente la porción más pequeña
        explode = [0] * len(etiquetas)
        if len(valores) > 1:
            # Encontrar el índice del valor más pequeño para destacarlo
            min_index = valores.argmin()
            explode[min_index] = 0.1

        # 6. Crear el gráfico de pie con un diseño más limpio
        fig, ax = plt.subplots(figsize=(10, 7))
        
        fig.set_facecolor('white')
        ax.set_facecolor('white') # Nos aseguramos de que tanto la figura como los ejes tengan fondo blanco

        # Añadimos 'wedgeprops' para un borde blanco que define mejor las porciones
        ax.pie(valores, labels=etiquetas, autopct='%1.1f%%',
               shadow=True, startangle=140, explode=explode,
               textprops={'fontsize': 12},
               wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
        
        ax.set_title("Distribución de Consultas por Categoría", fontsize=16)
        ax.axis('equal')  # Asegura que el pie chart sea un círculo.

        # 7. Guardar el gráfico en un archivo
        # Forzamos explícitamente el color de fondo al guardar como última medida.
        plt.savefig(archivo_salida, bbox_inches='tight', facecolor=fig.get_facecolor())
        print(f"Gráfico guardado exitosamente en: {archivo_salida}")

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en la ruta '{ruta_csv}'.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

# --- Ejecución del script ---
# Obtener la ruta del directorio donde se encuentra este script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construir la ruta al archivo CSV subiendo un nivel (de 'graphics' a 'SIACASA') y luego entrando a 'datasets'
ruta_del_dataset = os.path.join(script_dir, '..', 'datasets', 'dataset_v2_140.csv')

# Guardar el gráfico en el mismo directorio que el script para encontrarlo fácilmente
nombre_archivo_grafico = os.path.join(script_dir, 'grafico_categorias.png')

# Llamar a la función para generar el gráfico
generar_grafico_categorias(ruta_del_dataset, nombre_archivo_grafico)