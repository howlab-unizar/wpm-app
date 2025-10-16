# processing/actions_handler.py
from pathlib import Path
import threading, asyncio
from processing.store import PIPELINE_STORE, BUSY
from processing.phases import PhaseTask, PhaseStatus
from processing.pipeline import PipelineManager
from processing.tasks.process_task import bin2csv, seg_csv, bio_analisis, move_analisis, create_report

PHASE_ORDER = ['bin2csv', 'seg_csv', 'bio_analisis', 'analisis_movimiento']

def build_pipeline_manager(pid: str, info: dict, base_dir: str) -> PipelineManager:
    """
    Crea (pero NO ejecuta) el PipelineManager para el record dado.
    Esto aglutina la parte de 'executeProcess' que configura fases/deps.
    """
    date      = info['patientDate']
    record    = {'id': pid, 'fecha': date}
    fecha_fmt = date.replace('-', '.')
    root_dir  = Path(base_dir) / 'Datos_pacientes' / pid / f"{pid}_{fecha_fmt}"

    # Configura tus fases y deps EXACTO mismo que en execute_pipeline
    task_map = {
        'bin2csv':             (bin2csv,             '01_raw'),
        'seg_csv':             (seg_csv,             '02_seg'),
        'bio_analisis':        (bio_analisis,        '03_bio'),
        'analisis_movimiento': (move_analisis,       '03_bio'),
        'create_report':       (create_report,     '05_rep')
    }
    deps = {
        'seg_csv':             ['bin2csv'],
        'bio_analisis':        ['seg_csv'],
        'analisis_movimiento': ['seg_csv'],
        'create_report': ['analisis_movimiento'] # bio_analisis
    }

    phases = {}
    for name, (fn, sub) in task_map.items():
        wd = root_dir / sub
        wd.mkdir(parents=True, exist_ok=True)
        pt = PhaseTask(name, fn, (record,), wd)
        phases[name] = pt

    return PipelineManager(phases, deps, root_dir)

def stop_pipeline(pid):
    pm = PIPELINE_STORE.get(pid)
    if not pm:
        return '❌ No hay pipeline activo para parar.'
    pm.cancel_all()
    return f'🛑 Proceso detenido para {pid}.'

def continue_pipeline(pid, info, base_dir):
    date = info['patientDate']
    record = {'id': pid, 'fecha': date}

    # 1) Si YA hay un proceso activo para este mismo PID, devolvemos advertencia:
    from processing import store
    # 1a) Si store.ACTIVE_JOB == pid, ya hay pipeline corriendo
    if store.ACTIVE_JOB == pid:
        return f"⚠️ Ya hay un proceso activo para el paciente {pid}."
    # 1b) Si ya está en la cola, también lo ignoramos
    for queued_pid, _ in store.PIPELINE_QUEUE:
        if queued_pid == pid:
            return f"⚠️ Ya hay un proceso en cola para el paciente {pid}."

    # Reconstruir las PhaseTask para este paciente
    root_dir = Path(base_dir) / 'Datos_pacientes' / pid / f"{pid}_{date.replace('-','.')}"
    phases: dict[str, PhaseTask] = {}
    task_map = {
        'bin2csv':             (bin2csv,             '01_raw'),
        'seg_csv':             (seg_csv,             '02_seg'),
        'bio_analisis':        (bio_analisis,        '03_bio'),
        'analisis_movimiento': (move_analisis,       '03_bio'),
    }
    from processing.phases import PhaseStatus
    for name, (fn, sub) in task_map.items():
        wd = root_dir / sub
        wd.mkdir(parents=True, exist_ok=True)
        pt = PhaseTask(name, fn, (record,), wd)
        pt.load_state()  # Lee <sub>/<name>.json y asigna pt.status
        phases[name] = pt

    # 2) Detectar “RUNNING huérfano” tras reinicio:
    # Si JSON dice RUNNING pero no existe un proceso vivo (store.BUSY == False),
    # lo marcamos CANCELLED para poder reanudarlo.
    if not store.BUSY:
        for name, ph in phases.items():
            if ph.status == PhaseStatus.RUNNING:
                ph.status = PhaseStatus.CANCELLED
                ph._save_state()

    # 3) Buscar la PRIMERA fase en CANCELLED para reanudar
    to_resume = next((n for n, ph in phases.items() if ph.status == PhaseStatus.CANCELLED), None)
    if not to_resume:
        return '⚠️ No hay fase en CANCELLED para continuar.'

    # 4) Preparamos la info para encolar/ejecutar la fase seleccionada
    info_resume = {
        'patientId': pid,
        'patientDate': date,
        'process': to_resume
    }
    from processing.pipeline_scheduler import schedule_pipeline
    return schedule_pipeline(pid, info_resume)

