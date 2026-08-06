import math
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

''' 
    This class takes an input of a calibration file spectrum and temperature to calculate 
    the black body spectrum, transfer function and fit of real spectrum to obtain
    the real temperature from known calibration curves
'''
class Temperature_Measurement(object):
    def __init__(self, init_temp_guess, init_epsilon_guess, calibration_temperature, calibration_wavelength, calibration_temperature_spectrum_counts, unknown_temperature_spectrum_counts):
            
           self.generate_blackbody_spectrum(calibration_temperature, calibration_wavelength)
           self.generate_correction_transfer_function(calibration_temperature_spectrum_counts)
           self.generate_corrected_spectrum_unknown_T(unknown_temperature_spectrum_counts)

           #print(self.black_body_radiance)

           # Fit the corrected spectrum to obtain a temperature
           init_guess = [init_temp_guess, init_epsilon_guess]
           fit_Planck = curve_fit(self.f_Planck, calibration_wavelength, self.unknown_graybody_spectrum, p0=init_guess, maxfev=5000)#, absolute_sigma=True)

           ans,cov = fit_Planck
           
           self.fit_T,self.fit_Eps = ans
           self.sigT, self.sigEps = np.sqrt(np.diag(cov))
           #print ('T = %.2f +/- %.2f' %(self.fit_T, self.sigT))
           #print ('\u03B5 = %.1E +/- %.1E' %(self.fit_Eps, self.sigEps))
           
           self.generate_estimated_temperature_spectrum(calibration_wavelength)

    def f_Planck(self, wavelengths, temperature, epsilon):
        #Constants needed for the calculation
        k = np.float64(1.380649*10**-23)        #J⋅K−1
        c = np.float64(299792458*10**0)         #m/s
        h = np.float64(6.62607015*10**-34)      #J⋅Hz−1

        # Convert wavelength numbers to meters from nanometers
        wavelengths = np.divide(wavelengths,10**9)

        #Calculating Black Body Radiance
        planck_prefactor = np.reciprocal(np.power(wavelengths,5))*2*h*c**2
        planck_occupation_factor = np.reciprocal(np.exp((h*c/(k*temperature))*np.reciprocal(wavelengths))-1)

        return epsilon*planck_prefactor*planck_occupation_factor
        #return epsilon*2*h*(c**2)/(wavelengths**5*(np.exp((h*c)/(wavelengths*k*temperature)) - 1))         

    def generate_blackbody_spectrum(self, temperature, wavelengths):        

        #Call function of black body to generate the black body curve for temperature in the given wavelength
        self.black_body_spectrum= self.f_Planck(wavelengths, temperature, 1)

        b = 2.897771955*10**-3 #m⋅K used for Wien's law to find the maximum lambda
        lambda_maximum = np.array([b/temperature*10**9])
        self.black_body_maximum_radiance = self.f_Planck(lambda_maximum, temperature, 1)
        #print(self.black_body_maximum_radiance)
    
    def generate_correction_transfer_function(self, calibration_temperature_spectrum):

        calibration_spectrum_peak_value = np.max(calibration_temperature_spectrum)
        self.blackbody_peak_value = self.black_body_maximum_radiance[0]

        #normalized black body spectrum
        normalized_blackbody_spectrum = self.black_body_spectrum/self.blackbody_peak_value

        #Correcting for a count exactly equal to 0
        calibration_temperature_spectrum[calibration_temperature_spectrum == 0] = 1
        normalized_calibration_spectrum = calibration_temperature_spectrum/calibration_spectrum_peak_value

        #Normalized transfer function (ideal black body over calibrated)
        self.normalized_transfer_function = normalized_blackbody_spectrum/normalized_calibration_spectrum

    def generate_corrected_spectrum_unknown_T(self, unknown_temperature_counts):
        #Uses the transfer function to convert the unknown spectrum into a corrected black body spectrum
        unknown_spectrum_peak_value = np.max(unknown_temperature_counts)

        #normalized gray body spectrum
        #Correcting for counts less than 1
        unknown_temperature_counts[unknown_temperature_counts == 0] = 1
        unknown_temperature_counts = np.absolute(unknown_temperature_counts)
        normalized_unknown_spectrum = unknown_temperature_counts/unknown_spectrum_peak_value

        #gray body spectrum scaled up to values of a black body after transformation via the normalized transfer function
        self.unknown_graybody_spectrum = normalized_unknown_spectrum*self.normalized_transfer_function*self.blackbody_peak_value
        
    def generate_estimated_temperature_spectrum(self, wavelengths):
        #Uses the transfer function to convert the unknown spectrum into a a corrected black body spectrum     
        self.gray_body_spectrum = self.f_Planck(wavelengths,self.fit_T, self.fit_Eps)
 
 

if __name__ == "__main__":
    
    wavelengths = np.zeros(200)
    
    for i in range(0,len(wavelengths)):
            wavelengths[i] = 100+i*20

    test_spectrum = Temperature_Measurement(2000, 0.5, 5000, wavelengths, wavelengths, wavelengths)

    black_body_spectrum = test_spectrum.normalized_transfer_function

    print(wavelengths[45],black_body_spectrum[45])
    #plt.xscale('log')
    #plt.plot(wavelengths, black_body_spectrum)
    #plt.show()
