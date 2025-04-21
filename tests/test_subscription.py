import pytest

subscription = {
    "name": "Subscription only",
    "price": 100,
    "number_of_sessions": 4,
    "validity_days": 30,
}



def test_create_training_type(client, auth_headers):
    response = client.post("/subscriptions/", json=subscription, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == subscription["name"]


def test_get_subscriptions(client, auth_headers):
    client.post("/subscriptions/", json=subscription, headers=auth_headers)
    response = client.get("/subscriptions/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["subscriptions"]) == 1


def test_get_training_type_by_id(client, auth_headers):
    client.post("/subscriptions/", json=subscription, headers=auth_headers)
    response = client.get("/subscriptions/1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_update_training_type(client, auth_headers):
    client.post("/subscriptions/", json=subscription, headers=auth_headers)
    response = client.patch("/subscriptions/1", json={"name": "New name"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New name"


