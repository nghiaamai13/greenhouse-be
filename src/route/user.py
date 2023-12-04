from fastapi import Depends, APIRouter, HTTPException, Security, Response
from sqlalchemy.orm import Session
from starlette import status
from uuid import UUID

from src import schemas, models, utils, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/api",
    tags=["User"]
)


@router.post("/customer", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_customer(user_credentials: schemas.UserCreate, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    
    username = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    hashed_password = utils.get_password_hash(user_credentials.password)
    user_credentials.password = hashed_password
    new_user = models.User(created_by=current_user.user_id, **user_credentials.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/tenant", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
def create_tenant(user_credentials: schemas.TenantCreate, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["admin"])):
    
    username = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    hashed_password = utils.get_password_hash(user_credentials.password)
    user_credentials.password = hashed_password
    new_user = models.User(created_by=current_user.user_id, **user_credentials.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.delete("/customer/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer(customer_id: UUID, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["tenant"])):
    customer_query = db.query(models.User).filter(models.User.user_id == customer_id,
                                                  models.User.created_by == current_user.user_id)
    if customer_query.first() == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            ,detail="Not found or invalid ownership detected.")
    customer_query.delete(synchronize_session=False)
    
    db.commit()
    
    return Response(status_code=status.HTTP_200_OK, content="Successfully deleted customer")


@router.delete("/tenant/{tenant_id}", status_code=status.HTTP_200_OK)
def delete_tenant(tenant_id: UUID, db: Session = Depends(get_db),
                    current_user: models.User = Security(oauth2.get_current_user, scopes=["admin"])):
    tenant = db.query(models.User).filter(models.User.user_id == tenant_id)
    if tenant.first() == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            ,detail="Tenant not found")
    tenant.delete(synchronize_session=False)
    
    db.commit()
    
    return Response(status_code=200, content="Successfully deleted tenant")