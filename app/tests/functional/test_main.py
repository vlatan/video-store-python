def test_home_page(app, client):
    response = client.get("/")
    assert response.status_code == 200
    assert app.config["APP_NAME"].encode() in response.data
