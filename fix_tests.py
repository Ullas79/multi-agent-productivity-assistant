import re
with open('test_agents.py', 'r') as f:
    code = f.read()
code = code.replace('/api/tasks', '/api/clinical-tasks')
code = code.replace('/api/events', '/api/appointments')
code = code.replace('/api/notes', '/api/patient-records')
code = code.replace('json={"title": "High P Task", "priority": "high"}', 'json={"title": "High P Task", "patient_name": "Test Patient", "priority": "high"}')
code = code.replace('json={"title": "Low P Task", "priority": "low"}', 'json={"title": "Low P Task", "patient_name": "Test Patient", "priority": "low"}')
code = code.replace('"title": "Future Event"', '"patient_name": "Future Event", "doctor_name": "Dr Test"')
code = code.replace('["title"] == "Sample Event"', '["patient_name"] == "Test Patient"')
code = code.replace('["title"] == "Sample Note"', '["patient_name"] == "Test Patient"')
with open('test_agents.py', 'w') as f:
    f.write(code)
