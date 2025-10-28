---
title: Mi App Streamlit
sdk: docker
app_port: 8501
---

# TINKA

Aplicación Streamlit para analizar sorteos de la Tinka utilizando conectores de Snowflake y diferentes estrategias estadísticas/ML.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py --server.port=8501
```

La aplicación se sirve en el puerto **8501**, requisito para Hugging Face Spaces.

## Despliegue en Hugging Face Spaces

1. Crea un Space nuevo con el SDK **Docker**.
2. Copia el contenido de este repositorio.
3. Configura las variables de entorno (Secrets) si necesitas conectar a Snowflake.
4. Opcional: activa el workflow de GitHub Actions y define el secreto `HF_TOKEN` para sincronizar automáticamente.

## Sincronización automática (GitHub → Hugging Face)

Este repositorio incluye el workflow `.github/workflows/sync-to-hf.yml`. Configura los valores `HF_USERNAME`, `SPACE_NAME` y el secreto `HF_TOKEN` en GitHub para que cada push a `main` se replique en el Space.

## Licencia

Este proyecto se distribuye bajo los términos indicados en el repositorio original.
