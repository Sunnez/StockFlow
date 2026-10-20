from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from tests.factories import (
    create_inventory,
    create_product,
    create_warehouse,
)


@pytest.mark.asyncio
async def test_create_inventory(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    response = await client.post(
        f"/warehouses/{warehouse['id']}/inventory",
        json={
            "product_id": product["id"],
            "quantity": 25,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert UUID(data["id"])
    assert data["product_id"] == product["id"]
    assert data["warehouse_id"] == warehouse["id"]
    assert data["quantity"] == 25


@pytest.mark.asyncio
async def test_create_inventory_with_zero_quantity(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    response = await client.post(
        f"/warehouses/{warehouse['id']}/inventory",
        json={
            "product_id": product["id"],
            "quantity": 0,
        },
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == 0


@pytest.mark.asyncio
async def test_create_duplicate_inventory(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    response = await client.post(
        f"/warehouses/{warehouse['id']}/inventory",
        json={
            "product_id": product["id"],
            "quantity": 20,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Product with id={product['id']} already exists "
        f"in warehouse with id={warehouse['id']}"
    )


@pytest.mark.asyncio
async def test_create_inventory_with_nonexistent_warehouse(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse_id = uuid4()

    response = await client.post(
        f"/warehouses/{warehouse_id}/inventory",
        json={
            "product_id": product["id"],
            "quantity": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_create_inventory_with_nonexistent_product(
    client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(client)
    product_id = uuid4()

    response = await client.post(
        f"/warehouses/{warehouse['id']}/inventory",
        json={
            "product_id": str(product_id),
            "quantity": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Product with id={product_id} does not exist"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "product_id": str(uuid4()),
                "quantity": -1,
            },
            id="negative-quantity",
        ),
        pytest.param(
            {
                "product_id": str(uuid4()),
            },
            id="missing-quantity",
        ),
        pytest.param(
            {
                "quantity": 10,
            },
            id="missing-product-id",
        ),
        pytest.param(
            {
                "product_id": "not-a-uuid",
                "quantity": 10,
            },
            id="invalid-product-id",
        ),
        pytest.param(
            {
                "product_id": str(uuid4()),
                "quantity": 10,
                "unexpected": "value",
            },
            id="extra-field",
        ),
    ],
)
async def test_create_inventory_with_invalid_payload(
    client: AsyncClient,
    payload: dict[str, Any],
) -> None:
    warehouse_id = uuid4()

    response = await client.post(
        f"/warehouses/{warehouse_id}/inventory",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_warehouse_inventory(
    client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(client)

    another_warehouse = await create_warehouse(
        client,
        name="Tallinn Warehouse",
        location="Tallinn, Estonia",
    )

    product_1 = await create_product(
        client,
        name="NVIDIA RTX 5090",
        sku="RTX5090",
    )
    product_2 = await create_product(
        client,
        name="NVIDIA RTX 4090",
        sku="RTX4090",
    )
    product_3 = await create_product(
        client,
        name="NVIDIA RTX 3090",
        sku="RTX3090",
    )

    inventory_1 = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product_1["id"],
        quantity=10,
    )

    inventory_2 = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product_2["id"],
        quantity=20,
    )

    await create_inventory(
        client,
        warehouse_id=another_warehouse["id"],
        product_id=product_3["id"],
        quantity=30,
    )

    response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory"
    )

    assert response.status_code == 200

    data = response.json()

    expected_inventory = [
        inventory_1,
        inventory_2,
    ]

    assert sorted(
        data,
        key=lambda item: item["id"],
    ) == sorted(
        expected_inventory,
        key=lambda item: item["id"],
    )


@pytest.mark.asyncio
async def test_get_inventory_for_nonexistent_warehouse(
    client: AsyncClient,
) -> None:
    warehouse_id = uuid4()

    response = await client.get(
        f"/warehouses/{warehouse_id}/inventory"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_get_warehouse_inventory_pagination(
    client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(client)

    products = [
        await create_product(
            client,
            name="NVIDIA RTX 5090",
            sku="RTX5090",
        ),
        await create_product(
            client,
            name="NVIDIA RTX 4090",
            sku="RTX4090",
        ),
        await create_product(
            client,
            name="NVIDIA RTX 3090",
            sku="RTX3090",
        ),
    ]

    inventory = []

    for index, product in enumerate(
        products,
        start=1,
    ):
        item = await create_inventory(
            client,
            warehouse_id=warehouse["id"],
            product_id=product["id"],
            quantity=index * 10,
        )

        inventory.append(item)

    response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory",
        params={
            "limit": 2,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    expected_inventory = sorted(
        inventory,
        key=lambda item: item["id"],
    )[1:3]

    assert data == expected_inventory


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
async def test_get_inventory_invalid_pagination(
    client: AsyncClient,
    params: dict[str, int],
) -> None:
    warehouse_id = uuid4()

    response = await client.get(
        f"/warehouses/{warehouse_id}/inventory",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_inventory_quantity(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    created_inventory = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    response = await client.patch(
        (
            f"/warehouses/{warehouse['id']}"
            f"/inventory/{product['id']}"
        ),
        json={
            "quantity": 99,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == created_inventory["id"]
    assert data["product_id"] == product["id"]
    assert data["warehouse_id"] == warehouse["id"]
    assert data["quantity"] == 99

    get_response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory"
    )

    assert get_response.status_code == 200

    inventory = get_response.json()

    assert len(inventory) == 1
    assert inventory[0]["id"] == created_inventory["id"]
    assert inventory[0]["quantity"] == 99


@pytest.mark.asyncio
async def test_update_inventory_for_nonexistent_warehouse(
    client: AsyncClient,
) -> None:
    warehouse_id = uuid4()
    product_id = uuid4()

    response = await client.patch(
        f"/warehouses/{warehouse_id}/inventory/{product_id}",
        json={
            "quantity": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Warehouse with id={warehouse_id} does not exist"
    )


@pytest.mark.asyncio
async def test_update_nonexistent_inventory(
    client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(client)
    product_id = uuid4()

    response = await client.patch(
        f"/warehouses/{warehouse['id']}/inventory/{product_id}",
        json={
            "quantity": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Inventory for product id={product_id} "
        f"in warehouse id={warehouse['id']} does not exist"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "quantity": -1,
            },
            id="negative-quantity",
        ),
        pytest.param(
            {},
            id="missing-quantity",
        ),
        pytest.param(
            {
                "quantity": 10,
                "unexpected": "value",
            },
            id="extra-field",
        ),
    ],
)
async def test_update_inventory_with_invalid_payload(
    client: AsyncClient,
    payload: dict[str, Any],
) -> None:
    warehouse_id = uuid4()
    product_id = uuid4()

    response = await client.patch(
        f"/warehouses/{warehouse_id}/inventory/{product_id}",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_inventory_with_invalid_warehouse_uuid(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/warehouses/not-a-uuid/inventory",
        json={
            "product_id": str(uuid4()),
            "quantity": 10,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_inventory_with_invalid_warehouse_uuid(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/warehouses/not-a-uuid/inventory/{uuid4()}",
        json={
            "quantity": 10,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_inventory_with_invalid_product_uuid(
    client: AsyncClient,
) -> None:
    response = await client.patch(
        f"/warehouses/{uuid4()}/inventory/not-a-uuid",
        json={
            "quantity": 10,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_empty_inventory(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=0,
    )

    response = await client.delete(
        f"/warehouses/{warehouse['id']}/inventory/{product['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""

    list_response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory"
    )

    assert list_response.status_code == 200
    assert list_response.json() == []


@pytest.mark.asyncio
async def test_delete_non_empty_inventory(
    client: AsyncClient,
) -> None:
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    inventory = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    response = await client.delete(
        f"/warehouses/{warehouse['id']}/inventory/{product['id']}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Inventory for product id={product['id']} "
        f"in warehouse id={warehouse['id']} "
        f"cannot be deleted since it is not empty"
    )

    list_response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory"
    )

    assert list_response.status_code == 200

    data = list_response.json()

    assert len(data) == 1
    assert data[0]["id"] == inventory["id"]
    assert data[0]["quantity"] == 10


@pytest.mark.asyncio
async def test_delete_nonexistent_inventory(
    client: AsyncClient,
) -> None:
    warehouse = await create_warehouse(client)
    product_id = uuid4()

    response = await client.delete(
        f"/warehouses/{warehouse['id']}/inventory/{product_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Inventory for product id={product_id} "
        f"in warehouse id={warehouse['id']} does not exist"
    )


@pytest.mark.asyncio
async def test_delete_inventory_with_invalid_uuid(
    client: AsyncClient,
) -> None:
    response = await client.delete(
        f"/warehouses/not-a-uuid/inventory/{uuid4()}"
    )

    assert response.status_code == 422