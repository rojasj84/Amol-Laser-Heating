import csv
import numpy as np

class FestoStateCalibrationsCheck:
    def __init__(self, csv_file_location):
        
        self.festo_states = np.empty(12)
        self.calibration_file_name = np.empty(1)

        with open(csv_file_location, newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            next(csv_reader)  # Skip the header row
            next(csv_reader)  # Skip the header row
            
            for row in csv_reader:
                #print(row[0:12])   
                self.festo_states = np.vstack((self.festo_states, row[0:12]))
                self.calibration_file_name = np.vstack((self.calibration_file_name, row[12:13]))

            self.festo_states = np.delete(self.festo_states, (0), axis=0)
            self.calibration_file_name = np.delete(self.calibration_file_name, (0), axis=0)
    
    def compare_rows_return_calibration_file(self,festo_state):
        rows,cols = self.festo_states.shape

        for i in range (0, rows):
            are_rows_same = (self.festo_states[i, :].astype(int) == festo_state[:]).all()            
            #print(are_rows_same)
            if are_rows_same == True:
                #print(are_rows_same, i)
                return self.calibration_file_name[i]
        

if __name__ == "__main__":

    A_Win = 'TemperatureFit\calibration_file_table.csv'
    A_Lin = 'TemperatureFit/calibration_file_table.csv'

    Calibrations = FestoStateCalibrationsCheck(A_Lin)

    rows,cols = Calibrations.festo_states.shape

    test_list = np.array([1,0,0,1,0,1,0,0,0,0,1,0])
    print(test_list)

    '''for i in range (0, rows):
        #print(Calibrations.festo_states[i,:].astype(int))
        
        are_rows_same = (Calibrations.festo_states[i, :].astype(int) == test_list[:]).all()
        if 
        print(are_rows_same, i)'''
    
    A = Calibrations.compare_rows_return_calibration_file(test_list)
    print(A)

