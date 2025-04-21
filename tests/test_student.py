import pytest

student = {
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "2025-04-21",
  "client_id": 1,
}

def test_create_student(client, auth_headers, create_test_client): 
    response = client.post("/students/", json=student, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "string"
    
