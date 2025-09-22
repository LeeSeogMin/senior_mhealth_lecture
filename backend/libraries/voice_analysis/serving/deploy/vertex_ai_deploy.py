"""
Vertex AI model deployment script
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

from google.cloud import aiplatform
from google.cloud import storage
from google.cloud.aiplatform import Model, Endpoint
import click

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VertexAIDeployer:
    """Vertex AI model deployment manager"""
    
    def __init__(
        self,
        project_id: str,
        location: str = "asia-northeast3",
        staging_bucket: str = None
    ):
        self.project_id = project_id
        self.location = location
        self.staging_bucket = staging_bucket or f"{project_id}-vertex-staging"
        
        # Initialize Vertex AI
        aiplatform.init(
            project=project_id,
            location=location,
            staging_bucket=f"gs://{self.staging_bucket}"
        )
        
        logger.info(f"Initialized Vertex AI for project {project_id} in {location}")
    
    def upload_model_artifact(
        self,
        local_model_path: str,
        model_name: str,
        version: str = None
    ) -> str:
        """Upload model artifact to Cloud Storage"""
        try:
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(self.staging_bucket)
            
            # Create versioned path
            version = version or datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_path = f"models/{model_name}/{version}/model.pt"
            
            # Upload file
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(local_model_path)
            
            gcs_uri = f"gs://{self.staging_bucket}/{blob_path}"
            logger.info(f"Model uploaded to {gcs_uri}")
            
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload model: {e}")
            raise
    
    def create_model_registry(
        self,
        display_name: str,
        artifact_uri: str,
        serving_container_uri: str = None,
        description: str = None,
        labels: Dict[str, str] = None,
        serving_env_vars: Dict[str, str] = None
    ) -> Model:
        """Register model in Vertex AI Model Registry"""
        try:
            # Use default PyTorch container if not specified
            if not serving_container_uri:
                serving_container_uri = (
                    "asia-docker.pkg.dev/vertex-ai/prediction/"
                    "pytorch-gpu.2-1:latest"
                )
            
            # Default environment variables
            env_vars = {
                "MODEL_NAME": display_name,
                "ENABLE_METRICS": "true"
            }
            if serving_env_vars:
                env_vars.update(serving_env_vars)
            
            # Upload model
            model = aiplatform.Model.upload(
                display_name=display_name,
                artifact_uri=os.path.dirname(artifact_uri),
                serving_container_image_uri=serving_container_uri,
                serving_container_predict_route="/predict",
                serving_container_health_route="/health",
                serving_container_ports=[8080],
                serving_container_environment_variables=env_vars,
                description=description,
                labels=labels or {
                    "framework": "pytorch",
                    "task": "voice-analysis",
                    "team": "ai"
                }
            )
            
            logger.info(f"Model registered: {model.display_name} (Resource: {model.resource_name})")
            return model
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            raise
    
    def deploy_to_endpoint(
        self,
        model: Model,
        endpoint_display_name: str,
        machine_type: str = "n1-standard-4",
        accelerator_type: str = None,
        accelerator_count: int = 0,
        min_replica_count: int = 1,
        max_replica_count: int = 3,
        traffic_percentage: int = 100,
        enable_autoscaling: bool = True
    ) -> Endpoint:
        """Deploy model to endpoint"""
        try:
            # Check for existing endpoint
            endpoints = aiplatform.Endpoint.list(
                filter=f'display_name="{endpoint_display_name}"'
            )
            
            if endpoints:
                endpoint = endpoints[0]
                logger.info(f"Using existing endpoint: {endpoint.display_name}")
            else:
                # Create new endpoint
                endpoint = aiplatform.Endpoint.create(
                    display_name=endpoint_display_name,
                    labels={
                        "environment": "production",
                        "model_type": "voice_analysis"
                    }
                )
                logger.info(f"Created new endpoint: {endpoint.display_name}")
            
            # Autoscaling configuration
            if enable_autoscaling:
                autoscaling_config = {
                    "min_replica_count": min_replica_count,
                    "max_replica_count": max_replica_count,
                    "metric_specs": [
                        {
                            "metric_name": "aiplatform.googleapis.com/prediction/online/cpu/utilization",
                            "target": 60
                        }
                    ]
                }
            else:
                autoscaling_config = None
            
            # Deploy model
            deployed_model = endpoint.deploy(
                model=model,
                deployed_model_display_name=f"{model.display_name}-deployment",
                machine_type=machine_type,
                accelerator_type=accelerator_type,
                accelerator_count=accelerator_count,
                min_replica_count=min_replica_count,
                max_replica_count=max_replica_count,
                traffic_percentage=traffic_percentage,
                autoscaling_config=autoscaling_config,
                sync=True
            )
            
            logger.info(f"Model deployed to endpoint: {endpoint.resource_name}")
            logger.info(f"Endpoint ID: {endpoint.name}")
            
            return endpoint
            
        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise
    
    def setup_monitoring(
        self,
        endpoint: Endpoint,
        email_alerts: List[str] = None,
        sampling_rate: float = 0.1
    ):
        """Setup monitoring for deployed model"""
        try:
            # Create monitoring configuration
            monitoring_config = {
                "display_name": f"{endpoint.display_name}-monitoring",
                "endpoint": endpoint.resource_name,
                "logging_sampling_strategy": {
                    "random_sample_config": {
                        "sample_rate": sampling_rate
                    }
                },
                "schedule_config": {
                    "monitor_interval": {
                        "seconds": 3600  # 1 hour
                    }
                },
                "alert_config": {
                    "user_emails": email_alerts or [],
                    "enable_logging": True
                }
            }
            
            # Note: Actual monitoring job creation would require additional setup
            logger.info(f"Monitoring configuration prepared for {endpoint.display_name}")
            logger.info(f"Sampling rate: {sampling_rate * 100}%")
            
            if email_alerts:
                logger.info(f"Alert emails: {', '.join(email_alerts)}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
            raise
    
    def test_endpoint(
        self,
        endpoint: Endpoint,
        test_instance: Dict
    ) -> Dict:
        """Test deployed endpoint"""
        try:
            logger.info(f"Testing endpoint {endpoint.display_name}...")
            
            # Make prediction
            response = endpoint.predict(
                instances=[test_instance],
                parameters={}
            )
            
            logger.info("Test successful!")
            logger.info(f"Response: {response.predictions[0]}")
            
            return response.predictions[0]
            
        except Exception as e:
            logger.error(f"Endpoint test failed: {e}")
            raise
    
    def undeploy_model(
        self,
        endpoint_name: str,
        deployed_model_id: str
    ):
        """Undeploy a model from endpoint"""
        try:
            endpoint = aiplatform.Endpoint(endpoint_name)
            endpoint.undeploy(deployed_model_id=deployed_model_id)
            logger.info(f"Model {deployed_model_id} undeployed from {endpoint_name}")
            
        except Exception as e:
            logger.error(f"Failed to undeploy model: {e}")
            raise

@click.command()
@click.option('--project-id', required=True, help='GCP Project ID')
@click.option('--location', default='asia-northeast3', help='Vertex AI location')
@click.option('--model-path', required=True, help='Path to local model file')
@click.option('--model-name', default='voice-analysis-model', help='Model display name')
@click.option('--endpoint-name', default='voice-analysis-endpoint', help='Endpoint display name')
@click.option('--machine-type', default='n1-standard-4', help='Machine type for deployment')
@click.option('--gpu-type', help='GPU type (e.g., NVIDIA_TESLA_T4)')
@click.option('--gpu-count', default=0, type=int, help='Number of GPUs')
@click.option('--min-replicas', default=1, type=int, help='Minimum replicas')
@click.option('--max-replicas', default=3, type=int, help='Maximum replicas')
@click.option('--test', is_flag=True, help='Run endpoint test after deployment')
@click.option('--monitor-emails', multiple=True, help='Email addresses for monitoring alerts')
def deploy(
    project_id: str,
    location: str,
    model_path: str,
    model_name: str,
    endpoint_name: str,
    machine_type: str,
    gpu_type: Optional[str],
    gpu_count: int,
    min_replicas: int,
    max_replicas: int,
    test: bool,
    monitor_emails: tuple
):
    """Deploy model to Vertex AI"""
    
    # Initialize deployer
    deployer = VertexAIDeployer(
        project_id=project_id,
        location=location
    )
    
    # Step 1: Upload model artifact
    logger.info("Step 1: Uploading model artifact...")
    artifact_uri = deployer.upload_model_artifact(
        local_model_path=model_path,
        model_name=model_name
    )
    
    # Step 2: Register model
    logger.info("Step 2: Registering model in Model Registry...")
    model = deployer.create_model_registry(
        display_name=model_name,
        artifact_uri=artifact_uri,
        description=f"Voice analysis model deployed on {datetime.now().isoformat()}",
        labels={
            "version": datetime.now().strftime("%Y%m%d"),
            "framework": "pytorch",
            "task": "mental-health-analysis"
        }
    )
    
    # Step 3: Deploy to endpoint
    logger.info("Step 3: Deploying model to endpoint...")
    endpoint = deployer.deploy_to_endpoint(
        model=model,
        endpoint_display_name=endpoint_name,
        machine_type=machine_type,
        accelerator_type=gpu_type,
        accelerator_count=gpu_count,
        min_replica_count=min_replicas,
        max_replica_count=max_replicas,
        traffic_percentage=100
    )
    
    # Step 4: Setup monitoring
    if monitor_emails:
        logger.info("Step 4: Setting up monitoring...")
        deployer.setup_monitoring(
            endpoint=endpoint,
            email_alerts=list(monitor_emails)
        )
    
    # Step 5: Test endpoint
    if test:
        logger.info("Step 5: Testing endpoint...")
        test_instance = {
            "audio_url": "gs://test-bucket/sample.wav",
            "analysis_type": "comprehensive"
        }
        deployer.test_endpoint(endpoint, test_instance)
    
    # Print summary
    logger.info("=" * 50)
    logger.info("Deployment Summary:")
    logger.info(f"Model: {model.display_name}")
    logger.info(f"Model ID: {model.name}")
    logger.info(f"Endpoint: {endpoint.display_name}")
    logger.info(f"Endpoint ID: {endpoint.name}")
    logger.info(f"Region: {location}")
    logger.info("=" * 50)
    
    # Save endpoint ID for later use
    config_file = Path("endpoint_config.json")
    config = {
        "endpoint_id": endpoint.name,
        "endpoint_name": endpoint.display_name,
        "model_id": model.name,
        "model_name": model.display_name,
        "project_id": project_id,
        "location": location,
        "deployed_at": datetime.now().isoformat()
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Configuration saved to {config_file}")

if __name__ == "__main__":
    deploy()