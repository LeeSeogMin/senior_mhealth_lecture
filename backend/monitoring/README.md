# ETL Pipeline Monitoring & Alerting

Comprehensive monitoring and alerting system for the Senior MHealth ETL pipeline.

## 📊 Overview

This monitoring system provides real-time visibility into the 3-tier ETL pipeline:
- **Firestore → Cloud SQL** (Real-time ETL)
- **Cloud SQL → BigQuery** (Batch ETL)
- **Custom Metrics Collection** (Data quality and freshness)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firestore     │───▶│   Cloud SQL     │───▶│   BigQuery ML   │
│   (Sessions)    │    │  (PostgreSQL)   │    │   (Training)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                Cloud Monitoring Dashboard                        │
├─────────────────────────────────────────────────────────────────┤
│ • Function Executions  • Error Rates     • Data Freshness      │
│ • Latency Metrics     • SQL Connections  • Quality Scores      │
│ • BigQuery Jobs       • Pipeline Health  • Custom Metrics     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Alert Policies                               │
├─────────────────────────────────────────────────────────────────┤
│ 🚨 Error Rate > 5%           📧 Email Notifications            │
│ ⏱️ Latency > 5 minutes       📱 SMS (configurable)            │
│ 🔌 SQL Connections > 80      📞 PagerDuty (enterprise)        │
│ 📅 Data Age > 4 hours        💬 Slack (configurable)          │
│ ❌ BigQuery Failures > 10%   📋 Incident Management           │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Metrics Collected

### 1. Function Performance Metrics
- **Execution Rate**: Functions per second
- **Error Rate**: Failed executions percentage
- **Latency**: P95 execution duration
- **Memory Usage**: Function memory consumption
- **Invocation Count**: Total function calls

### 2. Data Pipeline Metrics
- **Data Freshness**: Hours since latest BigQuery data
- **Data Quality Score**: Completeness percentage (0-100%)
- **Pipeline Health**: Recent success rate percentage
- **Sync Lag**: Delay between Cloud SQL and BigQuery
- **Record Volume**: Daily data processing counts

### 3. Infrastructure Metrics
- **Cloud SQL Connections**: Active database connections
- **BigQuery Jobs**: In-flight and failed job counts
- **Storage Usage**: Database and data warehouse size
- **Network Latency**: Connection response times

### 4. Custom Quality Metrics
- **Missing Speech Rate**: Records without voice features
- **Missing Text Embeddings**: Records without NLP features
- **Missing Labels**: Records without ML target labels
- **Low Confidence Labels**: Predictions below 50% confidence
- **Missing Audio URIs**: Records without audio files

## 🚨 Alert Policies

### Critical Alerts (Immediate Response)
1. **ETL Function High Error Rate** (>5%)
   - **Threshold**: 5% error rate over 5 minutes
   - **Action**: Check function logs, investigate root cause
   - **Auto-close**: 30 minutes

2. **Data Freshness Alert** (>4 hours)
   - **Threshold**: BigQuery data older than 4 hours
   - **Action**: Check batch ETL function and Cloud Scheduler
   - **Auto-close**: When data updates

3. **BigQuery Job Failures** (>10%)
   - **Threshold**: 10% BigQuery job failure rate
   - **Action**: Check BigQuery logs and data validation
   - **Auto-close**: When jobs succeed

### Warning Alerts (Monitor & Plan)
4. **ETL Function High Latency** (>5 minutes)
   - **Threshold**: P95 execution time over 5 minutes
   - **Action**: Check performance bottlenecks
   - **Auto-close**: When latency normalizes

5. **Cloud SQL High Connection Count** (>80)
   - **Threshold**: More than 80 active connections
   - **Action**: Check for connection leaks in functions
   - **Auto-close**: When connections drop below 70

## 🔧 Setup Instructions

### 1. Run Automated Setup
```bash
cd setup/scripts
11-setup-monitoring.bat
```

### 2. Manual Configuration (if needed)

#### Enable APIs
```bash
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
```

#### Create Dashboard
```bash
gcloud monitoring dashboards create --config-from-file=backend/monitoring/etl-dashboard.json
```

