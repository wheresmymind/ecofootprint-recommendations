# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import recommendations
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EcoFootprint Recommendation API",
    description="API to generate carbon footprint reduction recommendations using AI.",
    version="1.0.0"
)

# Add CORS middleware to allow any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router
app.include_router(
    recommendations.router,
    prefix="/api/v1/recommendations",
    tags=["Recommendations"]        
)

@app.get("/", tags=["Health Check"])
async def read_root():
    logger.info("Health check endpoint '/' accessed.")
    return {"message": "Welcome to the EcoFootprint Recommendation API!"}
