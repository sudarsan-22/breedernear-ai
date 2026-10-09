import pytest
from pydantic import ValidationError

from breedernear_core.config import Settings


def test_default_model_is_current_flash():
    assert Settings(_env_file=None).breedernear_model.startswith("gemini-3")


@pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"])
def test_retiring_models_are_rejected(model):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, breedernear_model=model)
