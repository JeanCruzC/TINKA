# Tinka Analytics

Aplicación integral para analizar los sorteos de la Tinka y generar combinaciones
sugeridas. El proyecto combina una interfaz de línea de comandos y una versión
web en Streamlit, además de conectores a bases de datos MySQL y Snowflake.

## Estructura principal

```
.
├── analizador.py          # Estadísticas y análisis históricos
├── config.py              # Configuración de BD, Snowflake y rutas de datos
├── data/                  # Caché, reportes HTML y resultados generados
├── db_connector.py        # Conectores MySQL y Snowflake + caché local
├── generador.py           # Estrategias heurísticas para crear combinaciones
├── main.py                # Menú CLI con todas las funcionalidades
├── ml.py                  # Utilidades de probabilidad bayesiana y ranking ML
├── streamlit_app.py       # Interfaz Streamlit con el mismo motor del CLI
├── utils.py               # Utilidades comunes (I/O, parsing, helpers)
├── visualizador.py        # Gráficas y reportes en HTML/ASCII
├── Dockerfile             # Imagen preparada para Hugging Face Spaces
├── environment.yml        # Entorno Conda con dependencias principales
└── requirements.txt       # Dependencias pip equivalentes
```

## Requisitos

- Python 3.9+
- Dependencias listadas en `requirements.txt`

Instala las dependencias con:

```bash
pip install -r requirements.txt
```

> Para entornos Conda puedes crear el entorno usando
> `conda env create -f environment.yml`.

## Uso de la aplicación

### CLI (modo consola)

1. Edita `config.py` si necesitas cambiar la configuración de la base de datos
   local o de Snowflake.
2. Ejecuta el menú interactivo:

   ```bash
   python main.py
   ```

3. Desde el menú podrás:
   - Visualizar estadísticas detalladas y exportar un reporte HTML.
   - Analizar la frecuencia de números individuales.
   - Generar combinaciones con múltiples estrategias heurísticas.
   - Evaluar tu combinación manual.
   - Revisar las mejores jugadas históricas según un puntaje heurístico.
   - Actualizar los datos desde la base de datos y refrescar la caché local.
   - Obtener recomendaciones automáticas que combinan análisis bayesiano y
     un ranking ML heurístico.

### Aplicación web (Streamlit)

```bash
streamlit run streamlit_app.py --server.port=8501
```

La aplicación se sirve en el puerto `8501`, requisito para Hugging Face Spaces.
Incluye las mismas funcionalidades que el menú CLI, conectándose a la fuente de
datos configurada.

### Conexión a Snowflake

Configura las credenciales a través de variables de entorno o mediante
`st.secrets["snowflake"]` cuando despliegues en Streamlit Cloud/Hugging Face.
Si no se detectan credenciales válidas la aplicación continuará funcionando con
los datos locales en `data/`.

## Despliegue en Docker / Hugging Face Spaces

1. Crea un Space nuevo con el SDK **Docker**.
2. Copia el contenido de este repositorio.
3. Configura las variables de entorno (Secrets) si necesitas conectar a
   Snowflake.
4. Opcional: activa el workflow de GitHub Actions y define el secreto
   `HF_TOKEN` para sincronización automática.

## Licencia

Este proyecto se distribuye bajo los términos indicados en el repositorio
original.
