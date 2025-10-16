# config.py
import os
from pydantic_settings import BaseSettings
from pydantic import DirectoryPath, Field
from pathlib import Path

directorio_actual = Path(__file__).resolve().parent.parent  # project_root
bucket_path = directorio_actual / '_bucket'
datos_pacientes = directorio_actual / 'Datos_pacientes'

os.makedirs(bucket_path, exist_ok=True)  # Crea la carpeta si no existe
os.makedirs(datos_pacientes, exist_ok=True)  # Crea la carpeta si no existe

class Settings(BaseSettings):
    base_directory: DirectoryPath
    bucket_directory: DirectoryPath
    watch_directory: DirectoryPath

    purge_after_pdf: bool = Field(default=False, alias="PURGE_AFTER_PDF")

    class Config:
        # Ubicación del archivo .env en el paquete
        base_dir = Path(__file__).resolve().parent
        env_file = str(base_dir / '.env')
        env_file_encoding = 'utf-8'

        @classmethod
        def get_env_val(cls, field: str) -> str:
            raw = super().get_env_val(field)
            # Determinar carpeta base para relatives
            project_root = cls.base_dir.parent

            # Si configuración es un punto, usar ruta estándar
            if raw == '.':
                if field == 'base_directory':
                    path = project_root / 'Datos_pacientes'
                else:
                    path = project_root / '_bucket'
            else:
                candidate = Path(raw)
                if candidate.is_absolute():
                    path = candidate
                else:
                    # para base_directory, relativo a project_root
                    if field == 'base_directory':
                        path = project_root / raw
                    else:
                        # bucket y watch también relativos a project_root
                        path = project_root / raw
            # Asegurar que exista
            path.mkdir(parents=True, exist_ok=True)
            return str(path)

settings = Settings()
