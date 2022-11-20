import hashlib


def assert_new_user(user):
    assert user.name == "Test User"
    assert user.email == "test@email.com"
    assert user.picture == "https://path.to.picture.com"


def test_new_google_user(new_google_user):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the name email, picture url, google id and analytics id
    """
    assert_new_user(new_google_user)
    assert new_google_user.google_id == "12345677890"
    assert new_google_user.facebook_id == None


def test_new_facebook_user(new_facebook_user):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the name email, picture url, facebook id and analytics id
    """
    assert_new_user(new_facebook_user)
    assert new_facebook_user.google_id == None
    assert new_facebook_user.facebook_id == "0987654321"
