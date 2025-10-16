# store.py
from collections import deque
from processing.pipeline import PipelineManager

# Diccionario global: pid -> PipelineManager
PIPELINE_STORE: dict[str, PipelineManager] = {}

PIPELINE_QUEUE = deque() # Cola de pid, info, base_dir
BUSY = False             # Indica si hay un pipeline en ejecución
ACTIVE_JOB: str | None = None  # PID del paciente cuyo pipeline está corriendo ahora mismo (o None)