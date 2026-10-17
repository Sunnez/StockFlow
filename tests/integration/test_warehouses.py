from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_warehouse(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert UUID(data["id"])
    assert data["name"] == "Riga Warehouse"
    assert data["location"] == "Riga, Latvia"


@pytest.mark.asyncio
async def test_create_warehouse_with_duplicate_name(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201

    duplicate_response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Warehouse with name='Riga Warehouse' already exists"
    )


@pytest.mark.asyncio
async def test_get_warehouse_by_id(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201

    warehouse_id = create_response.json()["id"]

    get_response = await client.get(
        f"/warehouses/{warehouse_id}"
    )

    assert get_response.status_code == 200

    data = get_response.json()

    assert data["id"] == warehouse_id
    assert data["name"] == "Riga Warehouse"
    assert data["location"] == "Riga, Latvia"


@pytest.mark.asyncio
async def test_get_warehouse_by_nonexistent_id(
    client: AsyncClient,
) -> None:
    warehouse_id = uuid4()

    response = await client.get(
        f"/warehouses/{warehouse_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_get_warehouse_with_invalid_uuid(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/warehouses/not-a-uuid"
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_warehouses_list(
    client: AsyncClient,
) -> None:
    warehouses = []

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Tallinn Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Vilnius Warehouse",
            "location": "Vilnius, Lithuania",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    response = await client.get(
        "/warehouses"
    )

    assert response.status_code == 200

    data = response.json()

    assert sorted(
        warehouses,
        key=lambda warehouse: warehouse["id"],
    ) == sorted(
        data,
        key=lambda warehouse: warehouse["id"],
    )


@pytest.mark.asyncio
async def test_get_warehouses_pagination(
    client: AsyncClient,
) -> None:
    warehouses = []

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Tallinn Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await client.post(
        "/warehouses",
        json={
            "name": "Vilnius Warehouse",
            "location": "Vilnius, Lithuania",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    response = await client.get(
        "/warehouses",
        params={
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    expected_warehouses = sorted(
        warehouses,
        key=lambda warehouse: warehouse["id"],
    )[1:3]

    assert data == expected_warehouses


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        pytest.param(
            {"limit": 0},
            id="limit-below-minimum",
        ),
        pytest.param(
            {"limit": 101},
            id="limit-above-maximum",
        ),
        pytest.param(
            {"offset": -1},
            id="negative-offset",
        ),
    ],
)
async def test_get_warehouses_invalid_pagination(
    client: AsyncClient,
    params: dict[str, int],
) -> None:
    response = await client.get(
        "/warehouses",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "name": "",
                "location": "Riga, Latvia",
            },
            id="empty-name",
        ),
        pytest.param(
            {
                "name": "Riga Warehouse",
                "location": "",
            },
            id="empty-location",
        ),
        pytest.param(
            {
                "name": "Riga Warehouse",
            },
            id="missing-location",
        ),
        pytest.param(
            {
                "name": "Riga Warehouse",
                "location": "Riga, Latvia",
                "unexpected": "value",
            },
            id="extra-field",
        ),
        pytest.param(
            {
                "name": "X" * 256,
                "location": "Riga, Latvia",
            },
            id="name-too-long",
        ),
        pytest.param(
            {
                "name": "Riga Warehouse",
                "location": "X" * 256,
            },
            id="location-too-long",
        ),
    ],
)
async def test_create_warehouse_with_invalid_payload(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    response = await client.post(
        "/warehouses",
        json=payload,
    )

    assert response.status_code == 422