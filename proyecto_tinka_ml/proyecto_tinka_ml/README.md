# Sistema de Análisis y Generación de Combinaciones — Tinka (con ML)

**Aviso:** La lotería es aleatoria. Este proyecto es **educativo**; no garantiza aciertos.

## 1) Requisitos
- Python 3.9+
- Instala dependencias:
```bash
pip install -r requirements.txt
```

## 2) Configurar BD
Edita `config.py` con tus credenciales (XAMPP por defecto). La tabla `resultados` debe tener:
`id_sorteo`, `fecha_sorteo`, `numeros`, `boliyapa`, `jackpot`, `created_at` (opcional).

## 3) Ejecutar
```bash
python main.py
```

## 4) Menú
1. Dashboard de estadísticas (exporta `data/reporte.html`)
2. Análisis por número
3. Generar combinaciones (elige estrategia y **cantidad**)
4. Evaluar tu combinación
5. Mejores históricas por score heurístico
6. Exportar análisis a HTML
7. Refrescar datos desde la BD (actualiza caché)
8. **Recomendación automática (ML)**: calcula probabilidades bayesianas (globales + recientes), genera un pool (estrategias clásicas + **Thompson Sampling**) y rankea con un score ML (log-prob + heurísticas). Guarda:
   - `data/probabilidades.json`
   - `data/combinaciones_generadas.json`

## 5) Notas
- Cambios robustos en caché (JSON atómico).
- SQL con SQLAlchemy para evitar warnings.
- Visualización simple con matplotlib (PNG embebido).
