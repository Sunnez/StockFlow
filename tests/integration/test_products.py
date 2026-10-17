from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


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