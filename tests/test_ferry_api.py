def test_ferry_api_endpoint():
    from app import app

    with app.test_client() as client:
        response = client.get('/api/ferries')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)