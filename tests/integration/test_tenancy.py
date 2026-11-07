"""Real HTTP/SQL regressions. Execution requires separate PostgreSQL approval."""

from uuid import uuid4

import pytest
import pytest_asyncio

from tests.factories import create_user, login

pytestmark = pytest.mark.asyncio


async def create_org(client, name):
    response = await client.post("/organizations", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


async def seed(client, organization):
    prefix = f"/organizations/{organization['id']}"
    product = await client.post(
        prefix + "/products", json={"name": "Product", "sku": "SAME-SKU"}
    )
    warehouse = await client.post(
        prefix + "/warehouses", json={"name": "Same warehouse", "location": "Riga"}
    )
    assert product.status_code == warehouse.status_code == 201
    product, warehouse = product.json(), warehouse.json()
    inventory = await client.post(
        prefix + f"/warehouses/{warehouse['id']}/inventory",
        json={"product_id": product["id"], "quantity": 10},
    )
    order = await client.post(
        prefix + "/orders",
        json={"items": [{"product_id": product["id"], "quantity": 6}]},
    )
    assert inventory.status_code == order.status_code == 201
    return prefix, product, warehouse, order.json()


@pytest_asyncio.fixture
async def owner(client):
    await create_user(client)
    await login(client)
    return client


async def test_tenant_lists_details_writes_and_references_are_isolated(owner):
    a = await create_org(owner, "Organization A")
    b = await create_org(owner, "Organization B")
    pa, product_a, warehouse_a, order_a = await seed(owner, a)
    pb, product_b, warehouse_b, order_b = await seed(owner, b)
    # Same SKU and warehouse name can exist independently in both tenants.
    for suffix, expected in (
        ("products", product_a),
        ("warehouses", warehouse_a),
        ("orders", order_a),
    ):
        response = await owner.get(f"{pa}/{suffix}")
        assert response.status_code == 200
        assert [row["id"] for row in response.json()] == [expected["id"]]
        assert all(row["organization_id"] == a["id"] for row in response.json())
    for resource, foreign in (
        ("products", product_b),
        ("warehouses", warehouse_b),
        ("orders", order_b),
    ):
        path = f"{pa}/{resource}/{foreign['id']}"
        assert (await owner.get(path)).status_code == 404
        assert (await owner.delete(path)).status_code == 404
        body = (
            {"items": [{"product_id": product_a["id"], "quantity": 1}]}
            if resource == "orders"
            else {"name": "Denied"}
        )
        assert (await owner.patch(path, json=body)).status_code == 404
    for action in ("allocate", "fulfill", "cancel"):
        assert (
            await owner.post(f"{pa}/orders/{order_b['id']}/{action}")
        ).status_code == 404
    assert (
        await owner.get(f"{pa}/warehouses/{warehouse_b['id']}/inventory")
    ).status_code == 404
    for method in ("PATCH", "DELETE"):
        assert (
            await owner.request(
                method,
                f"{pa}/warehouses/{warehouse_b['id']}/inventory/{product_b['id']}",
                json={"quantity": 0} if method == "PATCH" else None,
            )
        ).status_code == 404
    assert (
        await owner.post(
            f"{pa}/warehouses/{warehouse_a['id']}/inventory",
            json={"product_id": product_b["id"], "quantity": 1},
        )
    ).status_code == 404
    assert (
        await owner.post(
            f"{pa}/orders",
            json={"items": [{"product_id": product_b["id"], "quantity": 1}]},
        )
    ).status_code == 404
    assert (
        await owner.post(
            f"{pa}/products",
            json={"organization_id": b["id"], "name": "Denied", "sku": "DENIED"},
        )
    ).status_code == 422
    unchanged = await owner.get(f"{pb}/orders/{order_b['id']}")
    assert unchanged.json()["status"] == "pending"
    assert unchanged.json()["items"][0]["allocations"] == []
    # Allocation of tenant A must leave tenant B stock untouched.
    assert (
        await owner.post(f"{pa}/orders/{order_a['id']}/allocate")
    ).status_code == 200
    foreign_stock = await owner.get(f"{pb}/warehouses/{warehouse_b['id']}/inventory")
    assert foreign_stock.json()[0]["reserved_quantity"] == 0


async def test_nonmember_and_anonymous_cannot_discover_tenant(owner, client_factory):
    organization = await create_org(owner, "Private")
    prefix, product, warehouse, order = await seed(owner, organization)
    async with client_factory() as outsider:
        paths = [
            prefix,
            prefix + "/products",
            prefix + f"/products/{product['id']}",
            prefix + "/warehouses",
            prefix + f"/warehouses/{warehouse['id']}/inventory",
            prefix + "/orders",
            prefix + f"/orders/{order['id']}",
            prefix + "/members",
        ]
        for path in paths:
            assert (await outsider.get(path)).status_code == 401
        await create_user(outsider, email="outsider@example.com")
        await login(outsider, email="outsider@example.com")
        for path in paths:
            response = await outsider.get(path)
            assert response.status_code == 404
            assert response.json()["detail"] == "Organization not found"
        assert (
            await outsider.post(
                prefix + "/products", json={"name": "Denied", "sku": "D"}
            )
        ).status_code == 404
        assert (await outsider.get(f"/organizations/{uuid4()}")).status_code == 404
        assert (await outsider.get("/organizations")).json() == []


@pytest.mark.parametrize("role", ["owner", "admin", "manager", "viewer"])
async def test_all_business_roles_read_and_write_matrix(owner, client_factory, role):
    organization = await create_org(owner, "Role matrix")
    prefix, product, warehouse, order = await seed(owner, organization)
    pending = await owner.post(
        prefix + "/orders",
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )
    removable = await owner.post(
        prefix + "/products", json={"name": "Removable", "sku": "DELETE"}
    )
    empty_wh = await owner.post(
        prefix + "/warehouses", json={"name": "Empty", "location": "Riga"}
    )
    removable, empty_wh = removable.json(), empty_wh.json()
    inv_path = f"{prefix}/warehouses/{empty_wh['id']}/inventory"
    assert (
        await owner.post(inv_path, json={"product_id": removable["id"], "quantity": 0})
    ).status_code == 201
    async with client_factory() as member:
        if role == "owner":
            member.cookies.update(owner.cookies)
            member.headers["X-CSRF-Token"] = owner.headers["X-CSRF-Token"]
        else:
            await create_user(member, email="member@example.com")
            added = await owner.post(
                prefix + "/members", json={"email": "member@example.com", "role": role}
            )
            assert added.status_code == 201
            await login(member, email="member@example.com")
        for suffix in (
            "products",
            f"products/{product['id']}",
            "warehouses",
            f"warehouses/{warehouse['id']}",
            f"warehouses/{warehouse['id']}/inventory",
            "orders",
            f"orders/{order['id']}",
        ):
            assert (await member.get(f"{prefix}/{suffix}")).status_code == 200
        writes = [
            ("POST", "/products", {"name": "New", "sku": "NEW"}, 201),
            ("POST", "/warehouses", {"name": "New", "location": "Riga"}, 201),
            (
                "POST",
                "/orders",
                {"items": [{"product_id": product["id"], "quantity": 1}]},
                201,
            ),
            ("PATCH", f"/products/{removable['id']}", {"name": "Renamed"}, 200),
            ("PATCH", f"/warehouses/{empty_wh['id']}", {"name": "Renamed"}, 200),
            (
                "PATCH",
                f"/warehouses/{warehouse['id']}/inventory/{product['id']}",
                {"quantity": 10},
                200,
            ),
            (
                "DELETE",
                f"/warehouses/{empty_wh['id']}/inventory/{removable['id']}",
                None,
                204,
            ),
            (
                "POST",
                f"/warehouses/{empty_wh['id']}/inventory",
                {"product_id": product["id"], "quantity": 0},
                201,
            ),
            (
                "DELETE",
                f"/warehouses/{empty_wh['id']}/inventory/{product['id']}",
                None,
                204,
            ),
            ("DELETE", f"/products/{removable['id']}", None, 204),
            ("DELETE", f"/warehouses/{empty_wh['id']}", None, 204),
            (
                "PATCH",
                f"/orders/{order['id']}",
                {"items": [{"product_id": product["id"], "quantity": 6}]},
                200,
            ),
            ("POST", f"/orders/{order['id']}/allocate", None, 200),
            ("POST", f"/orders/{order['id']}/fulfill", None, 200),
            ("POST", f"/orders/{pending.json()['id']}/cancel", None, 200),
        ]
        for method, path, payload, success in writes:
            response = await member.request(method, prefix + path, json=payload)
            assert response.status_code == (403 if role == "viewer" else success), (
                method,
                path,
                response.text,
            )
        delete_order = await owner.post(
            prefix + "/orders",
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )
        response = await member.delete(f"{prefix}/orders/{delete_order.json()['id']}")
        assert response.status_code == (403 if role == "viewer" else 204)


async def test_membership_hierarchy_and_removal_revokes_tenant_access(
    owner, client_factory
):
    organization = await create_org(owner, "Hierarchy")
    prefix = f"/organizations/{organization['id']}"
    ids = {}
    async with client_factory() as member:
        for role in ("admin", "manager", "viewer"):
            user = await create_user(member, email=f"{role}@example.com")
            ids[role] = user["id"]
            assert (
                await owner.post(
                    prefix + "/members", json={"email": user["email"], "role": role}
                )
            ).status_code == 201
        assert (
            await owner.post(
                prefix + "/members",
                json={"email": "viewer@example.com", "role": "owner"},
            )
        ).status_code == 422
        assert (
            await owner.post(
                prefix + "/members",
                json={"email": "viewer@example.com", "role": "viewer"},
            )
        ).status_code == 409
        await login(member, email="admin@example.com")
        assert (await member.get(prefix + "/members")).status_code == 200
        assert (
            await member.post(
                prefix + "/members",
                json={"email": "viewer@example.com", "role": "admin"},
            )
        ).status_code == 403
        assert (
            await member.delete(prefix + f"/members/{ids['admin']}")
        ).status_code == 403
        owner_id = (await owner.get("/users/me")).json()["id"]
        assert (await member.delete(prefix + f"/members/{owner_id}")).status_code == 403
        await login(member, email="manager@example.com")
        assert (await member.get(prefix + "/members")).status_code == 403
        assert (
            await member.post(
                prefix + "/members",
                json={"email": "viewer@example.com", "role": "viewer"},
            )
        ).status_code == 403
        assert (
            await member.delete(prefix + f"/members/{ids['admin']}")
        ).status_code == 403
        # Preserve the intentional MANAGER -> VIEWER removal rule.
        assert (
            await member.delete(prefix + f"/members/{ids['viewer']}")
        ).status_code == 204
        await login(member, email="viewer@example.com")
        assert (await member.get(prefix)).status_code == 404


async def test_role_is_scoped_to_requested_organization(owner, client_factory):
    a, b = await create_org(owner, "A"), await create_org(owner, "B")
    async with client_factory() as member:
        await create_user(member, email="dual@example.com")
        for org, role in ((a, "manager"), (b, "viewer")):
            assert (
                await owner.post(
                    f"/organizations/{org['id']}/members",
                    json={"email": "dual@example.com", "role": role},
                )
            ).status_code == 201
        await login(member, email="dual@example.com")
        for org, expected in ((a, 201), (b, 403)):
            response = await member.post(
                f"/organizations/{org['id']}/products",
                json={"name": "Product", "sku": "SAME"},
            )
            assert response.status_code == expected


@pytest.mark.parametrize(
    "name",
    [
        "Acme Ltd",
        "12345678-1234-1234-1234-123456789abc",
        "12345678123412341234123456789abc",
    ],
)
async def test_organization_routes_resolve_uuid_and_unambiguous_slug(owner, name):
    from uuid import UUID

    org = await create_org(owner, name)
    with pytest.raises(ValueError):
        UUID(org["slug"])
    for identifier in (org["id"], org["slug"]):
        response = await owner.get(f"/organizations/{identifier}")
        assert response.status_code == 200
        assert response.json()["id"] == org["id"]
        assert (await owner.get(f"/organizations/{identifier}/products")).json() == []
    renamed = await owner.patch(
        f"/organizations/{org['slug']}", json={"name": "Renamed"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["slug"] == org["slug"]


async def test_business_writes_require_csrf_even_for_owner(owner):
    organization = await create_org(owner, "CSRF")
    prefix, product, warehouse, order = await seed(owner, organization)
    owner.headers.pop("X-CSRF-Token")
    for method, path, payload in (
        ("POST", "/products", {"name": "Denied", "sku": "DENIED"}),
        (
            "PATCH",
            f"/warehouses/{warehouse['id']}/inventory/{product['id']}",
            {"quantity": 0},
        ),
        ("POST", f"/orders/{order['id']}/allocate", None),
        ("DELETE", f"/orders/{order['id']}", None),
    ):
        assert (
            await owner.request(method, prefix + path, json=payload)
        ).status_code == 403
    assert (await owner.get(prefix + "/products")).status_code == 200


async def test_database_composite_foreign_keys_reject_cross_tenant_rows(
    owner, db_sessions
):
    from uuid import UUID

    from sqlalchemy.exc import IntegrityError

    from app.models.inventory import Inventory
    from app.models.order_allocation import OrderAllocation
    from app.models.order_item import OrderItem

    a, b = await create_org(owner, "FK A"), await create_org(owner, "FK B")
    pa, product_a, warehouse_a, order_a = await seed(owner, a)
    pb, product_b, warehouse_b, order_b = await seed(owner, b)
    stock_b = (
        await owner.get(f"{pb}/warehouses/{warehouse_b['id']}/inventory")
    ).json()[0]
    invalid_rows = [
        Inventory(
            organization_id=UUID(a["id"]),
            product_id=UUID(product_b["id"]),
            warehouse_id=UUID(warehouse_a["id"]),
            quantity=1,
        ),
        OrderItem(
            organization_id=UUID(a["id"]),
            order_id=UUID(order_b["id"]),
            product_id=UUID(product_a["id"]),
            quantity=1,
            position=99,
        ),
        OrderAllocation(
            organization_id=UUID(a["id"]),
            order_item_id=UUID(order_a["items"][0]["id"]),
            inventory_id=UUID(stock_b["id"]),
            product_id=UUID(product_a["id"]),
            quantity=1,
        ),
        OrderAllocation(
            organization_id=UUID(a["id"]),
            order_item_id=UUID(order_a["items"][0]["id"]),
            inventory_id=UUID(stock_b["id"]),
            product_id=UUID(product_b["id"]),
            quantity=1,
        ),
    ]
    for row in invalid_rows:
        async with db_sessions() as db:
            with pytest.raises(IntegrityError) as error:
                async with db.begin():
                    db.add(row)
                    await db.flush()
            assert error.value.orig.sqlstate == "23503"
    assert (await owner.get(pa + "/orders")).json()[0]["items"][0]["allocations"] == []
