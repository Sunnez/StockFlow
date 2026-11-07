from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserRead,
)
async def get_my_profile(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    return current_user