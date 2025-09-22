"""
Simple configuration
"""
import os

class Settings:
    app_name = "Senior MHealth User API"
    version = "1.0.0"
    description = "User Management API"

    port = int(os.getenv("PORT", 8080))
    environment = os.getenv("ENVIRONMENT", "development")

    @property
    def is_production(self):
        return self.environment == "production"

    @property
    def allowed_origins(self):
        if self.is_production:
            return ["*"]  # Allow all for now
        return ["*"]

settings = Settings()

def get_settings():
    return settings