"""
Configuration management for Voice Analysis Service
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Project settings
    project_id: str = os.getenv("PROJECT_ID", "senior-mhealth-2025")
    model_name: str = os.getenv("MODEL_NAME", "mental-health-analyzer")
    model_version: str = os.getenv("MODEL_VERSION", "v1.0.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Vertex AI settings
    vertex_endpoint_id: Optional[str] = os.getenv("VERTEX_ENDPOINT_ID")
    vertex_location: str = os.getenv("VERTEX_LOCATION", "asia-northeast3")
    vertex_model_id: Optional[str] = os.getenv("VERTEX_MODEL_ID")
    
    # Cloud Storage settings
    gcs_bucket: str = os.getenv("GCS_BUCKET", "senior-mhealth-models")
    model_path: str = os.getenv("MODEL_PATH", "models/sincnet/model.pt")
    audio_bucket: str = os.getenv("AUDIO_BUCKET", "senior-mhealth-472007.firebasestorage.app")
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8080))
    workers: int = int(os.getenv("WORKERS", 1))
    reload: bool = os.getenv("RELOAD", "false").lower() == "true"
    
    # Model serving settings
    max_batch_size: int = 32
    model_cache_ttl: int = 3600  # 1 hour
    request_timeout: int = 30
    max_audio_duration: int = 300  # 5 minutes
    warmup_enabled: bool = True
    
    # Performance settings
    enable_gpu: bool = os.getenv("ENABLE_GPU", "true").lower() == "true"
    memory_limit_mb: int = int(os.getenv("MEMORY_LIMIT_MB", 4096))
    cpu_cores: int = int(os.getenv("CPU_CORES", 2))
    
    # Monitoring and logging
    enable_metrics: bool = True
    enable_tracing: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_cloud_logging: bool = os.getenv("ENABLE_CLOUD_LOGGING", "true").lower() == "true"
    
    # Security settings
    api_key_required: bool = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    max_request_size_mb: int = 100
    
    # Cache settings
    redis_host: Optional[str] = os.getenv("REDIS_HOST")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "false").lower() == "true"
    cache_ttl: int = 300  # 5 minutes
    
    # Feature flags
    enable_batch_processing: bool = True
    enable_async_processing: bool = True
    enable_model_quantization: bool = False
    enable_onnx_runtime: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

def get_gcp_project_id() -> str:
    """Get GCP project ID from various sources"""
    settings = get_settings()
    
    # Try settings first
    if settings.project_id:
        return settings.project_id
    
    # Try metadata service (when running on GCP)
    try:
        import requests
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
            headers={"Metadata-Flavor": "Google"},
            timeout=1
        )
        if response.status_code == 200:
            return response.text
    except:
        pass
    
    return "senior-mhealth-2025"