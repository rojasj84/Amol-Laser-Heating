import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Pre-calculate physical constants for Planck function (T-Rax Speedup)
_k = np.float64(1.380649e-23)       # J/K
_c = np.float64(299792458.0)        # m/s
_h = np.float64(6.62607015e-34)     # J*s

# c1 = 2 * h * c^2
_c1 = 2.0 * _h * (_c ** 2) 
# c2 = h * c / k
_c2 = (_h * _c) / _k

''' 
    This class takes an input of a calibration file spectrum and temperature to calculate 
    the black body spectrum, transfer function and fit of real spectrum to obtain
    the real temperature from known calibration curves
    
    If an external 'etalon_spectrum' array is provided, it replaces the theoretical 
    Planck curve calculation for the calibration lamp.
'''
class Temperature_Measurement(object):
    def __init__(self, init_temp_guess, init_epsilon_guess, calibration_temperature, calibration_wavelength, calibration_temperature_spectrum_counts, unknown_temperature_spectrum_counts, etalon_spectrum=None):
            
           self.generate_blackbody_spectrum(calibration_temperature, calibration_wavelength, etalon_spectrum)
           self.generate_correction_transfer_function(calibration_temperature_spectrum_counts)
           self.generate_corrected_spectrum_unknown_T(unknown_temperature_spectrum_counts)

           # Fit the corrected spectrum to obtain a temperature
           init_guess = [init_temp_guess, init_epsilon_guess]
           
           # Filter out NaN values before fitting to prevent scipy errors (T-Rax NaN-safe division handling)
           valid_idx = ~np.isnan(self.unknown_graybody_spectrum)
           fit_wavelengths = calibration_wavelength[valid_idx]
           fit_spectrum = self.unknown_graybody_spectrum[valid_idx]

           # If we masked everything (bad data), return NaNs
           if len(fit_wavelengths) == 0:
               self.fit_T, self.fit_Eps = np.nan, np.nan
               self.sigT, self.sigEps = np.nan, np.nan
               self.gray_body_spectrum = np.full_like(calibration_wavelength, np.nan)
               return

           fit_Planck = curve_fit(self.f_Planck, fit_wavelengths, fit_spectrum, p0=init_guess, maxfev=5000)

           ans, cov = fit_Planck
           
           self.fit_T, self.fit_Eps = ans
           
           # Protect against infinite covariance
           if not np.isinf(cov).all():
               self.sigT, self.sigEps = np.sqrt(np.diag(cov))
           else:
               self.sigT, self.sigEps = np.nan, np.nan
           
           self.generate_estimated_temperature_spectrum(calibration_wavelength)

    def f_Planck(self, wavelengths, temperature, epsilon):
        # Convert wavelength numbers to meters from nanometers
        wavelengths_m = np.divide(wavelengths, 1e9)

        # Calculating Black Body Radiance using pre-computed constants (T-Rax Method)
        planck_prefactor = _c1 * np.reciprocal(np.power(wavelengths_m, 5))
        
        # Suppress overflow warnings during curve_fit probing
        with np.errstate(over='ignore'):
            planck_occupation_factor = np.reciprocal(np.exp(_c2 / (temperature * wavelengths_m)) - 1.0)

        return epsilon * planck_prefactor * planck_occupation_factor

    def generate_blackbody_spectrum(self, temperature, wavelengths, etalon_spectrum=None):        
        if etalon_spectrum is not None:
            # Use empirical lamp curve if provided (T-Rax Etalon Support)
            self.black_body_spectrum = np.array(etalon_spectrum)
            self.black_body_maximum_radiance = np.max(self.black_body_spectrum)
        else:
            # Fallback to theoretical Planck Blackbody
            self.black_body_spectrum = self.f_Planck(wavelengths, temperature, 1.0)
            
            # Wien's law to find max radiance theoretical peak
            b = 2.897771955e-3 # m*K
            lambda_maximum = np.array([b / temperature * 1e9])
            self.black_body_maximum_radiance = self.f_Planck(lambda_maximum, temperature, 1.0)[0]
    
    def generate_correction_transfer_function(self, calibration_temperature_spectrum):
        self.blackbody_peak_value = self.black_body_maximum_radiance
        
        # Avoid division by zero artifacts using np.where and NaN padding
        safe_calib = np.where(calibration_temperature_spectrum <= 0, np.nan, calibration_temperature_spectrum)
        
        # T-Rax Method: Transfer function mapping Empirical Counts to Theoretical Curve directly
        # Inverse Transfer Function (Response Y) = Empirical Counts / Theoretical Blackbody
        with np.errstate(invalid='ignore', divide='ignore'):
            self.response_y = safe_calib / self.black_body_spectrum

    def generate_corrected_spectrum_unknown_T(self, unknown_temperature_counts):
        # Prevent zero-values from breaking math using NaNs instead of hardcoded 1s
        safe_unknown = np.where(unknown_temperature_counts <= 0, np.nan, unknown_temperature_counts)
        
        # Apply inverse transfer function (T-Rax method)
        with np.errstate(invalid='ignore'):
            corrected_y = safe_unknown / self.response_y
        
        # T-Rax Scaling approach: Scale back to the peak of the UNKNOWN sample's CCD counts
        unknown_spectrum_peak_value = np.nanmax(safe_unknown)
        corrected_peak_value = np.nanmax(corrected_y)
        
        if np.isnan(corrected_peak_value) or corrected_peak_value == 0:
            self.unknown_graybody_spectrum = corrected_y
        else:
            self.unknown_graybody_spectrum = (corrected_y / corrected_peak_value) * unknown_spectrum_peak_value
        
    def generate_estimated_temperature_spectrum(self, wavelengths):
        # Uses the fitted parameters to generate the estimated spectrum for plotting
        self.gray_body_spectrum = self.f_Planck(wavelengths, self.fit_T, self.fit_Eps)
 

if __name__ == "__main__":
    
    wavelengths = np.linspace(400, 900, 200)
    
    # Synthetic empirical data test
    test_spectrum = Temperature_Measurement(2000, 0.5, 2255, wavelengths, wavelengths*10, wavelengths*15)

    print("Sample Output at index 45:")
    print("Wavelength:", wavelengths[45])
    print("Corrected Y:", test_spectrum.unknown_graybody_spectrum[45])
    print("Fitted Temperature:", test_spectrum.fit_T)

