import sys
import os
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app.main import app
    print("Import app.main successful")
except Exception as e:
    import traceback
    with open("import_error.log", "w") as f:
        traceback.print_exc(file=f)
    print("Error written to import_error.log")
