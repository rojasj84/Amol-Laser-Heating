"""Camera acquisition services. No widgets here; every call may block.

``PicamDriverCamera`` talks to the camera through the PICAM driver (LightField
closed). The driver does not know the spectrograph, so a reference SPE supplies
the wavelength axis and readout regions. ``LightFieldCamera`` drives LightField
through its automation interface instead. ``SimulatedCamera`` is used in debug
mode and writes NPZ files.
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
from . import spe
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


def _open_picam_device(serial_number=None, dll_folder=None):
    """Open the camera with pylablib's PICAM wrapper (imported only when needed)."""
    try:
        import pylablib
        from pylablib.devices import PrincetonInstruments
    except ImportError as error:
        raise CameraError("The pylablib package is required: "
                          "python -m pip install pylablib-lightweight") from error
    if dll_folder:
        pylablib.par["devices/dlls/picam"] = str(dll_folder)
    try:
        return PrincetonInstruments.PicamCamera(serial_number)
    except Exception as error:
        raise CameraError(f"Could not open the camera through PICAM ({error}). "
                          "Close LightField if it is running") from error


def _spaced(text: str) -> str:
    """LowNoise -> Low Noise (LightField files and the driver spell enums differently)."""
    return "".join(" " + letter if letter.isupper() and index else letter for index, letter in enumerate(text))


