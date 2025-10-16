# processing/phases.py
import asyncio
import json
import time
import inspect
from enum import Enum
from pathlib import Path
from multiprocessing import Process

class PhaseStatus(Enum):
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    SUCCESS   = "SUCCESS"
    ERROR     = "ERROR"
    CANCELLED = "CANCELLED"

def _run_phase(fn, args):
    """
    Función auxiliar de nivel de módulo para ejecutar una tarea de fase,
    compatible con pickle en multiprocessing.
    """
    res = fn(*args)
    if inspect.isawaitable(res):
        import asyncio as _asyncio
        _asyncio.run(res)

class PhaseTask:
    def __init__(self, name: str, fn, args: tuple, work_dir: Path):
        self.name     = name
        self.fn       = fn
        self.args     = args
        self.work_dir = work_dir
        self.status   = PhaseStatus.PENDING
        self.log_file = work_dir / f"{name}.json"
        self._proc    = None

    def _save_state(self):
        data = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": time.time()
        }
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text(json.dumps(data))

    def load_state(self):
        if self.log_file.exists():
            data = json.loads(self.log_file.read_text())
            self.status = PhaseStatus(data.get("status", PhaseStatus.PENDING.value))

    def cancel(self):
        # Marca cancelado; start() se encargará de matar el proceso
        if self.status == PhaseStatus.RUNNING:
            self.status = PhaseStatus.CANCELLED
            self._save_state()

    async def start(self):
        if self.status == PhaseStatus.RUNNING:
            return

        # Inicia la fase
        self.status = PhaseStatus.RUNNING
        self._save_state()

        # Levanta proceso usando función de módulo
        self._proc = Process(target=_run_phase, args=(self.fn, self.args))
        self._proc.start()

        try:
            # Espera finalización o cancelación
            while True:
                if self._proc.exitcode is not None:
                    break
                if self.status == PhaseStatus.CANCELLED:
                    self._proc.terminate()
                    self._proc.join()
                    break
                await asyncio.sleep(0.5)

            # Estado final según exitcode
            if self.status == PhaseStatus.CANCELLED:
                pass
            elif self._proc.exitcode == 0:
                if self.name == "create_report":
                    # Mantener en estado PENDING para la fase de informe
                    self.status = PhaseStatus.PENDING
                else:
                    self.status = PhaseStatus.SUCCESS
            else:
                self.status = PhaseStatus.ERROR

        except Exception:
            self.status = PhaseStatus.ERROR
        finally:
            self._save_state()