def execute_pipeline(pid: str, info: dict, base_dir: str) -> str:
    """
    Ejecuta (o encola) el pipeline completo o la fase concreta seleccionada,
    garantizando que ninguna fase arranque si sus previas no están en SUCCESS.
    Además, si ya hay un pipeline activo o en cola para este paciente,
    no crea uno nuevo y devuelve advertencia.
    Si existe en disco un estado RUNNING huérfano para la fase solicitada,
    permite continuar esa fase (tratándola como CANCELLED) y la reanuda.
    """
    # 1) Normalizar datos
    date      = info.get('patientDate')
    record    = {'id': pid, 'fecha': date}
    fecha_fmt = date.replace('-', '.')
    root_dir  = Path(base_dir) / 'Datos_pacientes' / pid / f"{pid}_{fecha_fmt}"

    from processing import store
    from processing.phases import PhaseStatus

    # 1b) Comprobar si ya hay un proceso activo o en cola para este paciente
    if store.ACTIVE_JOB == pid:
        return f"⚠️ Ya hay un proceso activo para el paciente {pid}."
    for queued_pid, _ in store.PIPELINE_QUEUE:
        if queued_pid == pid:
            return f"⚠️ Ya hay un proceso en cola para el paciente {pid}."

    # 2) Reconstruir o recuperar PipelineManager (si existe)
    pm = PIPELINE_STORE.get(pid)

    # 3) Si se solicita una fase concreta...
    selected = info.get('process')
    if selected:
        # 3a) Reconstruir únicamente la PhaseTask de la fase seleccionada para leer su estado
        #     (no es necesario cargar todas todavía)
        task_map = {
            'bin2csv':             (bin2csv,             '01_raw'),
            'seg_csv':             (seg_csv,             '02_seg'),
            'bio_analisis':        (bio_analisis,        '03_bio'),
            'analisis_movimiento': (move_analisis,       '03_bio'),
        }
        fn, sub = task_map[selected]
        wd = root_dir / sub
        wd.mkdir(parents=True, exist_ok=True)
        pt_selected = PhaseTask(selected, fn, (record,), wd)
        pt_selected.load_state()

        # 3b) Si la fase está marcada como RUNNING en disco, pero no hay ningún hilo vivo,
        #     la consideramos huérfana: la marcamos CANCELLED en el JSON y la reanudamos.
        if pt_selected.status == PhaseStatus.RUNNING and not store.BUSY:
            pt_selected.status = PhaseStatus.CANCELLED
            pt_selected._save_state()
            # Reutilizamos schedule_pipeline para reanudarla:
            from processing.pipeline_scheduler import schedule_pipeline
            return schedule_pipeline(pid, {
                'patientId':   pid,
                'patientDate': date,
                'process':     selected
            })

        # 3c) Si no era un RUNNING huérfano, entonces procedemos con la lógica normal:
        #     cargar todas las PhaseTask para ver dependencias.
        if pm and selected in pm.phases:
            phases = pm.phases
        else:
            phases = {}
            for name, (fn_phase, subdir) in task_map.items():
                wd_phase = root_dir / subdir
                wd_phase.mkdir(parents=True, exist_ok=True)
                pt = PhaseTask(name, fn_phase, (record,), wd_phase)
                pt.load_state()
                phases[name] = pt

        # 3d) Comprobar dependencias anteriores
        idx   = PHASE_ORDER.index(selected)
        unmet = [
            phase for phase in PHASE_ORDER[:idx]
            if phases.get(phase) is None or phases[phase].status != PhaseStatus.SUCCESS
        ]
        if unmet:
            return (
                f"⚠️ No se puede ejecutar “{selected}” porque faltan fases anteriores "
                f"en SUCCESS: {unmet}."
            )

        # 3e) Encolar solo esa fase
        from processing.pipeline_scheduler import schedule_pipeline
        return schedule_pipeline(pid, {
            'patientId':   pid,
            'patientDate': date,
            'process':     selected
        })

    # 4) Si no se solicitó fase concreta, es pipeline completo
    if pm:
        # 4a) Asegurar que no hay fases en CANCELLED ni ERROR
        problematic = [
            name for name, ph in pm.phases.items()
            if ph.status not in (PhaseStatus.PENDING, PhaseStatus.SUCCESS)
        ]
        if problematic:
            return (
                f"⚠️ No se puede iniciar pipeline completo: hay fases en "
                f"CANCELLED/ERROR ({problematic}). Usa “Continuar” para reanudarlas."
            )
        # 4b) Encolar to do el pipeline
        from processing.pipeline_scheduler import schedule_pipeline
        return schedule_pipeline(pid, {
            'patientId':   pid,
            'patientDate': date
        })

    # 5) No existe ningún manager previo: informar error
    return '❌ Primero inicie el pipeline completo desde la página de Datos de Pacientes.'