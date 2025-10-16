# processing/pipeline.py
import asyncio
import json
from pathlib import Path
from processing.phases import PhaseTask, PhaseStatus

class PipelineManager:
    def __init__(self, phases: dict[str, PhaseTask], deps: dict[str, list[str]], root_dir: Path):
        self.phases = phases
        self.deps = deps
        self.root_dir = root_dir
        self.global_log = root_dir / "pipeline.json"
        self._load_global_state()

    def _load_global_state(self):
        if self.global_log.exists():
            _ = json.loads(self.global_log.read_text())

    def _save_global_state(self):
        summary = {name: task.status.value for name, task in self.phases.items()}
        self.global_log.parent.mkdir(parents=True, exist_ok=True)
        self.global_log.write_text(json.dumps(summary))

    def cancel_all(self):
        """
        Cancela todas las fases que estén en RUNNING, mostrando pid y estado.
        """
        for name, phase in self.phases.items():
            phase.load_state()
            pid = phase._proc.pid if phase._proc else None
            alive = phase._proc.is_alive() if phase._proc else False
            print(f"[cancel_all] Fase {name}: status={phase.status}, pid={pid}, is_alive={alive}")
            if phase.status == PhaseStatus.RUNNING and phase._proc:
                print(f"[cancel_all] → Terminando proceso {name} (pid={pid})")
                phase.cancel()
        self._save_global_state()

    async def run(self):
        pending = set(self.phases.keys())
        completed = set()

        while pending:
            # fases listas cuyo deps ya completadas
            ready = [n for n in pending if all(d in completed for d in self.deps.get(n, []))]
            if not ready:
                raise RuntimeError("Dependencias cíclicas o faltantes en el pipeline.")
            tasks = []
            for name in ready:
                phase = self.phases[name]
                phase.load_state()
                if phase.status == PhaseStatus.SUCCESS:
                    completed.add(name)
                else:
                    tasks.append(asyncio.create_task(phase.start()))
                pending.remove(name)
            if tasks:
                # Si alguna fase se canceló, abortamos to do de inmediato
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Chequea estado de cada fase que acabó de ejecutarse
                for name in ready:
                    st = self.phases[name].status
                    if st == PhaseStatus.CANCELLED:
                        # Guardar estado global y salir del run
                        self._save_global_state()
                        return

                for name in ready:
                    st = self.phases[name].status
                    if st == PhaseStatus.ERROR:
                        self._save_global_state()
                        return

                # marcar completadas (excluye CANCELLED para no volver a correrlas)
                for name in ready:
                    st = self.phases[name].status
                    if st == PhaseStatus.SUCCESS:
                        completed.add(name)
                # guardar estado global tras cada ronda
                self._save_global_state()