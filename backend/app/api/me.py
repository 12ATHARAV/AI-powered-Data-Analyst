from fastapi import APIRouter, Depends

from app.db.models import User
from app.deps import get_current_user
from app.schemas import UserOut

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return currently authenticated user profile."""
    return UserOut.model_validate(current_user)
