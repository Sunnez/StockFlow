import asyncio
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from tests.factories import (
    create_inventory,
    create_product,
    create_warehouse,
)

pytestmark = pytest.mark.asyncio


async def create_order(
    client: AsyncClient,
    *,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    response = await client.post(
        "/orders",
        json={
            "items": items,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def get_inventory(
    client: AsyncClient,
    *,
    warehouse_id: str,
    product_id: str,
) -> dict[str, Any]:
    response = await client.get(f"/warehouses/{warehouse_id}/inventory")

    assert response.status_code == 200, response.text

    for inventory in response.json():
        if inventory["product_id"] == product_id:
            return inventory

    raise AssertionError(
        f"Inventory for product_id={product_id} "
        f"in warehouse_id={warehouse_id} not found"
    )


# ---------------------------------------------------------------------------
# Basic Order CRUD
# ---------------------------------------------------------------------------


async def test_create_order(
    client: AsyncClient,
):
    product = await create_product(client)

    response = await client.post(
        "/orders",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 3,
                }
            ]
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["status"] == "pending"
    assert len(body["items"]) == 1

    item = body["items"][0]

    assert item["product_id"] == product["id"]
    assert item["quantity"] == 3
    assert item["allocations"] == []


async def test_create_order_rejects_duplicate_product(
    client: AsyncClient,
):
    product = await create_product(client)

    response = await client.post(
        "/orders",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                },
                {
                    "product_id": product["id"],
                    "quantity": 3,
                },
            ]
        },
    )

    assert response.status_code == 422


async def test_create_order_rejects_missing_product(
    client: AsyncClient,
):
    missing_product_id = str(uuid4())

    response = await client.post(
        "/orders",
        json={
            "items": [
                {
                    "product_id": missing_product_id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 404


async def test_get_order_not_found(
    client: AsyncClient,
):
    response = await client.get(f"/orders/{uuid4()}")

    assert response.status_code == 404


async def test_list_orders(
    client: AsyncClient,
):
    product = await create_product(client)

    first_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 1,
            }
        ],
    )

    second_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 2,
            }
        ],
    )

    response = await client.get("/orders")

    assert response.status_code == 200

    body = response.json()

    order_ids = {order["id"] for order in body}

    assert first_order["id"] in order_ids
    assert second_order["id"] in order_ids


async def test_update_pending_order(
    client: AsyncClient,
):
    first_product = await create_product(
        client,
        name="RTX 5090",
        sku="RTX5090",
    )

    second_product = await create_product(
        client,
        name="RTX 5080",
        sku="RTX5080",
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": first_product["id"],
                "quantity": 2,
            }
        ],
    )

    response = await client.patch(
        f"/orders/{order['id']}",
        json={
            "items": [
                {
                    "product_id": second_product["id"],
                    "quantity": 5,
                }
            ]
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "pending"
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == second_product["id"]
    assert body["items"][0]["quantity"] == 5
    assert body["items"][0]["allocations"] == []


async def test_update_allocated_order_is_rejected(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 4,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    response = await client.patch(
        f"/orders/{order['id']}",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 409


async def test_delete_pending_order(
    client: AsyncClient,
):
    product = await create_product(client)

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 2,
            }
        ],
    )

    response = await client.delete(f"/orders/{order['id']}")

    assert response.status_code == 204

    get_response = await client.get(f"/orders/{order['id']}")

    assert get_response.status_code == 404


async def test_delete_allocated_order_is_rejected(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 4,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    response = await client.delete(f"/orders/{order['id']}")

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Allocation
# ---------------------------------------------------------------------------


async def test_allocate_order_from_single_warehouse(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    inventory = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    response = await client.post(f"/orders/{order['id']}/allocate")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "allocated"

    item = body["items"][0]

    assert len(item["allocations"]) == 1

    allocation = item["allocations"][0]

    assert allocation["inventory_id"] == inventory["id"]
    assert allocation["quantity"] == 6

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 10
    assert current_inventory["reserved_quantity"] == 6
    assert current_inventory["available_quantity"] == 4


async def test_allocate_order_can_split_between_warehouses(
    client: AsyncClient,
):
    product = await create_product(client)

    first_warehouse = await create_warehouse(
        client,
        name="Riga Warehouse",
        location="Riga, Latvia",
    )

    second_warehouse = await create_warehouse(
        client,
        name="Tallinn Warehouse",
        location="Tallinn, Estonia",
    )

    first_inventory = await create_inventory(
        client,
        warehouse_id=first_warehouse["id"],
        product_id=product["id"],
        quantity=7,
    )

    second_inventory = await create_inventory(
        client,
        warehouse_id=second_warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 12,
            }
        ],
    )

    response = await client.post(f"/orders/{order['id']}/allocate")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "allocated"

    allocations = body["items"][0]["allocations"]

    assert len(allocations) == 2
    assert sum(allocation["quantity"] for allocation in allocations) == 12

    allocation_inventory_ids = {
        allocation["inventory_id"] for allocation in allocations
    }

    assert allocation_inventory_ids == {
        first_inventory["id"],
        second_inventory["id"],
    }

    first_current = await get_inventory(
        client,
        warehouse_id=first_warehouse["id"],
        product_id=product["id"],
    )

    second_current = await get_inventory(
        client,
        warehouse_id=second_warehouse["id"],
        product_id=product["id"],
    )

    assert (
        first_current["reserved_quantity"] + second_current["reserved_quantity"] == 12
    )

    assert first_current["reserved_quantity"] <= first_current["quantity"]

    assert second_current["reserved_quantity"] <= second_current["quantity"]


async def test_allocate_order_respects_existing_reservations(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    first_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    first_response = await client.post(f"/orders/{first_order['id']}/allocate")

    assert first_response.status_code == 200

    second_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 4,
            }
        ],
    )

    second_response = await client.post(f"/orders/{second_order['id']}/allocate")

    assert second_response.status_code == 200

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 10
    assert current_inventory["reserved_quantity"] == 10
    assert current_inventory["available_quantity"] == 0


