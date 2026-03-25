import pytest
import sys
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ferry_refresh_called_during_startup():
    """Test that ferry refresh is called during app startup"""
    mock_positions = [
        {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456}
    ]

    with patch('ferry_api.refresh_ferry_positions', return_value=mock_positions) as mock_refresh:
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
            # Import app module to test startup behavior
            import app

            # Clear any existing ferry data
            app._ferries = []

            # Run startup
            app.startup()

            # Verify refresh was called
            mock_refresh.assert_called_once()
            assert len(app._ferries) == 1
            assert app._ferries[0]['name'] == 'BARØY'
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_ferry_loading_failure_graceful():
    """Test graceful handling of ferry loading failure"""
    with patch('ferry_api.refresh_ferry_positions', return_value=[]):
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
            import app

            app._ferries = []
            app.startup()

            # Should continue with empty ferry list, no startup error
            assert app._ferries == []
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_app_startup_ferry_data_flow():
    """Test complete ferry data flow during app startup"""
    with patch('ferry_api.get_barentswatch_token') as mock_token, \
         patch('ferry_api.fetch_ferry_positions') as mock_fetch:

        mock_token.return_value = "mock-token"
        mock_fetch.return_value = [
            {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456, 'lastUpdate': '2024-01-01T12:00:00Z'},
            {'name': 'BASTØ ELECTRIC', 'mmsi': '257122880', 'lat': 59.456, 'lon': 10.789, 'lastUpdate': '2024-01-01T12:01:00Z'}
        ]

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

        try:
            import app
            app._ferries = []
            app.startup()

            # Verify startup called ferry refresh
            mock_token.assert_called_once()
            mock_fetch.assert_called_once()

            # Verify ferry data loaded correctly
            assert len(app._ferries) == 2
            assert app._ferries[0]['name'] == 'BARØY'
            assert app._ferries[1]['name'] == 'BASTØ ELECTRIC'
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_app_startup_handles_ferry_api_failure():
    """Test app startup gracefully handles ferry API failures"""
    with patch('ferry_api.refresh_ferry_positions', side_effect=Exception("API Error")):
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

        try:
            import app
            app._ferries = []
            app.startup()  # Should not raise exception
            assert app._ferries == []  # Empty list on failure
        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']


def test_status_endpoint_includes_ferry_count():
    """Test status endpoint returns ferry count after startup"""
    mock_ferries = [
        {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456},
        {'name': 'BASTØ ELECTRIC', 'mmsi': '257122880', 'lat': 59.456, 'lon': 10.789}
    ]

    with patch('ferry_api.refresh_ferry_positions', return_value=mock_ferries):
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

        try:
            import app
            app.startup()

            # Test status endpoint
            client = app.app.test_client()
            response = client.get('/api/status')

            assert response.status_code == 200
            status_data = response.get_json()
            assert 'ferry_count' in status_data
            assert status_data['ferry_count'] == 2

        finally:
            # Clean up
            if 'app' in sys.modules:
                del sys.modules['app']
