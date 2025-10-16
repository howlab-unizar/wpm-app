# processing/pipeline_scheduler.py
import threading
import asyncio
from pathlib import Path

from collections import deque
import processing.store as store
from processing.actions_handler import build_pipeline_manager
from processing.config import settings
from processing.phases import PhaseStatus

# Lock para operaciones atómicas en la cola y el flag
_lock = threading.Lock()


def _worker(pid: str, info: dict):
    """
    Worker que ejecuta el PipelineManager y, al terminar,
    dispara el siguiente en cola.
    """
    try:
        pm = store.PIPELINE_STORE[pid]
        # Ejecuta el pipeline (puede ser completo o fase individual)
        asyncio.run(pm.run())
    finally:
        # Al terminar, marcamos BUSY=False y sacamos el siguiente en cola (si hay)
        next_entry = None
        with _lock:
            # Ya no hay proceso en ejecución
                store.BUSY = False
                store.ACTIVE_JOB = None
                if store.PIPELINE_QUEUE:
                    next_entry = store.PIPELINE_QUEUE.popleft()

        # Si había uno en cola, lo arranca fuera del lock para evitar deadlock
        if next_entry:
            next_pid, next_info = next_entry
            schedule_pipeline(next_pid, next_info)


def schedule_pipeline(pid: str, info: dict) -> str:
    """
    Encola o ejecuta inmediatamente el pipeline para el paciente `pid`.

    - Si no hay ningún pipeline ejecutándose, lo arranca de inmediato.
    - Si ya hay uno en curso, lo añade a la cola FIFO.

    Devuelve un mensaje indicando la acción tomada.
    """
    with _lock:
        # Construye (o reconstruye) el PipelineManager
        pm = build_pipeline_manager(pid, info, settings.base_directory)
        store.PIPELINE_STORE[pid] = pm

        # Si no hay pipeline corriendo, lo ejecutamos ahora
        if not store.BUSY:
            # Iniciamos el pipeline de inmediato para `pid`
            store.BUSY = True
            store.ACTIVE_JOB = pid
            thread = threading.Thread(
                target = lambda: _worker(pid, info),
                daemon = True
            )
            thread.start()
            return f"🚀 Pipeline para {pid} iniciada inmediatamente."

        # Si hay uno en curso, lo ponemos en cola
        store.PIPELINE_QUEUE.append((pid, info))
        pos = len(store.PIPELINE_QUEUE)

        # 3a) Si es “continuar” (fase concreta), marcamos SOLO esa fase en PENDING:
        fase_a_continuar = info.get('process')
        if fase_a_continuar:
            phase_obj = pm.phases.get(fase_a_continuar)
            if phase_obj:
                phase_obj.status = PhaseStatus.PENDING
                phase_obj._save_state()  # Graba en disco el JSON con estado “PENDING”
            else:
                # Si se ha solicitado pipeline completo (no hay key 'process'),
                #     marcamos todas las fases como PENDING (por si ya existiera pipeline anterior con otro estado)
                for phase_obj in pm.phases.values():
                    phase_obj.status = PhaseStatus.PENDING
                    phase_obj._save_state()
                # Además, conviene actualizar también el estado global del pipeline:
                pm._save_global_state()

        return f"⏳ Pipeline para {pid} en cola (posición {pos})."
