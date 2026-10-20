from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from tests.factories import (
    create_inventory,
    create_product,
    create_warehouse,
)


@pytest.mark.asyncio
async def test_create_product(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 5090",
            "sku": "RTX5090",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert UUID(data["id"])
    assert data["name"] == "NVIDIA RTX 5090"
    assert data["sku"] == "RTX5090"


@pytest.mark.asyncio
async def test_create_product_with_duplicate_sku(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 5090",
            "sku": "RTX5090",
        },
    )

    assert create_response.status_code == 201

    duplicate_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 6090",
            "sku": "RTX5090",
        },
    )

    assert duplicate_response.status_code == 409

    assert duplicate_response.json()["detail"] == ("Product with sku='RTX5090' already exists")


@pytest.mark.asyncio
async def test_get_product_by_id(
    client: AsyncClient,
) -> None:
    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 5090",
            "sku": "RTX5090",
        }
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    get_response = await client.get(
        f"/products/{product_id}"
    )

    assert get_response.status_code == 200

    data = get_response.json()

    assert data["id"] == product_id
    assert data["name"] == "NVIDIA RTX 5090"
    assert data["sku"] == "RTX5090"


@pytest.mark.asyncio
async def test_get_product_by_nonexistent_id(
    client: AsyncClient,
) -> None:
    product_id = uuid4()

    get_response = await client.get(
        f"/products/{product_id}"
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == (f"Product with id={product_id} does not exist")


@pytest.mark.asyncio
async def test_get_products_list(
    client: AsyncClient,
) -> None:
    products_list = []
    
    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 5090",
            "sku": "RTX5090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 4090",
            "sku": "RTX4090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 1090",
            "sku": "RTX1090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    get_response = await client.get(
        "/products",
    )

    assert get_response.status_code == 200

    data = get_response.json()

    assert sorted(products_list, key=lambda product: product["id"]) == sorted(data, key=lambda product: product["id"])


