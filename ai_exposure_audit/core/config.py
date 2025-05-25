import os
from dotenv import load_dotenv

load_dotenv() # Loads environment variables from .env file if present

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")

# Placeholder for database URL if not already there
# SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_exposure_audit.db")

AI_JOB_TITLE_KEYWORDS = [
    "AI", "Artificial Intelligence", "Machine Learning", "ML ", # Space after ML to avoid matching "HTML"
    "Data Scientist", "Deep Learning", "NLP", "Natural Language Processing",
    "Computer Vision", "Robotics Engineer", "AI Engineer", "ML Engineer"
]
