import pytest

# Configure pytest-asyncio to auto mode so we don't need @pytest.mark.asyncio
# on every test function (still works if you add it manually)
pytest_plugins = ["pytest_asyncio"]
