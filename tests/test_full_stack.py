"""
Full stack integration tests for ferry startup refresh
"""
import pytest
import sys
from unittest.mock import patch, Mock
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_complete_ferry_integration_workflow():
    """Test complete ferry integration from CSV to API to app startup"""
    # Mock API response
    mock_token_response = Mock()
    mock_token_response.json.return_value = {"access_token": "test-token", "expires_in": 3600}
    mock_token_response.status_code = 200

    mock_positions_response = Mock()
    mock_positions_response.json.return_value = [
        {
            "mmsi": 257122880,
            "latitude": 59.456,
            "longitude": 10.789,
            "timestamp": "2024-01-01T12:00:00Z"
        }
    ]
    mock_positions_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response) as mock_post, \
         patch('requests.get', return_value=mock_positions_response) as mock_get, \
         patch.dict('os.environ', {'BARENTSWATCH_CLIENT_ID': 'test_id', 'BARENTSWATCH_CLIENT_SECRET': 'test_secret'}):

        import ferry_api
        from unittest.mock import MagicMock

        # Mock routing and nsr modules before importing app to avoid type hint issues
        mock_graph = MagicMock()
        mock_graph.number_of_nodes.return_value = 100
        mock_graph.number_of_edges.return_value = 200
        mock_routing = MagicMock()
        mock_routing.build_graph = MagicMock(return_value=(mock_graph, MagicMock(), []))
        mock_nsr = MagicMock()
        mock_nsr.fetch_quays = MagicMock()
        mock_nsr.get_quays_dict = MagicMock(return_value={})
        mock_dotenv = MagicMock()
        mock_dotenv.load_dotenv = MagicMock()

        sys.modules['routing'] = mock_routing
        sys.modules['nsr'] = mock_nsr
        sys.modules['dotenv'] = mock_dotenv

        try:
            # Test CSV loading
            csv_path = Path(__file__).parent.parent / "data" / "ferries.csv"
            ferries = ferry_api.load_ferry_data_from_csv(csv_path)
            assert len(ferries) > 0
            assert any(ferry['mmsi'] == '257122880' for ferry in ferries)

            # Test API integration
            result = ferry_api.refresh_ferry_positions(csv_path)
            assert len(result) == 1
            assert result[0]['name'] == 'BASTØ ELECTRIC'
            assert result[0]['mmsi'] == '257122880'

            # Test app startup integration
            import app
            app._ferries = []
            app.startup()
            assert len(app._ferries) == 1
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_error_handling_throughout_stack():
    """Test error handling at each layer of the stack"""
    csv_path = Path(__file__).parent.parent / "data" / "ferries.csv"

    # Test OAuth2 failure
    with patch('requests.post', side_effect=Exception("Network error")):
        import ferry_api
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []

    # Test API failure
    mock_token_response = Mock()
    mock_token_response.json.return_value = {"access_token": "test-token"}
    mock_token_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response), \
         patch('requests.get', side_effect=Exception("API error")):
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []

    # Test app startup with API failure
    from unittest.mock import MagicMock

    # Mock routing and nsr modules before importing app to avoid type hint issues
    mock_routing = MagicMock()
    mock_routing.build_graph = MagicMock(return_value=(MagicMock(), MagicMock(), []))
    mock_nsr = MagicMock()
    mock_nsr.fetch_quays = MagicMock()
    mock_nsr.get_quays_dict = MagicMock(return_value={})
    mock_dotenv = MagicMock()
    mock_dotenv.load_dotenv = MagicMock()

    sys.modules['routing'] = mock_routing
    sys.modules['nsr'] = mock_nsr
    sys.modules['dotenv'] = mock_dotenv

    with patch('ferry_api.refresh_ferry_positions', side_effect=Exception("API Error")):
        try:
            import app
            app._ferries = []
            app.startup()  # Should not crash
            assert app._ferries == []
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_production_readiness_checks():
    """Test production readiness aspects"""
    from unittest.mock import MagicMock
    import os

    # Test environment variable handling
    with patch.dict('os.environ', {}, clear=True):
        # Missing environment variables should be handled gracefully
        import ferry_api
        result = ferry_api.refresh_ferry_positions(Path("data/ferries.csv"))
        assert result == []

    # Test CSV file missing
    missing_path = Path("nonexistent.csv")
    result = ferry_api.refresh_ferry_positions(missing_path)
    assert result == []

    # Test app startup with missing dependencies
    # Mock routing and nsr modules before importing app to avoid type hint issues
    mock_routing = MagicMock()
    mock_routing.build_graph = MagicMock(return_value=(MagicMock(), MagicMock(), []))
    mock_nsr = MagicMock()
    mock_nsr.fetch_quays = MagicMock()
    mock_nsr.get_quays_dict = MagicMock(return_value={})
    mock_dotenv = MagicMock()
    mock_dotenv.load_dotenv = MagicMock()

    sys.modules['routing'] = mock_routing
    sys.modules['nsr'] = mock_nsr
    sys.modules['dotenv'] = mock_dotenv

    with patch('ferry_api.refresh_ferry_positions', return_value=[]):
        try:
            import app
            app.startup()
            assert app._ferries == []
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_ferry_data_persistence_across_endpoints():
    """Test that ferry data loaded at startup is accessible via endpoints"""
    mock_ferries = [
        {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456},
        {'name': 'BASTØ ELECTRIC', 'mmsi': '257122880', 'lat': 59.456, 'lon': 10.789}
    ]

    from unittest.mock import MagicMock

    # Mock routing and nsr modules before importing app
    mock_graph = MagicMock()
    mock_graph.number_of_nodes.return_value = 100
    mock_graph.number_of_edges.return_value = 200
    mock_routing = MagicMock()
    mock_routing.build_graph = MagicMock(return_value=(mock_graph, MagicMock(), []))
    mock_nsr = MagicMock()
    mock_nsr.fetch_quays = MagicMock()
    mock_nsr.get_quays_dict = MagicMock(return_value={})
    mock_dotenv = MagicMock()
    mock_dotenv.load_dotenv = MagicMock()

    sys.modules['routing'] = mock_routing
    sys.modules['nsr'] = mock_nsr
    sys.modules['dotenv'] = mock_dotenv

    with patch('ferry_api.refresh_ferry_positions', return_value=mock_ferries):
        try:
            import app
            app.startup()

            # Test that ferry count is reflected in status endpoint
            client = app.app.test_client()
            response = client.get('/api/status')

            assert response.status_code == 200
            status_data = response.get_json()
            assert status_data['ferry_count'] == 2

            # Verify internal state matches
            assert len(app._ferries) == 2
            assert app._ferries[0]['name'] == 'BARØY'

        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_ferry_api_timeout_handling():
    """Test that API timeouts are handled gracefully"""
    import requests
    from unittest.mock import MagicMock

    csv_path = Path(__file__).parent.parent / "data" / "ferries.csv"

    # Test token request timeout
    with patch('requests.post', side_effect=requests.exceptions.Timeout("Token timeout")):
        import ferry_api
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []

    # Test positions request timeout
    mock_token_response = Mock()
    mock_token_response.json.return_value = {"access_token": "test-token"}
    mock_token_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response), \
         patch('requests.get', side_effect=requests.exceptions.Timeout("Positions timeout")):
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []


def test_malformed_api_responses():
    """Test handling of malformed API responses"""
    csv_path = Path(__file__).parent.parent / "data" / "ferries.csv"

    # Test malformed token response
    mock_token_response = Mock()
    mock_token_response.json.side_effect = ValueError("Invalid JSON")
    mock_token_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response):
        import ferry_api
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []

    # Test missing access_token in response
    mock_token_response = Mock()
    mock_token_response.json.return_value = {"expires_in": 3600}  # Missing access_token
    mock_token_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response):
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []

    # Test malformed positions response
    mock_token_response = Mock()
    mock_token_response.json.return_value = {"access_token": "test-token"}
    mock_token_response.status_code = 200

    mock_positions_response = Mock()
    mock_positions_response.json.side_effect = ValueError("Invalid JSON")
    mock_positions_response.status_code = 200

    with patch('requests.post', return_value=mock_token_response), \
         patch('requests.get', return_value=mock_positions_response):
        result = ferry_api.refresh_ferry_positions(csv_path)
        assert result == []