# app/domain/order.py

from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    ALLOCATED = "allocated"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
