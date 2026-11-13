"""Camera acquisition services. No widgets here; every call may block.

``LightFieldCamera`` drives Princeton Instruments LightField through its
automation interface, so the spectrograph wavelength calibration is saved in
each SPE file. ``SimulatedCamera`` is used in debug mode and writes NPZ files.
"""
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from typing import Callable, Protocol

import numpy as np

import comms_monitor
import hardware_mode
from TemperatureFit.TemperatureFitting import Temperature_Measurement
from .models import CameraData

CAPTURE_KINDS = ("spectrum", "background", "flatfield")
TARGET = "PIXIS camera"


class CameraError(RuntimeError):
    """A camera operation failed; the message is suitable for the status line."""


class CameraController(Protocol):
    name: str
    connected: bool

    def connect(self) -> None: ...
    def close(self) -> None: ...
    def get_exposure_seconds(self) -> float: ...
    def set_exposure_seconds(self, seconds: float) -> None: ...
    def load_experiment(self, path: str | Path) -> str: ...
    def acquire(self, folder: str | Path, base_name: str, kind: str = "spectrum") -> Path: ...


def validate_exposure(seconds: float) -> float:
    seconds = float(seconds)
    if not np.isfinite(seconds) or seconds <= 0:
        raise CameraError("Exposure time must be a positive number")
    return seconds


def _open_lightfield_session():
    """Start LightField and return the automation objects this module uses."""
    root = os.environ.get("LIGHTFIELD_ROOT")
    if not root or not Path(root).is_dir():
        raise CameraError("LightField is not installed here (LIGHTFIELD_ROOT is not set)")
    try:
        import clr  # pythonnet
    except ImportError as error:
        raise CameraError("The pythonnet package is required: python -m pip install pythonnet") from error
    for folder in (root, str(Path(root) / "AddInViews")):
        if folder not in sys.path:
            sys.path.append(folder)
    try:
        clr.AddReference("PrincetonInstruments.LightFieldViewV5")
        clr.AddReference("PrincetonInstruments.LightField.AutomationV5")
        clr.AddReference("PrincetonInstruments.LightFieldAddInSupportServices")
        from System import String
        from System.Collections.Generic import List
        from PrincetonInstruments.LightField.Automation import Automation
        from PrincetonInstruments.LightField.AddIns import CameraSettings, ExperimentSettings
        automation = Automation(True, List[String]())
    except CameraError:
        raise
    except Exception as error:
        raise CameraError(f"Could not start LightField automation: {error}") from error
    return SimpleNamespace(
        experiment=automation.LightFieldApplication.Experiment,
        dispose=automation.Dispose,
        exposure_ms=CameraSettings.ShutterTimingExposureTime,
        directory=ExperimentSettings.FileNameGenerationDirectory,
        base_name=ExperimentSettings.FileNameGenerationBaseFileName,
        attach_increment=ExperimentSettings.FileNameGenerationAttachIncrement,
        attach_date=ExperimentSettings.FileNameGenerationAttachDate,
        attach_time=ExperimentSettings.FileNameGenerationAttachTime,
        frames=ExperimentSettings.AcquisitionFramesToStore,
    )