async def test_allocate_order_with_insufficient_stock_rolls_back(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=3,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 4,
            }
        ],
    )

    response = await client.post(f"/orders/{order['id']}/allocate")

    assert response.status_code == 409

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 3
    assert current_inventory["reserved_quantity"] == 0
    assert current_inventory["available_quantity"] == 3

    order_response = await client.get(f"/orders/{order['id']}")

    assert order_response.status_code == 200

    current_order = order_response.json()

    assert current_order["status"] == "pending"
    assert current_order["items"][0]["allocations"] == []


async def test_allocate_order_rolls_back_all_products_if_one_is_insufficient(
    client: AsyncClient,
):
    first_product = await create_product(
        client,
        name="RTX 5090",
        sku="RTX5090",
    )

    second_product = await create_product(
        client,
        name="RTX 5080",
        sku="RTX5080",
    )

    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=first_product["id"],
        quantity=10,
    )

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=second_product["id"],
        quantity=2,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": first_product["id"],
                "quantity": 6,
            },
            {
                "product_id": second_product["id"],
                "quantity": 3,
            },
        ],
    )

    response = await client.post(f"/orders/{order['id']}/allocate")

    assert response.status_code == 409

    first_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=first_product["id"],
    )

    second_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=second_product["id"],
    )

    assert first_inventory["reserved_quantity"] == 0
    assert second_inventory["reserved_quantity"] == 0

    order_response = await client.get(f"/orders/{order['id']}")

    assert order_response.status_code == 200

    current_order = order_response.json()

    assert current_order["status"] == "pending"

    assert all(item["allocations"] == [] for item in current_order["items"])


async def test_allocate_order_twice_is_rejected(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 4,
            }
        ],
    )

    first_response = await client.post(f"/orders/{order['id']}/allocate")

    assert first_response.status_code == 200

    second_response = await client.post(f"/orders/{order['id']}/allocate")

    assert second_response.status_code == 409

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["reserved_quantity"] == 4


# ---------------------------------------------------------------------------
# Fulfillment
# ---------------------------------------------------------------------------


