import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.alerts.models import CustomButton


@pytest.mark.django_db
def test_get_custom_actions(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    custom_action = make_custom_action(organization=organization)

    url = reverse("api-public:actions-list")

    response = client.get(url, format="json", HTTP_AUTHORIZATION=f"{token}")

    expected_payload = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": custom_action.public_primary_key,
                "name": custom_action.name,
                "team_id": None,
                "url": custom_action.webhook,
                "data": custom_action.data,
                "user": custom_action.user,
                "password": custom_action.password,
                "authorization_header": custom_action.authorization_header,
                "forward_whole_payload": custom_action.forward_whole_payload,
            }
        ],
    }

    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected_payload


@pytest.mark.django_db
def test_get_custom_actions_filter_by_name(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    custom_action = make_custom_action(organization=organization)
    make_custom_action(organization=organization)
    url = reverse("api-public:actions-list")

    response = client.get(f"{url}?name={custom_action.name}", format="json", HTTP_AUTHORIZATION=f"{token}")

    expected_payload = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": custom_action.public_primary_key,
                "name": custom_action.name,
                "team_id": None,
                "url": custom_action.webhook,
                "data": custom_action.data,
                "user": custom_action.user,
                "password": custom_action.password,
                "authorization_header": custom_action.authorization_header,
                "forward_whole_payload": custom_action.forward_whole_payload,
            }
        ],
    }

    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected_payload


@pytest.mark.django_db
def test_get_custom_actions_filter_by_name_empty_result(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    make_custom_action(organization=organization)

    url = reverse("api-public:actions-list")

    response = client.get(f"{url}?name=NonExistentName", format="json", HTTP_AUTHORIZATION=f"{token}")

    expected_payload = {"count": 0, "next": None, "previous": None, "results": []}

    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected_payload


@pytest.mark.django_db
def test_get_custom_action(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    custom_action = make_custom_action(organization=organization)

    url = reverse("api-public:actions-detail", kwargs={"pk": custom_action.public_primary_key})

    response = client.get(url, format="json", HTTP_AUTHORIZATION=f"{token}")

    expected_payload = {
        "id": custom_action.public_primary_key,
        "name": custom_action.name,
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected_payload


@pytest.mark.django_db
def test_create_custom_action(make_organization_and_user_with_token):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    url = reverse("api-public:actions-list")

    data = {
        "name": "Test outgoing webhook",
        "url": "https://example.com",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    custom_action = CustomButton.objects.get(public_primary_key=response.data["id"])

    expected_result = {
        "id": custom_action.public_primary_key,
        "name": custom_action.name,
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data == expected_result


@pytest.mark.django_db
def test_create_custom_action_nested_data(make_organization_and_user_with_token):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    url = reverse("api-public:actions-list")

    data = {
        "name": "Test outgoing webhook with nested data",
        "url": "https://example.com",
        # Assert that nested field access still works as long as the variable
        # is quoted, making it valid JSON.
        # This ensures backwards compatibility from when templates were required
        # to be JSON.
        "data": '{"nested_item": "{{ alert_payload.foo.bar }}"}',
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    custom_action = CustomButton.objects.get(public_primary_key=response.data["id"])

    expected_result = {
        "id": custom_action.public_primary_key,
        "name": custom_action.name,
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == expected_result


@pytest.mark.django_db
def test_create_custom_action_valid_after_render(make_organization_and_user_with_token):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    url = reverse("api-public:actions-list")

    data = {
        "name": "Test outgoing webhook with nested data",
        "url": "https://example.com",
        # Assert that nested field access still works as long as the variable
        # is quoted, making it valid JSON.
        # This ensures backwards compatibility from when templates were required
        # to be JSON.
        "data": '{"name": "{{ alert_payload.name }}", "labels": {{ alert_payload.labels | tojson }}}',
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    custom_action = CustomButton.objects.get(public_primary_key=response.data["id"])

    expected_result = {
        "id": custom_action.public_primary_key,
        "name": custom_action.name,
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == expected_result


@pytest.mark.django_db
def test_create_custom_action_valid_after_render_use_all_data(make_organization_and_user_with_token):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    url = reverse("api-public:actions-list")

    data = {
        "name": "Test outgoing webhook with nested data",
        "url": "https://example.com",
        # Assert that nested field access still works as long as the variable
        # is quoted, making it valid JSON.
        # This ensures backwards compatibility from when templates were required
        # to be JSON.
        "data": "{{ alert_payload | tojson }}",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    custom_action = CustomButton.objects.get(public_primary_key=response.data["id"])

    expected_result = {
        "id": custom_action.public_primary_key,
        "name": custom_action.name,
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == expected_result


@pytest.mark.django_db
def test_create_custom_action_invalid_data(
    make_organization_and_user_with_token,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    url = reverse("api-public:actions-list")

    data = {
        "name": "Test outgoing webhook",
        "url": "invalid_url",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["url"][0] == "URL is incorrect"

    data = {
        "name": "Test outgoing webhook",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["url"][0] == "This field is required."

    data = {
        "url": "https://example.com",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["name"][0] == "This field is required."

    data = {
        "name": "Test outgoing webhook",
        "url": "https://example.com",
        "data": "invalid_json",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["data"][0] == "Data has incorrect format"

    data = {
        "name": "Test outgoing webhook",
        "url": "https://example.com",
        # This would need a `| tojson` or some double quotes around it to pass validation.
        "data": "{{ alert_payload.name }}",
    }

    response = client.post(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["data"][0] == "Data has incorrect format"


@pytest.mark.django_db
def test_update_custom_action(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    custom_action = make_custom_action(organization=organization)

    url = reverse("api-public:actions-detail", kwargs={"pk": custom_action.public_primary_key})

    data = {
        "name": "RENAMED",
    }

    assert custom_action.name != data["name"]

    response = client.put(url, data=data, format="json", HTTP_AUTHORIZATION=f"{token}")

    expected_result = {
        "id": custom_action.public_primary_key,
        "name": data["name"],
        "team_id": None,
        "url": custom_action.webhook,
        "data": custom_action.data,
        "user": custom_action.user,
        "password": custom_action.password,
        "authorization_header": custom_action.authorization_header,
        "forward_whole_payload": custom_action.forward_whole_payload,
    }

    assert response.status_code == status.HTTP_200_OK
    custom_action.refresh_from_db()
    assert custom_action.name == expected_result["name"]
    assert response.data == expected_result


@pytest.mark.django_db
def test_delete_custom_action(
    make_organization_and_user_with_token,
    make_custom_action,
):
    organization, user, token = make_organization_and_user_with_token()
    client = APIClient()

    custom_action = make_custom_action(organization=organization)
    url = reverse("api-public:actions-detail", kwargs={"pk": custom_action.public_primary_key})

    assert custom_action.deleted_at is None

    response = client.delete(url, format="json", HTTP_AUTHORIZATION=f"{token}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    custom_action.refresh_from_db()
    assert custom_action.deleted_at is not None

    response = client.get(url, format="json", HTTP_AUTHORIZATION=f"{token}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["detail"] == "Not found."
