import pytest
import sys
from unittest.mock import patch, Mock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_ferry_api_import_exists():
    """Test that ferry_api module can be imported and has refresh_ferry_positions"""
    from ferry_api import refresh_ferry_positions
    assert callable(refresh_ferry_positions)


def test_app_has_ferries_integration():
    """Test that app.py has ferry integration by checking source code"""
    # We can't import app due to Python 3.9 type hint issues, so check source
    app_path = Path(__file__).parent.parent / "app.py"
    source = app_path.read_text()

    # Check for ferry integration components
    assert "from ferry_api import refresh_ferry_positions" in source, "Missing ferry_api import"
    assert "_ferries = []" in source, "Missing _ferries global variable"
    assert "_ferries" in source and "global _graph, _kdtree, _node_list, _quays_dict, _startup_error, _shipyards, _ferries" in source, "Missing _ferries in global declaration"
    assert "refresh_ferry_positions(ferries_csv_path)" in source, "Missing ferry refresh call"


def test_refresh_ferry_positions_returns_list():
    """Test that ferry_api.refresh_ferry_positions returns a list"""
    from ferry_api import refresh_ferry_positions

    # This will fail with actual API calls, but shows the function exists
    # In production, this would be mocked
    with patch('ferry_api.get_barentswatch_token', side_effect=RuntimeError("No token")):
        result = refresh_ferry_positions(Path("data/ferries.csv"))
        assert isinstance(result, list)


def test_ferry_refresh_with_mock():
    """Test ferry refresh function with mocked API calls"""
    from ferry_api import refresh_ferry_positions

    mock_positions = [
        {'name': 'BARØY', 'mmsi': '257741000', 'lat': 69.123, 'lon': 16.456}
    ]

    with patch('ferry_api.get_barentswatch_token', return_value='mock_token'):
        with patch('ferry_api.fetch_ferry_positions', return_value=mock_positions):
            result = refresh_ferry_positions(Path("data/ferries.csv"))
            # Even with mocks, the function should return a list
            assert isinstance(result, list)
