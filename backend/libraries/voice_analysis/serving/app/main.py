"""
FastAPI application for voice analysis service
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager
import uvicorn
import uuid
import time
import logging
import psutil
import traceback
from datetime import datetime, timedelta
from typing import Optional, List

from prometheus_client import Counter, Histogram, Gauge, generate_latest
import asyncio

from app.config import get_settings
from app.models import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    HealthCheckResponse,
    ErrorResponse,
    AnalysisType
)
from app.inference import get_inference_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Metrics
request_count = Counter('prediction_requests_total', 'Total prediction requests')
request_duration = Histogram('prediction_duration_seconds', 'Prediction request duration')
active_requests = Gauge('active_requests', 'Number of active requests')
model_load_time = Gauge('model_load_time_seconds', 'Model loading time')
error_count = Counter('prediction_errors_total', 'Total prediction errors')

# Global variables
app_start_time = time.time()
inference_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global inference_engine
    
    # Startup
    logger.info(f"Starting {settings.model_name} service v{settings.model_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Load model
    start_time = time.time()
    try:
        inference_engine = get_inference_engine()
        load_time = time.time() - start_time
        model_load_time.set(load_time)
        logger.info(f"Model loaded in {load_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        # Continue anyway for health checks
    
    yield
    
    # Shutdown
    logger.info("Shutting down service")

# Create FastAPI app
app = FastAPI(
    title="Senior_MHealth Voice Analysis API",
    description="AI-powered voice analysis for mental health assessment",
    version=settings.model_version,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.run.app", "localhost"]
    )

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    error_id = str(uuid.uuid4())
    logger.error(f"Unhandled exception {error_id}: {exc}\n{traceback.format_exc()}")
    error_count.inc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"error_id": error_id} if settings.environment != "production" else None,
            request_id=getattr(request.state, "request_id", None)
        ).dict()
    )

# Health check endpoint
@app.get("/", response_model=HealthCheckResponse)
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Service health check"""
    uptime = int(time.time() - app_start_time)
    
    # Get memory usage
    process = psutil.Process()
    memory_usage_mb = process.memory_info().rss / 1024 / 1024
    
    # Check GPU availability
    gpu_available = False
    try:
        import torch
        gpu_available = torch.cuda.is_available()
    except:
        pass
    
    return HealthCheckResponse(
        status="healthy" if inference_engine and inference_engine.model_loaded else "degraded",
        model_loaded=inference_engine.model_loaded if inference_engine else False,
        model_version=settings.model_version,
        environment=settings.environment,
        uptime_seconds=uptime,
        last_prediction=datetime.fromtimestamp(inference_engine.last_prediction_time) if inference_engine and inference_engine.last_prediction_time else None,
        gpu_available=gpu_available,
        memory_usage_mb=int(memory_usage_mb)
    )

# Prediction endpoint
@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, background_tasks: BackgroundTasks):
    """Perform voice analysis prediction"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Metrics
    request_count.inc()
    active_requests.inc()
    
    try:
        # Check if model is loaded
        if not inference_engine or not inference_engine.model_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not loaded"
            )
        
        # Perform analysis
        logger.info(f"Processing request {request_id} for user {request.user_id}")
        
        analysis_result = await inference_engine.analyze(
            audio_url=request.audio_url,
            analysis_type=request.analysis_type.value
        )
        
        # Generate recommendations
        recommendations = generate_recommendations(
            analysis_result['emotions'],
            analysis_result['mental_health']
        )
        
        # Check for risk alerts
        risk_alerts = generate_risk_alerts(analysis_result['mental_health'])
        
        # Create response
        response = PredictionResponse(
            request_id=request_id,
            timestamp=datetime.utcnow(),
            status="success",
            emotions=analysis_result['emotions'] if request.analysis_type in [AnalysisType.EMOTION, AnalysisType.COMPREHENSIVE] else None,
            mental_health=analysis_result['mental_health'] if request.analysis_type in [AnalysisType.MENTAL_HEALTH, AnalysisType.COMPREHENSIVE] else None,
            voice_features=analysis_result['voice_features'],
            voice_biomarkers=analysis_result.get('voice_biomarkers'),
            confidence=analysis_result['confidence'],
            processing_time_ms=analysis_result['processing_time_ms'],
            model_version=settings.model_version,
            analysis_type=request.analysis_type,
            recommendations=recommendations,
            risk_alerts=risk_alerts
        )
        
        # Log metrics
        processing_time = time.time() - start_time
        request_duration.observe(processing_time)
        logger.info(f"Request {request_id} completed in {processing_time:.2f}s")
        
        # Background task for analytics (if needed)
        if settings.enable_metrics:
            background_tasks.add_task(log_analytics, request, response)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error_count.inc()
        logger.error(f"Prediction failed for request {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )
    finally:
        active_requests.dec()

# Batch prediction endpoint
@app.post("/batch_predict", response_model=BatchPredictionResponse)
async def batch_predict(batch_request: BatchPredictionRequest):
    """Process multiple predictions in batch"""
    batch_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Processing batch {batch_id} with {len(batch_request.requests)} requests")
    
    results = []
    successful = 0
    failed = 0
    
    # Process requests (could be parallelized)
    for req in batch_request.requests:
        try:
            # Create individual prediction
            response = await predict(req, BackgroundTasks())
            results.append(response)
            successful += 1
        except Exception as e:
            logger.error(f"Batch item failed: {e}")
            # Create error response
            results.append(PredictionResponse(
                request_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                status="failed",
                confidence=0,
                processing_time_ms=0,
                model_version=settings.model_version,
                analysis_type=req.analysis_type
            ))
            failed += 1
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return BatchPredictionResponse(
        batch_id=batch_id,
        total_requests=len(batch_request.requests),
        successful=successful,
        failed=failed,
        results=results,
        processing_time_ms=processing_time
    )

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest())

# Utility functions
def generate_recommendations(emotions, mental_health) -> List[str]:
    """Generate personalized recommendations based on analysis"""
    recommendations = []
    
    # Emotion-based recommendations
    if emotions and emotions.dominant_emotion == "sadness":
        recommendations.append("Consider engaging in activities that bring joy")
    if emotions and emotions.dominant_emotion == "anger":
        recommendations.append("Practice relaxation techniques like deep breathing")
    
    # Mental health based recommendations
    if mental_health:
        if mental_health.stress_level > 0.7:
            recommendations.append("High stress detected - consider stress management techniques")
        if mental_health.anxiety_level > 0.7:
            recommendations.append("Elevated anxiety - mindfulness exercises may help")
        if mental_health.depression_risk > 0.6:
            recommendations.append("Consider speaking with a mental health professional")
    
    return recommendations[:3]  # Limit to top 3 recommendations

def generate_risk_alerts(mental_health) -> Optional[List[str]]:
    """Generate risk alerts if thresholds are exceeded"""
    alerts = []
    
    if mental_health:
        if mental_health.depression_risk > 0.8:
            alerts.append("High depression risk detected")
        if mental_health.anxiety_level > 0.8:
            alerts.append("High anxiety level detected")
        if mental_health.overall_risk_score > 0.75:
            alerts.append("Overall mental health risk elevated")
    
    return alerts if alerts else None

async def log_analytics(request: PredictionRequest, response: PredictionResponse):
    """Log analytics data (placeholder for actual implementation)"""
    try:
        # This would send data to analytics service
        logger.debug(f"Analytics logged for request {response.request_id}")
    except Exception as e:
        logger.error(f"Failed to log analytics: {e}")

# Main entry point
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )