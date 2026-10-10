"""Spectrum extraction and temperature fitting, independent of Tk and hardware."""
import numpy as np

from TemperatureFit.TemperatureFitting import Temperature_Measurement
from .models import CameraData, ExtractedSpectrum, RegionOfInterest, TemperatureResult


def extract_spectrum(data: CameraData, roi: RegionOfInterest, frame_index: int = 0) -> ExtractedSpectrum:
    roi.validate(data.width, data.height)
    image = data.frame(frame_index)
    counts = np.sum(image[roi.y_start:roi.y_end, roi.x_start:roi.x_end], axis=0, dtype=float)
    return ExtractedSpectrum(data.wavelengths_nm[roi.x_start:roi.x_end], counts)


def fit_temperature(measurement: CameraData, calibration: CameraData, roi: RegionOfInterest,
                    calibration_temperature: float, frame_index: int = 0) -> TemperatureResult:
    measured = extract_spectrum(measurement, roi, frame_index)
    reference = extract_spectrum(calibration, roi)
    if measured.wavelengths_nm.shape != reference.wavelengths_nm.shape or not np.allclose(
            measured.wavelengths_nm, reference.wavelengths_nm, rtol=1e-7, atol=1e-5):
        raise ValueError("Measurement and calibration wavelength grids differ; select a matching calibration")
    if not np.isfinite(calibration_temperature) or calibration_temperature <= 0:
        raise ValueError("Calibration temperature must be positive and finite")
    # Preserve the established Planck fit and its initial guesses. Scientific
    # changes can be reviewed independently from this structural refactor.
    fit = Temperature_Measurement(1500, 0.5, calibration_temperature,
                                  measured.wavelengths_nm, reference.counts, measured.counts)
    return TemperatureResult(float(fit.fit_T), float(fit.sigT), float(fit.fit_Eps),
                             measured.wavelengths_nm, measured.counts,
                             fit.unknown_graybody_spectrum, fit.gray_body_spectrum)
