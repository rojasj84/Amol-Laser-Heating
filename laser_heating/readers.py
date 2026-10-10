"""File-format adapters. Add a reader without changing fitting or plotting."""
from pathlib import Path
from typing import Protocol

import numpy as np

from TemperatureFit.SpeFile import SpeFile
from .models import CameraData


class CameraReader(Protocol):
    extensions: tuple[str, ...]

    def read(self, path: Path) -> CameraData: ...


class SpeReader:
    extensions = (".spe",)

    def read(self, path: Path) -> CameraData:
        data = SpeFile(str(path))
        return CameraData(np.asarray(data.img), data.x_calibration, Path(path), float(data.exposure_time))


class NpzReader:
    """Generic camera export: frames and wavelengths_nm; optional exposure_seconds."""

    extensions = (".npz",)

    def read(self, path: Path) -> CameraData:
        with np.load(path, allow_pickle=False) as archive:
            exposure = float(archive["exposure_seconds"]) if "exposure_seconds" in archive else None
            return CameraData(archive["frames"], archive["wavelengths_nm"], Path(path), exposure)


class ReaderRegistry:
    def __init__(self) -> None:
        self._readers: dict[str, CameraReader] = {}

    def register(self, name: str, reader: CameraReader) -> None:
        if name in self._readers:
            raise ValueError(f"Reader {name!r} is already registered")
        self._readers[name] = reader

    def get(self, name: str) -> CameraReader:
        try:
            return self._readers[name]
        except KeyError as error:
            raise ValueError(f"Unknown camera reader {name!r}") from error

    def read(self, path: str | Path, reader_name: str) -> CameraData:
        reader = self.get(reader_name)
        path = Path(path)
        if path.suffix.lower() not in reader.extensions:
            raise ValueError(f"Reader {reader_name!r} supports {', '.join(reader.extensions)}, not {path.suffix}")
        return reader.read(path)

    @classmethod
    def defaults(cls) -> "ReaderRegistry":
        registry = cls()
        registry.register("spe", SpeReader())
        registry.register("npz", NpzReader())
        return registry
