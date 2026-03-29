from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from core.models import UserPreferences


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        username="morgan",
        password="calm-focus-123",
    )


def test_for_user_returns_existing_preferences_after_integrity_error(user) -> None:
    existing_preferences = UserPreferences.objects.create(user=user)

    with patch.object(
        UserPreferences.objects,
        "get_or_create",
        side_effect=IntegrityError("duplicate key value violates unique constraint"),
    ):
        preferences = UserPreferences.for_user(user)

    assert preferences == existing_preferences
