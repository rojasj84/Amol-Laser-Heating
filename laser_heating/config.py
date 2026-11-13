"""Validated application configuration; all saved paths are relative to the config."""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path

from .models import CameraData, RegionOfInterest

APP_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CameraProfile:
    name: str = "Acton-PIXIS 400"
    reader: str = "spe"
    width: int = 1340
    height: int = 70
    left_roi: RegionOfInterest = field(default_factory=lambda: RegionOfInterest(1, 1339, 0, 34))
    right_roi: RegionOfInterest = field(default_factory=lambda: RegionOfInterest(1, 1339, 35, 69))

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int or min(self.width, self.height) <= 0:
            raise ValueError("Camera image dimensions must be positive integers")
        if not self.name or not self.reader:
            raise ValueError("Camera name and reader are required")
        self.left_roi.validate(self.width, self.height)
        self.right_roi.validate(self.width, self.height)

    def validate_data(self, data: CameraData) -> None:
        if (data.width, data.height) != (self.width, self.height):
            raise ValueError(f"{self.name} expects {self.width}x{self.height} saved-image pixels, "
                             f"but {data.source.name} contains {data.width}x{data.height}")


@dataclass
class HardwareSettings:
    agilis_port: str = "COM11"
    left_relay_port: str = "COM7"
    right_relay_port: str = "COM6"
    left_laser_ip: str = "192.168.1.100"
    right_laser_ip: str = "192.168.0.100"


@dataclass(frozen=True)
class CalibrationSettings:
    root: Path = APP_ROOT / "TemperatureFit" / "T_Calib_20250314"
    left_table: Path = APP_ROOT / "TemperatureFit" / "calibration_file_table_left_side.csv"
    right_table: Path = APP_ROOT / "TemperatureFit" / "calibration_file_table_right_side.csv"
    left_file: Path = APP_ROOT / "TemperatureFit" / "T_Calib_20250314" / "15xMag" / "L_2255K_15x_wI.spe"
    right_file: Path = APP_ROOT / "TemperatureFit" / "T_Calib_20250314" / "15xMag" / "R_2255K_15x_wI.spe"
    temperature_kelvin: float = 2255
    use_filter_table: bool = True


    def __post_init__(self) -> None:
        if not math.isfinite(self.temperature_kelvin) or self.temperature_kelvin <= 0:
            raise ValueError("Calibration temperature must be positive and finite")
        if type(self.use_filter_table) is not bool:
            raise ValueError("use_filter_table must be a JSON boolean")


@dataclass(frozen=True)
class CameraControlSettings:
    """Direct acquisition. Debug mode always uses the simulated camera."""

    backend: str = "lightfield"
    exposure_seconds: float = 0.1
    acquire_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.backend != "lightfield":
            raise ValueError(f"Unknown camera_control backend {self.backend!r}")
        for name in ("exposure_seconds", "acquire_timeout_seconds"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or not math.isfinite(value) or value <= 0:
                raise ValueError(f"camera_control {name} must be a positive number")


@dataclass
class ApplicationConfig:
    camera: CameraProfile = field(default_factory=CameraProfile)
    hardware: HardwareSettings = field(default_factory=HardwareSettings)
    calibration: CalibrationSettings = field(default_factory=CalibrationSettings)
    acquisition_folder: Path = APP_ROOT / "TemperatureFit"
    initial_measurement: Path | None = None
    camera_control: CameraControlSettings = field(default_factory=CameraControlSettings)

    @classmethod
    def load(cls, path: str | Path) -> "ApplicationConfig":
        path = Path(path).resolve()
        with path.open(encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            raise ValueError("Application configuration must be a JSON object")
        if raw.get("schema_version") != 1:
            raise ValueError("Configuration schema_version must be 1")
        camera = dict(raw.get("camera", {}))
        for side in ("left", "right"):
            key = f"{side}_roi"
            if key in camera:
                camera[key] = RegionOfInterest(**camera[key])
        calibration = dict(raw.get("calibration", {}))
        for key in ("root", "left_table", "right_table", "left_file", "right_file"):
            if key in calibration:
                calibration[key] = (path.parent / calibration[key]).resolve()
        folder = (path.parent / raw["acquisition_folder"]).resolve() if "acquisition_folder" in raw else APP_ROOT / "TemperatureFit"
        measurement = (path.parent / raw["initial_measurement"]).resolve() if raw.get("initial_measurement") else None
        return cls(CameraProfile(**camera), HardwareSettings(**raw.get("hardware", {})),
                   CalibrationSettings(**calibration), folder, measurement,
                   CameraControlSettings(**raw.get("camera_control", {})))