@pytest.mark.asyncio
async def test_get_products_pagination(
    client: AsyncClient,
) -> None:
    products_list = []
    
    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 5090",
            "sku": "RTX5090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 4090",
            "sku": "RTX4090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    create_response = await client.post(
        "/products",
        json={
            "name": "NVIDIA RTX 1090",
            "sku": "RTX1090",
        }
    )

    assert create_response.status_code == 201
    data = create_response.json()
    products_list.append(
        {
            "id": data["id"],
            "name": data["name"],
            "sku": data["sku"]
        }
    )

    get_response = await client.get(
        "/products",
        params={
            "limit": 2,
            "offset": 1,
        }
    )

    assert get_response.status_code == 200

    data = get_response.json()

    expected_products = sorted(products_list, key=lambda product: product["id"])[1:3]

    assert expected_products == data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
    ],
)
async def test_get_products_invalid_pagination(
    client: AsyncClient,
    params: dict[str, int],
) -> None:
    response = await client.get(
        "/products",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_product_with_invalid_uuid(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/products/not-a-uuid"
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "name": "",
                "sku": "RTX5090",
            },
            id="empty-name",
        ),
        pytest.param(
            {
                "name": "NVIDIA RTX 5090",
                "sku": "",
            },
            id="empty-sku",
        ),
        pytest.param(
            {
                "name": "NVIDIA RTX 5090",
            },
            id="missing-sku",
        ),
        pytest.param(
            {
                "name": "NVIDIA RTX 5090",
                "sku": "RTX5090",
                "unexpected": "value",
            },
            id="extra-field",
        ),
        pytest.param(
            {
                "name": "X" * 256,
                "sku": "RTX5090",
            },
            id="name-too-long",
        ),
        pytest.param(
            {
                "name": "NVIDIA RTX 5090",
                "sku": "X" * 101,
            },
            id="sku-too-long",
        ),
    ],
)
async def test_create_product_with_invalid_payload(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    response = await client.post(
        "/products",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_product_name(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    response = await client.patch(
        f"/products/{product['id']}",
        json={
            "name": "NVIDIA RTX 5090 Founders Edition",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product["id"]
    assert data["name"] == "NVIDIA RTX 5090 Founders Edition"
    assert data["sku"] == product["sku"]


@pytest.mark.asyncio
async def test_update_product_sku(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    response = await client.patch(
        f"/products/{product['id']}",
        json={
            "sku": "RTX5090-FE",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product["id"]
    assert data["name"] == product["name"]
    assert data["sku"] == "RTX5090-FE"


@pytest.mark.asyncio
async def test_update_product_name_and_sku(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    response = await client.patch(
        f"/products/{product['id']}",
        json={
            "name": "NVIDIA RTX 6090",
            "sku": "RTX6090",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == product["id"]
    assert data["name"] == "NVIDIA RTX 6090"
    assert data["sku"] == "RTX6090"


@pytest.mark.asyncio
async def test_update_nonexistent_product(
    client: AsyncClient,
) -> None:
    product_id = uuid4()

    response = await client.patch(
        f"/products/{product_id}",
        json={
            "name": "Updated Product",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Product with id={product_id} does not exist"
    )


@pytest.mark.asyncio
async def test_update_product_with_duplicate_sku(
    client: AsyncClient,
) -> None:
    first_product = await create_product(
        client,
        name="NVIDIA RTX 5090",
        sku="RTX5090",
    )

    second_product = await create_product(
        client,
        name="NVIDIA RTX 4090",
        sku="RTX4090",
    )

    response = await client.patch(
        f"/products/{second_product['id']}",
        json={
            "sku": first_product["sku"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Product with sku='RTX5090' already exists"
    )

    get_response = await client.get(
        f"/products/{second_product['id']}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["sku"] == "RTX4090"


@pytest.mark.asyncio
async def test_update_product_with_empty_payload(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    response = await client.patch(
        f"/products/{product['id']}",
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                "name": "",
            },
            id="empty-name",
        ),
        pytest.param(
            {
                "name": "   ",
            },
            id="whitespace-name",
        ),
        pytest.param(
            {
                "sku": "",
            },
            id="empty-sku",
        ),
        pytest.param(
            {
                "sku": "   ",
            },
            id="whitespace-sku",
        ),
        pytest.param(
            {
                "unexpected": "value",
            },
            id="extra-field",
        ),
        pytest.param(
            {
                "name": "X" * 256,
            },
            id="name-too-long",
        ),
        pytest.param(
            {
                "sku": "X" * 101,
            },
            id="sku-too-long",
        ),
    ],
)
async def test_update_product_with_invalid_payload(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    product = await create_product(client)

    response = await client.patch(
        f"/products/{product['id']}",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_product(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    response = await client.delete(
        f"/products/{product['id']}"
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = await client.get(
        f"/products/{product['id']}"
    )

    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_product(
    client: AsyncClient,
) -> None:
    product_id = uuid4()

    response = await client.delete(
        f"/products/{product_id}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        f"Product with id={product_id} does not exist"
    )


@pytest.mark.asyncio
async def test_delete_product_used_in_order(
    client: AsyncClient,
) -> None:
    product = await create_product(client)

    order_response = await client.post(
        "/orders",
        json={
            "items": [
                {
                    "product_id": product["id"],
                    "quantity": 2,
                },
            ],
        },
    )

    assert order_response.status_code == 201

    order = order_response.json()

    response = await client.delete(
        f"/products/{product['id']}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Product with id={product['id']} "
        f"is used in order with id={order['id']}"
    )


@pytest.mark.asyncio
async def test_delete_product_with_stock(
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

    response = await client.delete(
        f"/products/{product['id']}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Product with id={product['id']} "
        "has stock in inventory"
    )

    get_response = await client.get(
        f"/products/{product['id']}"
    )

    assert get_response.status_code == 200


@pytest.mark.asyncio
async def test_delete_product_with_empty_inventory(
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
        f"/products/{product['id']}"
    )

    assert response.status_code == 204

    product_response = await client.get(
        f"/products/{product['id']}"
    )

    assert product_response.status_code == 404

    inventory_response = await client.get(
        f"/warehouses/{warehouse['id']}/inventory"
    )

    assert inventory_response.status_code == 200
    assert inventory_response.json() == []