async def test_fulfill_allocated_order(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    inventory = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    response = await client.post(f"/orders/{order['id']}/fulfill")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "fulfilled"

    allocations = body["items"][0]["allocations"]

    assert len(allocations) == 1
    assert allocations[0]["inventory_id"] == inventory["id"]
    assert allocations[0]["quantity"] == 6

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 4
    assert current_inventory["reserved_quantity"] == 0
    assert current_inventory["available_quantity"] == 4


async def test_fulfill_pending_order_is_rejected(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    response = await client.post(f"/orders/{order['id']}/fulfill")

    assert response.status_code == 409

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 10
    assert current_inventory["reserved_quantity"] == 0


async def test_fulfill_order_twice_is_rejected_without_double_debit(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    first_fulfill = await client.post(f"/orders/{order['id']}/fulfill")

    assert first_fulfill.status_code == 200

    second_fulfill = await client.post(f"/orders/{order['id']}/fulfill")

    assert second_fulfill.status_code == 409

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 4
    assert current_inventory["reserved_quantity"] == 0


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


async def test_cancel_pending_order(
    client: AsyncClient,
):
    product = await create_product(client)

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 3,
            }
        ],
    )

    response = await client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "cancelled"
    assert body["items"][0]["allocations"] == []

    second_response = await client.post(f"/orders/{order['id']}/cancel")

    assert second_response.status_code == 409


async def test_cancel_allocated_order_releases_reservation(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    inventory = await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    allocated_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert allocated_inventory["quantity"] == 10
    assert allocated_inventory["reserved_quantity"] == 6

    response = await client.post(f"/orders/{order['id']}/cancel")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "cancelled"

    allocations = body["items"][0]["allocations"]

    assert len(allocations) == 1
    assert allocations[0]["inventory_id"] == inventory["id"]
    assert allocations[0]["quantity"] == 6

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 10
    assert current_inventory["reserved_quantity"] == 0
    assert current_inventory["available_quantity"] == 10


async def test_cancel_fulfilled_order_is_rejected(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    fulfill_response = await client.post(f"/orders/{order['id']}/fulfill")

    assert fulfill_response.status_code == 200

    cancel_response = await client.post(f"/orders/{order['id']}/cancel")

    assert cancel_response.status_code == 409

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 4
    assert current_inventory["reserved_quantity"] == 0


# ---------------------------------------------------------------------------
# Historical allocations
# ---------------------------------------------------------------------------


async def test_inventory_used_by_historical_allocation_cannot_be_deleted(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=6,
    )

    order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 6,
            }
        ],
    )

    allocation_response = await client.post(f"/orders/{order['id']}/allocate")

    assert allocation_response.status_code == 200

    fulfill_response = await client.post(f"/orders/{order['id']}/fulfill")

    assert fulfill_response.status_code == 200

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 0
    assert current_inventory["reserved_quantity"] == 0

    delete_response = await client.delete(
        f"/warehouses/{warehouse['id']}/inventory/{product['id']}"
    )

    assert delete_response.status_code == 409

    inventory_after_delete_attempt = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert inventory_after_delete_attempt["id"] == current_inventory["id"]


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


async def test_concurrent_orders_cannot_over_reserve_inventory(
    client: AsyncClient,
):
    product = await create_product(client)
    warehouse = await create_warehouse(client)

    await create_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
        quantity=10,
    )

    first_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 10,
            }
        ],
    )

    second_order = await create_order(
        client,
        items=[
            {
                "product_id": product["id"],
                "quantity": 10,
            }
        ],
    )

    first_response, second_response = await asyncio.gather(
        client.post(f"/orders/{first_order['id']}/allocate"),
        client.post(f"/orders/{second_order['id']}/allocate"),
    )

    assert sorted(
        [
            first_response.status_code,
            second_response.status_code,
        ]
    ) == [200, 409]

    current_inventory = await get_inventory(
        client,
        warehouse_id=warehouse["id"],
        product_id=product["id"],
    )

    assert current_inventory["quantity"] == 10
    assert current_inventory["reserved_quantity"] == 10
    assert current_inventory["available_quantity"] == 0

    first_order_response = await client.get(f"/orders/{first_order['id']}")

    second_order_response = await client.get(f"/orders/{second_order['id']}")

    assert first_order_response.status_code == 200
    assert second_order_response.status_code == 200

    statuses = sorted(
        [
            first_order_response.json()["status"],
            second_order_response.json()["status"],
        ]
    )

    assert statuses == [
        "allocated",
        "pending",
    ]
