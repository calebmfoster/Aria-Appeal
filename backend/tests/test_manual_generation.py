import sys
import os
from unittest.mock import MagicMock, patch
import json

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm import LLMService

def test_llm_parsing():
    print("Testing LLM Response Parsing...")
    
    mock_response_content = json.dumps([
        {"text": "Sentence 1.", "duration_estimate": 2.0},
        {"text": "Sentence 2.", "duration_estimate": 3.5}
    ])
    
    with patch('app.services.llm.client.chat.completions.create') as mock_create:
        mock_create.return_value.choices = [
            MagicMock(message=MagicMock(content=mock_response_content))
        ]
        
        sentences = LLMService.generate_script("Donors", "Clean Water", "Hope")
        
        assert len(sentences) == 2
        assert sentences[0].text == "Sentence 1."
        print("SUCCESS: Parsed JSON array correctly.")

def test_llm_parsing_wrapper():
    print("Testing LLM Response Parsing with Wrapper...")
    
    mock_response_content = json.dumps({
        "script": [
            {"text": "Sentence 1.", "duration_estimate": 2.0}
        ]
    })
    
    with patch('app.services.llm.client.chat.completions.create') as mock_create:
        mock_create.return_value.choices = [
            MagicMock(message=MagicMock(content=mock_response_content))
        ]
        
        sentences = LLMService.generate_script("Donors", "Clean Water", "Hope")
        
        assert len(sentences) == 1
        assert sentences[0].text == "Sentence 1."
        print("SUCCESS: Parsed JSON object wrapper correctly.")

if __name__ == "__main__":
    try:
        test_llm_parsing()
        test_llm_parsing_wrapper()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"FAILED: {e}")
        exit(1)
