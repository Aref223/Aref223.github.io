from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import settings
from ..models.user import User

reuseable_oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(reuseable_oauth)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_email: str = payload.get("sub")
        if user_email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        raise credentials_exception
    return user