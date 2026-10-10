"""Camera-independent data passed from readers to analysis code."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class RegionOfInterest:
    """Pixel coordinates with exclusive end bounds, matching NumPy slices."""

    x_start: int
    x_end: int
    y_start: int
    y_end: int

    def validate(self, width: int, height: int) -> None:
        values = (self.x_start, self.x_end, self.y_start, self.y_end)
        if any(type(value) is not int for value in values):
            raise ValueError("ROI bounds must be integers")
        if not (0 <= self.x_start < self.x_end <= width):
            raise ValueError(f"ROI x bounds must fit within the {width}-pixel image width")
        if not (0 <= self.y_start < self.y_end <= height):
            raise ValueError(f"ROI y bounds must fit within the {height}-pixel image height")


@dataclass(frozen=True)
class CameraData:
    """All readers supply (frame, row, column) counts and wavelengths in nm.

    These coordinates describe the saved image after hardware cropping/binning.
    No camera SDK or GUI widget is needed to work with this object.
    """

    frames: np.ndarray
    wavelengths_nm: np.ndarray
    source: Path
    exposure_seconds: float | None = None

    def __post_init__(self) -> None:
        frames = np.asarray(self.frames)
        wavelengths = np.asarray(self.wavelengths_nm, dtype=float)
        if frames.ndim == 2:
            frames = frames[np.newaxis, ...]
        if frames.ndim != 3 or any(size <= 0 for size in frames.shape):
            raise ValueError("Camera frames must have shape (frames, rows, columns)")
        if not (np.issubdtype(frames.dtype, np.integer) or np.issubdtype(frames.dtype, np.floating)):
            raise ValueError("Camera counts must be real numeric values")
        if wavelengths.ndim != 1 or wavelengths.size != frames.shape[2]:
            raise ValueError("One wavelength is required for each image column")
        if not np.all(np.isfinite(wavelengths)) or np.any(wavelengths <= 0):
            raise ValueError("Wavelengths must be finite positive values in nanometers")
        if not np.all(np.diff(wavelengths) > 0):
            raise ValueError("Wavelengths must be strictly increasing")
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "wavelengths_nm", wavelengths)
        object.__setattr__(self, "source", Path(self.source))

    @property
    def frame_count(self) -> int:
        return self.frames.shape[0]

    @property
    def width(self) -> int:
        return self.frames.shape[2]

    @property
    def height(self) -> int:
        return self.frames.shape[1]

    def frame(self, index: int = 0) -> np.ndarray:
        if type(index) is not int or not 0 <= index < self.frame_count:
            raise ValueError(f"Frame index {index} is outside this {self.frame_count}-frame capture")
        return self.frames[index]


@dataclass(frozen=True)
class ExtractedSpectrum:
    wavelengths_nm: np.ndarray
    counts: np.ndarray


@dataclass(frozen=True)
class TemperatureResult:
    temperature_kelvin: float
    uncertainty_kelvin: float
    emissivity: float
    wavelengths_nm: np.ndarray
    raw_counts: np.ndarray
    corrected_counts: np.ndarray
    fitted_counts: np.ndarray
