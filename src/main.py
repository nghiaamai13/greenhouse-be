from fastapi import FastAPI

from src import models, utils
from src.database import SessionLocal
from src.database import engine
from src.route import device, user, auth, farm

app = FastAPI()

#models.Base.metadata.create_all(bind=engine)

app.include_router(device.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(farm.router)


@app.on_event("startup")
def start():
    db = SessionLocal()
    try:
        if not db.query(models.User).all():
            admin_user = models.User(username="admin",
                                     password=utils.get_password_hash("admin"),
                                     role="admin")
            db.add(admin_user)
            db.commit()
            print(admin_user)
    finally:
        db.close()


@app.get('/')
def home():
    return {"message": "Hello"}
