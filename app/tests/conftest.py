import pytest
from app.models import User
from app import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def user_info():
    return {
        "name": "Test User",
        "email": "test@email.com",
        "picture": "https://path.to.picture.com",
    }


@pytest.fixture()
def new_google_user():
    google_info = user_info().copy()
    google_info["google_id"] = "12345677890"
    return User(**google_info)


@pytest.fixture()
def new_facebook_user():
    facebook_info = user_info().copy()
    facebook_info["facebook_id"] = "0987654321"
    return User(**facebook_info)
