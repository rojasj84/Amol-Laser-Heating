@echo off
python "%~dp0main.py" 
if errorlevel 1 pause
start "" "C:\Users\LabUserR129\AppData\Local\Programs\Python\Python310\python.exe" "C:\Pyhon310Venv\venvfolder\simple_pyspin-master\examples\FLIR_4_Cam_Control_4_chatGPT_20260427_AllGreat.py"
exit
