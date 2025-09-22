# BigQuery ML Dataset

BigQuery ML dataset and tables for Senior MHealth multimodal analysis training pipeline.

## 📊 Dataset Overview

**Dataset**: `senior-mhealth-472007.ml_training`
**Location**: `asia-northeast3`
**Purpose**: ML training data storage for multimodal depression/anxiety detection

## 🗄️ Table Schema

### 1. `multimodal_dataset` - ML Training Data

**Partitioning**: `DATE(timestamp)` (90-day expiration)
**Clustering**: `user_id`, `split`

| Field | Type | Description |
|-------|------|-------------|
| `sample_id` | STRING | Unique training sample identifier |
| `user_id` | STRING | User identifier |
| `session_id` | STRING | Analysis session identifier |
| `timestamp` | TIMESTAMP | Data collection timestamp |
| `audio_gcs_uri` | STRING | GCS path to audio file |
| `text_content` | STRING | Whisper transcription |
| `text_embedding` | FLOAT[] | 768-dim text embedding |
| `voice_features` | RECORD | Voice/speech features |
| `labels` | RECORD | ML target labels |
| `label_source` | STRING | Label source type |
| `label_confidence` | FLOAT | Label confidence (0-1) |
| `model_version` | STRING | Model version |
| `data_version` | STRING | Data pipeline version |
| `split` | STRING | train/val/test split |

#### Voice Features Structure
```json
{
  "speech_rate": FLOAT,        // Words per minute
  "pause_ratio": FLOAT,        // Silence ratio
  "energy_level": FLOAT,       // Voice energy
  "pitch_variance": FLOAT,     // Pitch variance
  "mfcc_features": FLOAT[],    // MFCC features
  "prosody_embedding": FLOAT[] // Prosody embedding
}
```

#### Labels Structure
```json
{
  "depression": FLOAT,        // Depression score (0-1)
  "anxiety": FLOAT,           // Anxiety score (0-1)
  "cognitive": FLOAT,         // Cognitive score (0-1)
  "sleep_quality": FLOAT,     // Sleep quality
  "social_engagement": FLOAT, // Social engagement
  "appetite_change": FLOAT    // Appetite change
}
```

### 2. `model_performance` - Model Tracking

| Field | Type | Description |
|-------|------|-------------|
| `model_id` | STRING | Model identifier |
| `model_version` | STRING | Version string |
| `trained_at` | TIMESTAMP | Training timestamp |
| `architecture` | STRING | Model architecture |
| `training_samples` | INTEGER | Training sample count |
| `epochs` | INTEGER | Training epochs |
| `learning_rate` | FLOAT | Learning rate |
| `metrics` | RECORD | Performance metrics |
| `deployment_status` | STRING | Deployment status |
| `deployment_timestamp` | TIMESTAMP | Deployment time |

#### Metrics Structure
```json
{
  "train_loss": FLOAT,        // Training loss
  "val_loss": FLOAT,          // Validation loss
  "depression_mae": FLOAT,    // Depression MAE
  "anxiety_mae": FLOAT,       // Anxiety MAE
  "cognitive_mae": FLOAT,     // Cognitive MAE
  "overall_accuracy": FLOAT   // Overall accuracy
}
```

## 🚀 Setup Instructions

1. **Run Setup Script**:
   ```bash
   cd setup/scripts
   10-setup-bigquery.bat
   ```

2. **Verify Setup**:
   ```sql
   SELECT COUNT(*) FROM `senior-mhealth-472007.ml_training.multimodal_dataset`;
   ```

## 📈 Data Pipeline Integration

### Firestore → Cloud SQL → BigQuery Flow

1. **Real-time**: Firestore ETL function syncs to Cloud SQL
2. **Batch**: Daily sync from Cloud SQL to BigQuery ML dataset
3. **Training**: ML pipelines consume BigQuery data

### Data Quality Monitoring

- **Partition Monitoring**: Track daily data volume
- **Schema Validation**: Ensure consistent data types
- **Label Quality**: Monitor label_confidence distributions
- **Feature Completeness**: Check for missing embeddings/features

## 🔒 Access Control

**Service Account**: `senior-mhealth-service@senior-mhealth-472007.iam.gserviceaccount.com`
**Roles**:
- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`

## 📊 Sample Queries

### Training Data Analysis
```sql
-- Sample count by split and label source
SELECT
  split,
  label_source,
  COUNT(*) as sample_count,
  AVG(label_confidence) as avg_confidence
FROM `senior-mhealth-472007.ml_training.multimodal_dataset`
GROUP BY split, label_source
ORDER BY split, label_source;
```

### Model Performance Tracking
```sql
-- Latest model performance by architecture
SELECT
  architecture,
  model_version,
  metrics.val_loss,
  metrics.overall_accuracy,
  trained_at
FROM `senior-mhealth-472007.ml_training.model_performance`
QUALIFY ROW_NUMBER() OVER (PARTITION BY architecture ORDER BY trained_at DESC) = 1;
```

### Data Quality Check
```sql
-- Check for missing features
SELECT
  COUNT(*) as total_samples,
  COUNTIF(voice_features.speech_rate IS NULL) as missing_speech_rate,
  COUNTIF(ARRAY_LENGTH(text_embedding) = 0) as missing_text_embedding,
  COUNTIF(labels.depression IS NULL) as missing_depression_label
FROM `senior-mhealth-472007.ml_training.multimodal_dataset`
WHERE DATE(timestamp) = CURRENT_DATE();
```

## 🔧 Maintenance

- **Partition Cleanup**: Automatic 90-day expiration
- **Schema Evolution**: Use `bq update` for non-breaking changes
- **Cost Optimization**: Monitor query costs and optimize clustering
- **Backup**: Export critical training datasets periodically