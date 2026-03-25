import os
import pytest
from unittest.mock import Mock, patch
import requests

def test_get_barentswatch_token_success():
    """Test successful token retrieval from Barentswatch API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'access_token': 'test_bearer_token_123',
        'expires_in': 3600
    }

    with patch('requests.post', return_value=mock_response):
        with patch.dict(os.environ, {
            'BARENTSWATCH_CLIENT_ID': 'test_id',
            'BARENTSWATCH_CLIENT_SECRET': 'test_secret'
        }):
            from ferry_api import get_barentswatch_token
            token = get_barentswatch_token()
            assert token == 'test_bearer_token_123'

def test_get_barentswatch_token_missing_credentials():
    """Test error handling for missing credentials"""
    with patch.dict(os.environ, {}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_ID"):
            get_barentswatch_token()