#### Deploy Metrics Function
```bash
cd backend/functions/monitoring
gcloud functions deploy collect-etl-metrics --runtime=python311 --trigger-http
```

### 3. Verification Steps

#### Test Metrics Collection
```bash
curl https://asia-northeast3-senior-mhealth-472007.cloudfunctions.net/collect-etl-metrics
```

#### Check Dashboard
Visit: https://console.cloud.google.com/monitoring/dashboards

#### Verify Alerts
Visit: https://console.cloud.google.com/monitoring/alerting

## 📊 Dashboard Widgets

### Row 1: Function Performance
- **ETL Function Executions**: Line chart showing execution rate
- **ETL Function Error Rate**: Stacked bar chart showing error types

### Row 2: Infrastructure Health
- **ETL Function Execution Duration**: P95 latency trends
- **Cloud SQL Connection Pool**: Active connection counts

### Row 3: Data Pipeline Status
- **BigQuery Job Status**: Job types and status
- **Data Freshness**: Hours since last data update (scorecard)

### Row 4: Pipeline Overview
- **ETL Pipeline Health Status**: Markdown text with status indicators

## 🔔 Notification Channels

### Email Notifications (Default)
- **Primary**: admin@senior-mhealth.com
- **Format**: Alert summary with links to dashboard
- **Frequency**: Immediate on trigger, daily digest

### Additional Channels (Configurable)
- **Slack**: #etl-alerts channel
- **SMS**: Critical alerts only
- **PagerDuty**: Production incidents
- **Webhook**: Custom integrations

## 🧪 Testing & Validation

### Alert Testing
```bash
# Simulate high error rate
gcloud functions call firestore-to-sql-sync --data '{"test":true,"fail":true}'

# Simulate high latency
gcloud functions call sql-to-bigquery-sync --data '{"test":true,"delay":600}'
```

### Metrics Validation
```bash
# Check custom metrics
gcloud monitoring metrics list --filter="metric.type:custom.googleapis.com/etl/*"

# Test metrics collection
curl -X POST "https://asia-northeast3-senior-mhealth-472007.cloudfunctions.net/collect-etl-metrics"
```

### Dashboard Verification
1. Navigate to Cloud Monitoring Console
2. Verify all widgets display data
3. Check time range selections work
4. Test drill-down capabilities

## 🚨 Incident Response

### High Priority Incidents
1. **ETL Function Failures**
   - Check Cloud Function logs
   - Verify database connectivity
   - Review recent deployments
   - Manual data sync if needed

2. **Data Freshness Issues**
   - Check Cloud Scheduler status
   - Verify batch ETL function logs
   - Review BigQuery job status
   - Check data pipeline integrity

3. **Database Connection Issues**
   - Monitor SQL connection pool
   - Check VPC connector health
   - Review function concurrency
   - Scale database if needed

### Escalation Procedures
1. **Level 1**: Automated monitoring and self-healing
2. **Level 2**: On-call engineer notification (15 minutes)
3. **Level 3**: Team lead escalation (30 minutes)
4. **Level 4**: Management notification (60 minutes)

## 📝 Maintenance Tasks

### Daily
- Review dashboard for anomalies
- Check alert firing patterns
- Validate data freshness

### Weekly
- Analyze error rate trends
- Review performance metrics
- Update alert thresholds if needed

### Monthly
- Dashboard optimization
- Alert policy refinement
- Metrics cleanup and archival

## 📈 Performance Optimization

### Dashboard Optimization
- Use appropriate time ranges
- Limit concurrent widgets
- Optimize query complexity
- Cache frequently accessed data

### Alert Optimization
- Fine-tune thresholds based on historical data
- Reduce alert noise with proper filtering
- Group related alerts to prevent flooding
- Implement alert suppression during maintenance

### Metrics Optimization
- Reduce metrics collection frequency if needed
- Archive old metrics data
- Optimize custom metrics queries
- Use metric filters effectively

## 🔗 Related Documentation

- [ETL Pipeline Architecture](../pipeline/README.md)
- [Cloud SQL Setup](../database/README.md)
- [BigQuery ML Dataset](../bigquery/README.md)
- [Deployment Guide](../../setup/README.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)