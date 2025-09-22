#!/usr/bin/env python3
import os
import logging
from google.cloud import storage
from google.cloud.exceptions import NotFound

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models():
    """Download SincNet models from GCS at runtime - gracefully handle missing models"""
    try:
        # SincNet 모델 사용 여부 확인
        use_sincnet = os.environ.get('USE_SINCNET', 'false').lower() == 'true'

        if not use_sincnet:
            logger.info("SincNet is disabled, skipping model download")
            return True

        bucket_name = os.environ.get('GCS_MODEL_BUCKET', 'senior-mhealth-models')
        local_dir = os.environ.get('SINCNET_MODEL_DIR', '/tmp/sincnet_models')

        # Create local directory
        os.makedirs(local_dir, exist_ok=True)

        try:
            # Check if bucket exists
            client = storage.Client()
            bucket = client.bucket(bucket_name)

            # Test bucket accessibility
            if not bucket.exists():
                logger.warning(f"Model bucket '{bucket_name}' does not exist")
                logger.info("SincNet models not available - running without SincNet")
                return True  # Continue without models

        except Exception as e:
            logger.warning(f"Cannot access model bucket: {e}")
            logger.info("SincNet models not available - running without SincNet")
            return True  # Continue without models

        models = [
            'sincnet/dep_model_10500_raw.pkl',
            'sincnet/insom_model_38800_raw.pkl'
        ]

        downloaded_count = 0
        for model_path in models:
            try:
                blob = bucket.blob(model_path)
                local_path = os.path.join(local_dir, os.path.basename(model_path))

                if not os.path.exists(local_path):
                    if blob.exists():
                        logger.info(f"Downloading {model_path} to {local_path}")
                        blob.download_to_filename(local_path)
                        downloaded_count += 1
                    else:
                        logger.warning(f"Model not found in bucket: {model_path}")
                else:
                    logger.info(f"Model already cached: {local_path}")
                    downloaded_count += 1

            except Exception as e:
                logger.warning(f"Failed to download {model_path}: {e}")
                continue

        if downloaded_count == 0:
            logger.warning("No SincNet models could be downloaded")
            logger.info("Service will run without SincNet analysis")
        else:
            logger.info(f"Downloaded {downloaded_count}/{len(models)} models successfully")

        return True  # Always return True to not block service startup

    except Exception as e:
        logger.error(f"Unexpected error in model download: {e}")
        logger.info("Service will continue without SincNet models")
        return True  # Don't fail the service startup

if __name__ == "__main__":
    download_models()