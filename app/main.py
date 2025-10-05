from fastapi import FastAPI
# IMPORTANTE: Adicionar 'user' na lista de imports
from .api.v1 import auth, wallet, marketplace, loans, admin, user
from .core.database import Base, engine
from .core.config import settings

app = FastAPI(title="Quark Platform API")

# Incluir o novo router de usuário
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(wallet.router, prefix="/api/v1/wallet", tags=["Wallet"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["Marketplace"])
app.include_router(loans.router, prefix="/api/v1", tags=["Loans"])

if settings.ENVIRONMENT == "development":
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin (Development Only)"])
    print("--- Admin endpoints loaded (DEVELOPMENT MODE) ---")

@app.get("/")
def read_root():
    return {"Project": "Quark API", "Status": "Running"}