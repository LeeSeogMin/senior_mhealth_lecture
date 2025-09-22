"""
Senior MHealth User Management API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

# Simple FastAPI app
app = FastAPI(
    title="Senior MHealth User API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# Root
@app.get("/")
async def root():
    return {"message": "Senior MHealth User Management API", "version": "1.0.0"}

# Import routes
try:
    from app.api.users import router as users_router
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
except ImportError:
    pass  # Routes not available

try:
    from app.api.seniors import router as seniors_router
    app.include_router(seniors_router, prefix="/api/v1/seniors", tags=["Seniors"])
except ImportError:
    pass  # Routes not available

try:
    from app.api.analysis import router as analysis_router
    app.include_router(analysis_router, prefix="/analyze", tags=["Analysis"])
except ImportError:
    pass  # Routes not available

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)