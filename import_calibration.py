import csv
import re
from pathlib import Path
import numpy as np


# Resolve only files for this calibration session and the requested optical state.
CALIBRATION_ROOT = Path(__file__).resolve().parent / "TemperatureFit" / "T_Calib_20250314"


def resolve_calibration_file(calib_name, base_dir=None):
    """Return an existing processed SPE file, or None for unavailable states.

    Known spelling and exposure suffixes may vary; side, magnification, iris,
    and filter combination must match. Equally ranked files are ambiguous.
    """
    if not calib_name or not str(calib_name).strip():
        return None
    name = str(calib_name).strip()
    stem = name[:-4] if name.lower().endswith(".spe") else name
    state = re.fullmatch(r"([LR])_\d+K_(15x|20x)_(wI|woI)(?:_T\d+(?:T\d+)*)?", stem)
    if state is None:
        return None
    side, magnification = state.group(1, 2)
    root = Path(base_dir) if base_dir is not None else CALIBRATION_ROOT
    mag_folder = root / f"{magnification}Mag"
    preferred_folder = mag_folder / f"{magnification}{side}"

    def normalize(value):
        return value.replace("_T7050", "_T70T50").replace("_T7010", "_T70T10")

    candidates = []
    for candidate in mag_folder.rglob("*"):
        if not candidate.is_file() or candidate.suffix.lower() != ".spe":
            continue
        # A raw companion or a different filter combination never substitutes
        # for a missing processed calibration.
        file_stem = re.sub(r"_\d+(?:\.\d+)?(?:ms|s)$", "", candidate.stem)
        if normalize(file_stem) != normalize(stem):
            continue
        rank = (candidate.stem != file_stem,
                candidate.parent != preferred_folder,
                file_stem != stem)
        candidates.append((rank, candidate))
    if not candidates:
        return None
    best_rank = min(rank for rank, _ in candidates)
    best = [candidate for rank, candidate in candidates if rank == best_rank]
    return best[0].resolve() if len(best) == 1 else None

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
                name = str(self.calibration_file_name[i, 0]).strip()
                return np.array([name]) if name else None
        

if __name__ == "__main__":

    windows_path_example = r'TemperatureFit\calibration_file_table.csv'
    linux_path_example = 'TemperatureFit/calibration_file_table.csv'

    Calibrations = FestoStateCalibrationsCheck(linux_path_example)

    rows,cols = Calibrations.festo_states.shape

    test_list = np.array([1,0,0,1,0,1,0,0,0,0,1,0])
    print(test_list)

    matched_calibration_file = Calibrations.compare_rows_return_calibration_file(test_list)
    print(matched_calibration_file)

