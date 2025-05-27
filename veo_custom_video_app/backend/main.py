from fastapi import FastAPI
from veo_custom_video_app.backend.api import routes as api_routes
from veo_custom_video_app.backend.services.veo_service import VeoService
from veo_custom_video_app.backend.database import init_db, DATABASE_URL # Import init_db and potentially DATABASE_URL for logging

# Global VeoService instance (for simplicity in this context)
# In a production app, you'd likely use FastAPI's Depends for better management and testing.
veo_service_instance = VeoService(api_key="FAKE_KEY", api_endpoint="https://fake-veo-api.com/v3")

app = FastAPI(
    title="VEO Custom Video API",
    description="API for managing agencies, visions (campaigns), and video generation tasks.",
    version="0.1.0",
)

@app.on_event("startup")
async def startup_event():
    print("INFO:     Starting up application...")
    print(f"INFO:     Attempting to initialize database tables with DATABASE_URL: {DATABASE_URL}")
    try:
        init_db()
        print("INFO:     Database tables initialization process completed.")
    except Exception as e:
        print(f"ERROR:    Database initialization failed: {e}")
        # Depending on the severity, you might want to prevent startup or log more details.

# Make the service instance available to routers/app state if needed,
# though direct import or dependency injection in routes is cleaner.
# For this example, we'll allow routes to import this instance.
app.state.veo_service = veo_service_instance

app.include_router(api_routes.router, prefix="/api/v1")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the VEO Custom Video API"}

# Optional: Add a health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
