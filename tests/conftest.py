import pytest
import respx
import httpx

BASE = "http://localhost:8000"


@pytest.fixture
def mock_api():
    """respx mock that intercepts all httpx calls to BASE."""
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        yield mock
