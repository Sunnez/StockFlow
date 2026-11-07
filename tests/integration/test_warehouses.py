from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.factories import (
    create_inventory,
    create_product,
    create_warehouse,
)


@pytest.mark.asyncio
async def test_create_warehouse(
    tenant_client: AsyncClient,
) -> None:
    response = await tenant_client.post(
        "warehouses",
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
    tenant_client: AsyncClient,
) -> None:
    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201

    duplicate_response = await tenant_client.post(
        "warehouses",
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
    tenant_client: AsyncClient,
) -> None:
    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201

    warehouse_id = create_response.json()["id"]

    get_response = await tenant_client.get(f"warehouses/{warehouse_id}")

    assert get_response.status_code == 200

    data = get_response.json()

    assert data["id"] == warehouse_id
    assert data["name"] == "Riga Warehouse"
    assert data["location"] == "Riga, Latvia"


@pytest.mark.asyncio
async def test_get_warehouse_by_nonexistent_id(
    tenant_client: AsyncClient,
) -> None:
    warehouse_id = uuid4()

    response = await tenant_client.get(f"warehouses/{warehouse_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_get_warehouse_with_invalid_uuid(
    tenant_client: AsyncClient,
) -> None:
    response = await tenant_client.get("warehouses/not-a-uuid")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_warehouses_list(
    tenant_client: AsyncClient,
) -> None:
    warehouses = []

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Tallinn Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Vilnius Warehouse",
            "location": "Vilnius, Lithuania",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    response = await tenant_client.get("warehouses")

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
    tenant_client: AsyncClient,
) -> None:
    warehouses = []

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Riga Warehouse",
            "location": "Riga, Latvia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Tallinn Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    create_response = await tenant_client.post(
        "warehouses",
        json={
            "name": "Vilnius Warehouse",
            "location": "Vilnius, Lithuania",
        },
    )

    assert create_response.status_code == 201
    warehouses.append(create_response.json())

    response = await tenant_client.get(
        "warehouses",
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
    tenant_client: AsyncClient,
    params: dict[str, int],
) -> None:
    response = await tenant_client.get(
        "warehouses",
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
    tenant_client: AsyncClient,
    payload: dict[str, str],
) -> None:
    response = await tenant_client.post(
        "warehouses",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_warehouse_name(
    tenant_client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(tenant_client)

    response = await tenant_client.patch(
        f"warehouses/{warehouse['id']}",
        json={
            "name": "New Riga Warehouse",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == warehouse["id"]
    assert data["name"] == "New Riga Warehouse"
    assert data["location"] == warehouse["location"]


@pytest.mark.asyncio
async def test_update_warehouse_location(
    tenant_client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(tenant_client)

    response = await tenant_client.patch(
        f"warehouses/{warehouse['id']}",
        json={
            "location": "Jurmala, Latvia",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == warehouse["name"]
    assert data["location"] == "Jurmala, Latvia"


@pytest.mark.asyncio
async def test_update_warehouse_name_and_location(
    tenant_client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(tenant_client)

    response = await tenant_client.patch(
        f"warehouses/{warehouse['id']}",
        json={
            "name": "Tallinn Warehouse",
            "location": "Tallinn, Estonia",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Tallinn Warehouse"
    assert data["location"] == "Tallinn, Estonia"


@pytest.mark.asyncio
async def test_update_nonexistent_warehouse(
    tenant_client: AsyncClient,
) -> None:
    warehouse_id = uuid4()

    response = await tenant_client.patch(
        f"warehouses/{warehouse_id}",
        json={
            "name": "Updated Warehouse",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_update_warehouse_with_duplicate_name(
    tenant_client: AsyncClient,
) -> None:
    first_warehouse = await create_warehouse(
        tenant_client,
        name="Riga Warehouse",
        location="Riga, Latvia",
    )

    second_warehouse = await create_warehouse(
        tenant_client,
        name="Tallinn Warehouse",
        location="Tallinn, Estonia",
    )

    response = await tenant_client.patch(
        f"warehouses/{second_warehouse['id']}",
        json={
            "name": first_warehouse["name"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Warehouse with name='Riga Warehouse' already exists"
    )

    get_response = await tenant_client.get(f"warehouses/{second_warehouse['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Tallinn Warehouse"


@pytest.mark.asyncio
async def test_update_warehouse_with_empty_payload(
    tenant_client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(tenant_client)

    response = await tenant_client.patch(
        f"warehouses/{warehouse['id']}",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_warehouse(
    tenant_client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(tenant_client)

    response = await tenant_client.delete(f"warehouses/{warehouse['id']}")

    assert response.status_code == 204
    assert response.content == b""

    get_response = await tenant_client.get(f"warehouses/{warehouse['id']}")

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_warehouse(
    tenant_client: AsyncClient,
) -> None:
    warehouse_id = uuid4()

    response = await tenant_client.delete(f"warehouses/{warehouse_id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_warehouse_with_inventory(
    tenant_client: AsyncClient,
) -> None:
    product = await create_product(tenant_client)
    warehouse = await create_warehouse(tenant_client)

    await create_inventory(
        tenant_client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=0,
    )

    response = await tenant_client.delete(f"warehouses/{warehouse['id']}")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse['id']} cannot be deleted "
        f"because it has inventory entries"
    )

    get_response = await tenant_client.get(f"warehouses/{warehouse['id']}")

    assert get_response.status_code == 200
