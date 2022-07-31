import pytest
from app.models import User

test_user_info = {
    "name": "Test User",
    "email": "test@email.com",
    "picture": "https://path.to.picture.com",
}


@pytest.fixture(scope="module")
def new_google_user():
    google_info = test_user_info.copy()
    google_info["google_id"] = "12345677890"
    return User(**google_info)


@pytest.fixture(scope="module")
def new_facebook_user():
    facebook_info = test_user_info.copy()
    facebook_info["facebook_id"] = "0987654321"
    return User(**facebook_info)
