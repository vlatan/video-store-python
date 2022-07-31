import hashlib


def test_new_google_user_with_fixture(new_google_user):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the name email, picture url, google id and analytics id
    """
    assert new_google_user.name == "Test User"
    assert new_google_user.email == "test@email.com"
    assert new_google_user.picture == "https://path.to.picture.com"
    assert new_google_user.google_id == "12345677890"
    assert new_google_user.facebook_id == None

    value = str(new_google_user.id) + new_google_user.google_id
    analytics_id = hashlib.md5(value.encode()).hexdigest()
    assert new_google_user.analytics_id == analytics_id


def test_new_facebook_user_with_fixture(new_facebook_user):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the name email, picture url, facebook id and analytics id
    """
    assert new_facebook_user.name == "Test User"
    assert new_facebook_user.email == "test@email.com"
    assert new_facebook_user.picture == "https://path.to.picture.com"
    assert new_facebook_user.google_id == None
    assert new_facebook_user.facebook_id == "0987654321"

    value = str(new_facebook_user.id) + new_facebook_user.facebook_id
    analytics_id = hashlib.md5(value.encode()).hexdigest()
    assert new_facebook_user.analytics_id == analytics_id
