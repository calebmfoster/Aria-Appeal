# Backend Testing
 
 This directory contains tests for the backend application.
 
 ## Test Files
 
 -   `test_import_app.py`: Verifies that the FastAPI application instance can be imported successfully, checking for configuration errors.
 -   `test_manual_generation.py`: Manually tests the LLM generation service logic, including mock responses to verify JSON parsing.
 -   `test_settings.py`: Tests the Settings API endpoints (`GET` and `POST`) and verifies that configuration changes are persisted.
 
 ## Running Tests
 
 To run the tests, navigate to the `backend` directory and execute:
 
 ```bash
 python tests/test_import_app.py
 python tests/test_manual_generation.py
 python tests/test_settings.py
 ```
 
 Ensure your virtual environment is activated before running tests.