class PicamDriverCamera:
    """PIXIS control through the PICAM driver; captures are written as SPE 3.0.

    One sensor rectangle covering every readout region is read unbinned and
    the regions are cut out of it, so the saved image matches LightField's.
    """

    name = "PICAM driver"

    def __init__(self, reference_path, serial_number=None, dll_folder=None, timeout_seconds: float = 30.0,
                 device_factory: Callable[[], object] | None = None):
        self._reference_path = Path(reference_path)
        self._device_factory = device_factory or (lambda: _open_picam_device(serial_number, dll_folder))
        self._device = None
        self._reference = None
        self._regions = ()
        self._model = "PIXIS"
        self.timeout_seconds = float(timeout_seconds)
        self.experiment_note = ""

    @property
    def connected(self) -> bool:
        return self._device is not None

    @property
    def reference_name(self) -> str:
        return (self._reference.source if self._reference is not None else self._reference_path).name

    def _driver(self, action, *arguments, **options):
        try:
            return action(*arguments, **options)
        except CameraError:
            raise
        except Exception as error:
            raise CameraError(f"Camera driver: {error}") from error

    def _require(self):
        if self._device is None:
            raise CameraError("Camera is not connected")
        return self._device

    def _load_reference(self, path):
        try:
            return spe.read_reference(path)
        except ValueError as error:
            raise CameraError(str(error)) from error

    def _apply_regions(self, regions) -> None:
        """Validate against the sensor and the reference, then set the readout window."""
        device, reference = self._require(), self._reference
        size = tuple(int(value) for value in self._driver(device.get_detector_size))
        if size != (reference.sensor_width, reference.sensor_height):
            raise CameraError(f"{reference.source.name} is from a {reference.sensor_width}x{reference.sensor_height} "
                              f"sensor, but this camera is {size[0]}x{size[1]}")
        try:
            spe.validate_regions(regions, *size)
            spe.region_wavelengths(reference.sensor_wavelengths_nm, regions)
        except ValueError as error:
            raise CameraError(str(error)) from error
        window = spe.readout_window(regions)
        self._settle()
        actual = tuple(int(value) for value in self._driver(device.set_roi, *window, 1, 1))
        if actual != window + (1, 1):
            raise CameraError(f"Camera did not accept the readout region {window} (it set {actual})")
        self._regions = tuple(regions)

    def connect(self) -> None:
        if self._device is not None:
            return
        if self._reference is None:
            self._reference = self._load_reference(self._reference_path)
        self._device = self._device_factory()
        try:
            self._apply_regions(self._regions or self._reference.setup.regions)
            try:
                self._model = str(self._device.get_device_info().model)
            except Exception:
                pass
        except Exception:
            self.close()
            raise
        comms_monitor.log(TARGET, f"PICAM camera opened; wavelengths from {self.reference_name}")

    def close(self) -> None:
        device, self._device = self._device, None
        if device is not None:
            try:
                device.close()
            except Exception as error:
                comms_monitor.log(TARGET, f"PICAM close: {error}", ok=False)

    def set_reference(self, path: str | Path) -> str:
        """Use another SPE for the wavelength axis and readout regions."""
        reference = self._load_reference(path)
        previous = self._reference, self._regions
        self._reference = reference
        if self._device is None:
            self._regions = ()
        else:
            try:
                self._apply_regions(reference.setup.regions)
            except Exception:
                self._reference, self._regions = previous
                raise
        comms_monitor.log(TARGET, f"Wavelength reference {reference.source.name}")
        return reference.source.name

    SETTLE_SECONDS = 5.0
    SETTLE_POLL_SECONDS = 0.02

    def _settle(self) -> None:
        """Wait until the driver agrees that no acquisition is running, then free its buffer.

        The wrapper's own stop waits only 10 ms for the camera to confirm, and
        gives up quietly or with an error. Left like that, the next command is
        refused because the driver still considers an acquisition in progress.
        Errors while stopping are therefore retried until the camera is idle.
        """
        device = self._require()
        deadline = time.monotonic() + self.SETTLE_SECONDS
        problem = None
        while True:
            try:
                if not device.acquisition_in_progress():
                    break
                device.stop_acquisition()
            except Exception as error:
                problem = error
            if time.monotonic() > deadline:
                detail = f" ({problem})" if problem is not None else ""
                raise CameraError(f"The camera did not stop acquiring within {self.SETTLE_SECONDS:g} s{detail}. "
                                  "Disconnecting and reconnecting the camera may be needed")
            time.sleep(self.SETTLE_POLL_SECONDS)
        try:
            device.clear_acquisition()
        except Exception as error:
            comms_monitor.log(TARGET, f"Clear acquisition: {error}", ok=False)

    def _read_one_frame(self, timeout_seconds: float):
        """Single readout. A frame that arrived is kept even if stopping then complains."""
        device = self._require()
        frame = None
        try:
            self._driver(device.setup_acquisition, mode="snap", nframes=1)
            self._driver(device.start_acquisition)
            try:
                device.wait_for_frame(timeout=timeout_seconds)
            except Exception as error:
                if isinstance(error, getattr(device, "TimeoutError", ())):
                    raise CameraError(f"No frame arrived within {timeout_seconds:g} s") from error
                raise CameraError(f"Camera driver while waiting for the frame: {error}") from error
            frame = self._driver(device.read_newest_image)
        finally:
            try:
                self._settle()
            except CameraError:
                if frame is None:
                    raise
                comms_monitor.log(TARGET, "Camera was slow to stop after the frame", ok=False)
        if frame is None:
            raise CameraError("The camera reported a finished acquisition but returned no frame")
        return frame

    def get_exposure_seconds(self) -> float:
        return float(self._driver(self._require().get_exposure))

    def set_exposure_seconds(self, seconds: float) -> None:
        seconds = validate_exposure(seconds)
        self._settle()
        self._driver(self._require().set_exposure, seconds)
        comms_monitor.log(TARGET, f"Exposure {seconds * 1000.0:.2f} ms")

    def _set_attribute(self, name, values) -> bool:
        for value in values:
            try:
                self._device.set_attribute_value(name, value, error_on_missing=True)
                return True
            except Exception:
                continue
        return False

    def load_experiment(self, path: str | Path) -> str:
        """Apply the settings in a LightField .lfe that the driver understands."""
        self._require()
        size = (self._reference.sensor_width, self._reference.sensor_height)
        try:
            setup = spe.read_experiment_file(path, size)
        except ValueError as error:
            raise CameraError(str(error)) from error
        applied, refused = [], []
        if setup.regions:
            self._apply_regions(setup.regions)
            applied.append(f"{len(setup.regions)} region{'s' if len(setup.regions) != 1 else ''}")
        if setup.exposure_seconds is not None:
            self.set_exposure_seconds(setup.exposure_seconds)
            applied.append("exposure")
        for label, name, value in (("ADC speed", "ADC Speed", setup.adc_speed_mhz),
                                   ("gain", "ADC Analog Gain", setup.adc_analog_gain),
                                   ("ADC quality", "ADC Quality", setup.adc_quality)):
            if value is None:
                continue
            values = (value, _spaced(value)) if isinstance(value, str) else (value,)
            (applied if self._set_attribute(name, values) else refused).append(label)
        if not applied and not refused:
            raise CameraError(f"{Path(path).name} contains no camera settings")
        self.experiment_note = "Applied " + (", ".join(applied) or "nothing")
        if refused:
            self.experiment_note += f"; camera refused {', '.join(refused)}"
        comms_monitor.log(TARGET, f"Experiment '{Path(path).stem}': {self.experiment_note}")
        return Path(path).stem

    def acquire(self, folder: str | Path, base_name: str, kind: str = "spectrum") -> Path:
        device = self._require()
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{base_name}.spe"
        if target.exists():
            raise CameraError(f"{target.name} already exists")
        self._settle()
        exposure = self.get_exposure_seconds()
        comms_monitor.log(TARGET, f"Acquire {kind}: {target.name}")
        frame = self._read_one_frame(exposure + self.timeout_seconds)
        reference = self._reference
        try:
            image = spe.assemble_image(frame, self._regions)
            return spe.write_spe(target, image, reference.sensor_wavelengths_nm, self._regions,
                                 (reference.sensor_width, reference.sensor_height), exposure, self._model)
        except (OSError, ValueError) as error:
            raise CameraError(f"Could not save {target.name}: {error}") from error


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


def create_camera(settings, template_loader: Callable[[], CameraData], reference_temperature: float,
                  default_reference: str | Path | None = None):
    """Simulated in debug mode; otherwise the back end named in the profile."""
    if hardware_mode.is_debug():
        return SimulatedCamera(template_loader, reference_temperature, settings.exposure_seconds)
    if settings.backend == "picam":
        reference = settings.reference_file or default_reference
        if reference is None:
            raise ValueError("camera_control needs a reference_file for the PICAM back end")
        return PicamDriverCamera(reference, settings.camera_serial, settings.picam_dll_folder,
                                 settings.acquire_timeout_seconds)
    if settings.backend == "lightfield":
        return LightFieldCamera(timeout_seconds=settings.acquire_timeout_seconds)
    raise ValueError(f"Unknown camera back end {settings.backend!r}")
