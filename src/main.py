from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, utils
from .database import SessionLocal
from .database import engine
from .route import device, user, auth, farm, telemetry

app = FastAPI(
    title="Greenhouse",
    description="API for greenhouse project",
    version="0.1.0"
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#models.Base.metadata.create_all(bind=engine)

app.include_router(device.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(farm.router)
app.include_router(telemetry.router)

@app.on_event("startup")
def create_admin():
    db = SessionLocal()
    try:
        if not db.query(models.User).all():
            admin_user = models.User(username="admin",
                                     password=utils.get_password_hash("admin"),
                                     role="admin",
                                     created_by='00000000-0000-0000-0000-000000000000')
            db.add(admin_user)
            db.commit()
            print(admin_user)
    finally:
        db.close()


@app.get('/')
def home():
    return {"message": "Hello"}
