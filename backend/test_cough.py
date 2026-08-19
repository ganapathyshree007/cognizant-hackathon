import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('d:\\cognizant-hackathon-main\\UC07_FINAL_RUNTIME\\backend'))

from safety_gate_engine import SafetyGateEngine

engine = SafetyGateEngine()
data = {
    'Temperature': 98.6,
    'Heart Rate': 75,
    'SpO2': 98,
    'Systolic BP': 120,
    'Respiratory Rate': 16,
    'AVPU': 'A',
    'Cough': True
}

result = engine.evaluate(data)
print("RESULT:", result)