class LightFieldCamera:
    """PIXIS control through a LightField instance owned by this application."""

    name = "LightField"
    POLL_SECONDS = 0.05

    def __init__(self, session_factory: Callable[[], object] | None = None, timeout_seconds: float = 30.0):
        self._session_factory = session_factory or _open_lightfield_session
        self._session = None
        self.timeout_seconds = float(timeout_seconds)

    @property
    def connected(self) -> bool:
        return self._session is not None

    def connect(self) -> None:
        if self._session is None:
            self._session = self._session_factory()
            comms_monitor.log(TARGET, "LightField automation started")

    def close(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            try:
                session.dispose()
            except Exception as error:  # LightField may already have been closed by hand
                comms_monitor.log(TARGET, f"LightField close: {error}", ok=False)

    def _require(self):
        if self._session is None:
            raise CameraError("Camera is not connected")
        return self._session

    def _set(self, setting, value) -> None:
        experiment = self._require().experiment
        if not experiment.Exists(setting):
            raise CameraError(f"LightField experiment has no setting {setting}")
        experiment.SetValue(setting, value)

    def get_exposure_seconds(self) -> float:
        session = self._require()
        return float(session.experiment.GetValue(session.exposure_ms)) / 1000.0

    def set_exposure_seconds(self, seconds: float) -> None:
        seconds = validate_exposure(seconds)
        self._set(self._require().exposure_ms, seconds * 1000.0)
        comms_monitor.log(TARGET, f"Exposure {seconds * 1000.0:.2f} ms")

    def load_experiment(self, path: str | Path) -> str:
        """LightField loads saved experiments by name from its own folder."""
        experiment = self._require().experiment
        name = Path(path).stem
        saved = [str(item) for item in experiment.GetSavedExperiments()]
        if name not in saved:
            raise CameraError(f"'{name}' is not in LightField's Experiments folder; "
                              "save the experiment from LightField first")
        experiment.Load(name)
        comms_monitor.log(TARGET, f"Experiment '{name}' loaded")
        return name

    def acquire(self, folder: str | Path, base_name: str, kind: str = "spectrum") -> Path:
        session = self._require()
        experiment = session.experiment
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{base_name}.spe"
        if target.exists():
            raise CameraError(f"{target.name} already exists")
        if not experiment.IsReadyToRun:
            raise CameraError("LightField is not ready to acquire (check the camera in LightField)")
        self._set(session.directory, str(folder))
        self._set(session.base_name, base_name)
        for setting in (session.attach_increment, session.attach_date, session.attach_time):
            self._set(setting, False)
        try:
            frames = max(1, int(experiment.GetValue(session.frames)))
        except Exception:
            frames = 1
        deadline = time.monotonic() + self.timeout_seconds + frames * self.get_exposure_seconds()
        comms_monitor.log(TARGET, f"Acquire {kind}: {target.name}")
        experiment.Acquire()
        # Acquire() returns immediately; the file appearing also covers the
        # moment before LightField reports that it is running.
        while experiment.IsRunning or not target.is_file():
            if time.monotonic() > deadline:
                if experiment.IsRunning:
                    experiment.Stop()
                raise CameraError("Timed out waiting for LightField to finish the acquisition")
            time.sleep(self.POLL_SECONDS)
        return target


class SimulatedCamera:
    """Debug-mode camera: plausible frames on the profile's wavelength grid."""

    name = "Simulated camera"
    DARK_COUNTS = 100.0
    NOISE_COUNTS = 2.0
    SAMPLE_TEMPERATURE = 1800.0

    def __init__(self, template_loader: Callable[[], CameraData], reference_temperature: float,
                 exposure_seconds: float = 0.1, seed: int | None = None):
        self._template_loader = template_loader
        self._template = None
        self.reference_temperature = float(reference_temperature)
        self._exposure = validate_exposure(exposure_seconds)
        self._reference_exposure = self._exposure
        self._random = np.random.default_rng(seed)
        self.connected = False

    def _log(self, message: str) -> None:
        if not hardware_mode.simulate_command(TARGET, message):
            comms_monitor.log(TARGET, f"[SIMULATED] {message}")

    def connect(self) -> None:
        if not self.connected:
            self._template = self._template_loader()
            self.connected = True
            self._log("Connect")

    def close(self) -> None:
        self.connected = False

    def _require(self) -> CameraData:
        if not self.connected:
            raise CameraError("Camera is not connected")
        return self._template

    def get_exposure_seconds(self) -> float:
        self._require()
        return self._exposure

    def set_exposure_seconds(self, seconds: float) -> None:
        self._require()
        self._exposure = validate_exposure(seconds)
        self._log(f"Exposure {self._exposure * 1000.0:.2f} ms")

    def load_experiment(self, path: str | Path) -> str:
        self._require()
        name = Path(path).stem
        self._log(f"Load experiment '{name}'")
        return name

    def acquire(self, folder: str | Path, base_name: str, kind: str = "spectrum") -> Path:
        template = self._require()
        if kind not in CAPTURE_KINDS:
            raise CameraError(f"Unknown capture kind {kind!r}")
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{base_name}.npz"
        if target.exists():
            raise CameraError(f"{target.name} already exists")
        shape = (template.height, template.width)
        frame = self.DARK_COUNTS + self._random.normal(0.0, self.NOISE_COUNTS, shape)
        if kind != "background":
            lamp = np.clip(np.asarray(template.frame(0), dtype=float), 0.0, None)
            if kind == "spectrum":
                planck = Temperature_Measurement.f_Planck
                lamp = lamp * (planck(None, template.wavelengths_nm, self.SAMPLE_TEMPERATURE, 1.0) /
                               planck(None, template.wavelengths_nm, self.reference_temperature, 1.0))
            frame = frame + lamp * (self._exposure / self._reference_exposure)
        np.savez(target, frames=frame, wavelengths_nm=template.wavelengths_nm,
                 exposure_seconds=self._exposure)
        self._log(f"Acquire {kind}: {target.name}")
        return target


def create_camera(settings, template_loader: Callable[[], CameraData], reference_temperature: float):
    """Simulated in debug mode; otherwise the back end named in the profile."""
    if hardware_mode.is_debug():
        return SimulatedCamera(template_loader, reference_temperature, settings.exposure_seconds)
    if settings.backend == "lightfield":
        return LightFieldCamera(timeout_seconds=settings.acquire_timeout_seconds)
    raise ValueError(f"Unknown camera back end {settings.backend!r}")
