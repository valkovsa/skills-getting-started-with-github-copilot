from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


BASELINE_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def restore_activities():
    app_module.activities.clear()
    app_module.activities.update(deepcopy(BASELINE_ACTIVITIES))
    yield
    app_module.activities.clear()
    app_module.activities.update(deepcopy(BASELINE_ACTIVITIES))


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_root_redirects_to_static_index(client):
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_activities_without_caching(client):
    # Arrange
    expected_activities = deepcopy(app_module.activities)

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected_activities
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in app_module.activities[activity_name]["participants"]


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_signup_rejects_full_activity(client):
    # Arrange
    activity_name = "Chess Club"
    activity = app_module.activities[activity_name]
    activity["participants"] = [
        f"student{index}@mergington.edu"
        for index in range(activity["max_participants"])
    ]

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "newstudent@mergington.edu"},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Activity is full"}


def test_signup_requires_email(client):
    # Arrange
    endpoint = "/activities/Chess Club/signup"

    # Act
    response = client.post(endpoint)

    # Assert
    assert response.status_code == 422


def test_remove_participant_unregisters_student(client):
    # Arrange
    activity_name = "Chess Club"
    email = app_module.activities[activity_name]["participants"][0]

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    assert email not in app_module.activities[activity_name]["participants"]


def test_remove_participant_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_remove_participant_rejects_unregistered_student(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }


def test_remove_participant_requires_email(client):
    # Arrange
    endpoint = "/activities/Chess Club/participants"

    # Act
    response = client.delete(endpoint)

    # Assert
    assert response.status_code == 422


def test_signup_mutates_participant_list(client):
    # Arrange
    activity_name = "Chess Club"
    email = "isolated@mergington.edu"
    original_participants = deepcopy(
        app_module.activities[activity_name]["participants"]
    )

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )

    # Assert
    assert signup_response.status_code == 200
    assert email in app_module.activities[activity_name]["participants"]
    assert app_module.activities[activity_name]["participants"] != original_participants
