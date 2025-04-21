import pytest

subscription_only_training_type_correct = {
    "name": "Subscription only",
    "price": None,
    "is_subscription_only": True,
    "color": "#000000"
}

subscription_only_training_type_incorrect = {
    "name": "Subscription only",
    "price": 30,
    "is_subscription_only": True,
    "color": "#000000"
}

price_only_training_type_correct = {
    "name": "Price Only",
    "price": 30,
    "is_subscription_only": False,
    "color": "#000000"
}

price_only_training_type_incorrect = {
    "name": "Price only",
    "price": None,
    "is_subscription_only": False,
    "color": "#000000"
}

def test_create_training_type(client, auth_headers):
    response = client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == subscription_only_training_type_correct["name"]

    response = client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == price_only_training_type_correct["name"]

    response = client.post("/training_types/", json=subscription_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422


    response = client.post("/training_types/", json=price_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422



def test_get_training_types(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.get("/training_types/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["training_types"]) == 2

def test_get_training_type_by_id(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.get("/training_types/1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_update_training_type(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.patch("/training_types/1", json={"name": "New name"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New name"


