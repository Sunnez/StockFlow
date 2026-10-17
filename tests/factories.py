from typing import Any

from httpx import AsyncClient


async def create_product(
    client: AsyncClient,
    *,
    name: str = "NVIDIA RTX 5090",
    sku: str = "RTX5090",
) -> dict[str, Any]:
    response = await client.post(
        "/products",
        json={
            "name": name,
            "sku": sku,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def create_warehouse(
    client: AsyncClient,
    *,
    name: str = "Riga Warehouse",
    location: str = "Riga, Latvia",
) -> dict[str, Any]:
    response = await client.post(
        "/warehouses",
        json={
            "name": name,
            "location": location,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


async def create_inventory(
    client: AsyncClient,
    *,
    warehouse_id: str,
    product_id: str,
    quantity: int = 10,
) -> dict[str, Any]:
    response = await client.post(
        f"/warehouses/{warehouse_id}/inventory",
        json={
            "product_id": product_id,
            "quantity": quantity,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()