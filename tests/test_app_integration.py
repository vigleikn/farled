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
