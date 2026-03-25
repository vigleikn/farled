import os
import pytest
from unittest.mock import patch

def test_environment_variables_required():
    """Test that missing client credentials raise appropriate errors"""
    with patch.dict(os.environ, {}, clear=True):
        from ferry_api import get_barentswatch_token
        with pytest.raises(ValueError, match="BARENTSWATCH_CLIENT_ID"):
            get_barentswatch_token()
