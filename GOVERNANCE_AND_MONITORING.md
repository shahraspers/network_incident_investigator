# Governance & Monitoring Layer

**Network Incident Investigator** now includes enterprise-grade governance, monitoring, and observability capabilities.

---

## Overview

The platform implements **5 key capability areas**:

1. **Centralized Logging** - Structured, queryable, audit-compliant logs
2. **Evaluation Layer** - Quality metrics for anomaly detection and LLM reliability
3. **Observability** - Real-time metrics on performance, latency, and costs
4. **Governance** - RBAC, audit trails, and PII protection
5. **Health Monitoring** - Service health checks and failover management

---

## 1. Centralized Logging

### Architecture

All logs are structured as JSON with:
- `timestamp`: UTC ISO format
- `trace_id`: Request tracing ID for end-to-end visibility
- `module`: Component generating the log (e.g., `anomaly_detector`)
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `custom fields`: metric, site_id, latency_ms, etc.

### Usage

```python
from services.logging import get_logger, PerformanceTimer

logger = get_logger("my_service")

# Log with context
logger.info(
    "Data loaded successfully",
    module="data_loader",
    trace_id="abc123",
    site_id="CELL_001",
    row_count=1000,
    latency_ms=45.2
)

# Measure operation latency automatically
with PerformanceTimer(logger, "anomaly_detection", "detector", trace_id) as timer:
    # Your operation here
    result = detect_anomalies(data)
    # Automatically logs success/failure with latency
```

### Log Destinations

- **File**: `logs/app.log` (JSON Lines format)
- **Console**: Readable JSON output
- **Enterprise**: Can be extended to:
  - ELK Stack (Elasticsearch/Logstash/Kibana)
  - OpenSearch
  - GCP Cloud Logging
  - Azure Monitor

### Example Log Entry

```json
{
  "timestamp": "2026-06-21T10:30:45.123Z",
  "trace_id": "abc12345",
  "module": "anomaly_detector",
  "level": "INFO",
  "message": "Detection completed",
  "site_id": "CELL_001",
  "metric": "rsrp",
  "anomaly_score": 3.2,
  "is_anomaly": true,
  "latency_ms": 12.4
}
```

---

## 2. Evaluation Layer

### Anomaly Detection Quality

Track anomaly detector performance against labeled data:

```python
from services.evaluation import AnomalyQualityEvaluator
import numpy as np

evaluator = AnomalyQualityEvaluator()

# Evaluate against ground truth
y_true = np.array([0, 0, 1, 0, 1, 1, 0, 0])
y_pred = np.array([0, 0, 1, 0, 0, 1, 0, 0])  # Our predictions

metrics = evaluator.evaluate(y_true, y_pred)
print(f"Precision: {metrics.precision:.2%}")  # 100%
print(f"Recall: {metrics.recall:.2%}")        # 66%
print(f"F1 Score: {metrics.f1_score:.2%}")    # 80%
```

**Metrics Tracked:**
- `true_positives`, `false_positives`, `false_negatives`, `true_negatives`
- `precision`, `recall`, `f1_score`, `specificity`, `accuracy`
- Historical tracking for trend analysis
- False positive analysis (identify patterns in misclassifications)

### LLM Quality Evaluation

Track LLM reliability, hallucinations, and consistency:

```python
from services.evaluation import LLMQualityEvaluator

llm_evaluator = LLMQualityEvaluator()

# Track each explanation
llm_evaluator.track_explanation(
    explanation_id="exp_001",
    provider="ollama_local",
    model="llama2",
    response_time_ms=250,
    token_count=450,
    explanation_data={
        "summary": "...",
        "likely_causes": [...],
        "confidence": 0.85
    }
)

# Detect hallucinations
analysis = llm_evaluator.detect_hallucinations(
    explanation_data=explanation_data,
    context_data=context_data
)

print(f"Hallucination detected: {analysis.hallucination_detected}")
print(f"Severity: {analysis.severity}")  # low, medium, high
print(f"Recommendation: {analysis.recommendation}")
```

**LLM Quality Metrics:**
- Hallucination detection (conflicting statements, unverifiable claims)
- Response time per provider
- Token usage and cost tracking
- Consistency across multiple runs
- Provider performance comparison

### Drift Detection

Monitor KPI distributions and anomaly frequency changes:

```python
from services.evaluation import DriftDetector
import numpy as np

detector = DriftDetector(baseline_df=historical_data)

# Detect KPI distribution drift
baseline = np.array([85, 87, 86, 88, 85, 86, 87])
current = np.array([80, 82, 78, 81, 79, 80, 81])

drift = detector.detect_kpi_drift(
    metric_name="rsrp",
    current_values=current,
    site_id="CELL_001",
    baseline_values=baseline
)

print(f"PSI Score: {drift.psi_score:.4f}")  # < 0.1 = no drift
print(f"Drift severity: {drift.severity}")   # no_drift, minor, moderate, severe
```

**Drift Metrics:**
- **PSI (Population Stability Index)**: Measures distribution shift
- **Severity Levels**: no_drift (<0.1), minor (0.1-0.25), moderate (0.25-0.5), severe (>0.5)
- **Anomaly Frequency Drift**: Detects increasing/decreasing anomaly rates
- **Triggering Signal**: If drift detected, may indicate need for detector retraining

---

## 3. Observability Metrics

### Real-Time Platform Metrics

Access comprehensive platform metrics via API:

```bash
# Get overall platform metrics
curl http://localhost:8000/api/metrics

# Get specific metrics
curl http://localhost:8000/api/metrics/latency?module=anomaly_detector
curl http://localhost:8000/api/metrics/tokens?minutes=60
curl http://localhost:8000/api/metrics/errors?minutes=60
```

### Metrics Tracked

#### Latency Metrics
- API endpoint response times
- Anomaly detection latency per module
- LLM provider response times
- Percentiles: p50, p95, p99

```json
{
  "count": 245,
  "avg_ms": 42.3,
  "median_ms": 38.5,
  "p95_ms": 89.2,
  "p99_ms": 156.8,
  "min_ms": 2.1,
  "max_ms": 312.4,
  "success_rate": 0.9918
}
```

#### Token Usage & Costs
- Tokens per provider per hour
- Estimated costs by provider
- Cost per detection run
- Cost trends over time

```json
{
  "total_tokens": 125480,
  "total_cost_usd": 3.27,
  "calls": 487,
  "avg_tokens_per_call": 258,
  "by_provider": {
    "openai": {"tokens": 75000, "cost_usd": 2.50, "calls": 250},
    "ollama_local": {"tokens": 50480, "cost_usd": 0.00, "calls": 237}
  }
}
```

#### Anomaly Detection Stats
- Anomalies detected per hour
- Detection frequency trends
- Sites with repeated anomalies
- Average anomalies per detection run

```json
{
  "total_detections": 120,
  "anomalies_detected": 480,
  "avg_per_detection": 4.0,
  "anomalies_per_hour": 2.5
}
```

#### Error Statistics
- Error rate (errors / total requests)
- Error types distribution
- Recent errors for debugging
- Service-specific error rates

```json
{
  "total_errors": 12,
  "error_rate": 0.0246,
  "by_type": {
    "TimeoutError": 7,
    "DataValidationError": 3,
    "LLMProviderError": 2
  },
  "recent_errors": [...]
}
```

### Grafana Dashboard Integration

(Optional) To integrate with Grafana:

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'nii-platform'
    static_configs:
      - targets: ['localhost:8000/metrics']
    interval: 30s
```

---

## 4. Governance: RBAC & Audit

### Role-Based Access Control

Four predefined roles with permissions:

| Role | Permissions | Use Case |
|------|-------------|----------|
| **viewer** | view_metrics | Dashboard viewers, executives |
| **analyst** | view_metrics, run_detection, view_explanations, upload_data | Data scientists, engineers |
| **admin** | All permissions | Platform administrators |
| **api_service** | run_detection, view_explanations | External integrations |

### Managing Users

```python
from services.governance import get_access_controller, Role, Permission

ac = get_access_controller()

# Create users
analyst = ac.create_user("alice@example.com", Role.ANALYST)
admin = ac.create_user("bob@example.com", Role.ADMIN)

# Check permissions
if ac.check_permission("alice@example.com", Permission.RUN_DETECTION):
    # Alice can run detection
    pass
```

### API Key Management

For service-to-service authentication:

```python
# Create API key
plaintext_key, api_key = ac.create_api_key(
    service_name="data_pipeline",
    role=Role.API_SERVICE
)
# Save plaintext_key securely (e.g., secrets manager)
# Server stores only api_key (hashed)

# Verify API key
api_key_obj = ac.verify_api_key(plaintext_key)
if api_key_obj:
    print(f"Service: {api_key_obj.service_name}")
```

### Audit Logging

All sensitive actions are logged immutably:

```python
from services.governance import get_audit_logger, AuditAction

audit = get_audit_logger()

# Logs are automatically created for:
# - Data uploads
# - Anomaly detection runs
# - LLM explanations
# - User/role changes
# - Unauthorized access attempts

# Query audit trail
logs = audit.get_audit_trail(
    actor="alice@example.com",
    action="run_anomaly_detection",
    limit=50
)

# Get user's actions
user_actions = audit.get_user_actions("alice@example.com")

# Get access history for a resource
resource_history = audit.get_resource_access_history(
    resource_type="anomaly_detection",
    resource_id="CELL_001"
)
```

**Audit Log Structure:**

```json
{
  "audit_id": "audit_20260621_000001",
  "timestamp": "2026-06-21T10:30:45.123Z",
  "actor": "alice@example.com",
  "action": "run_anomaly_detection",
  "resource_type": "anomaly_detection",
  "resource_id": "CELL_001",
  "status": "success",
  "details": {
    "metrics_count": 6,
    "anomalies_detected": 12
  },
  "ip_address": "192.168.1.100"
}
```

### PII Scrubbing

Automatically mask sensitive data in logs:

```python
from services.governance import PIIScrubber

# Scrub individual text
masked = PIIScrubber.scrub_text("Contact: john@example.com (555-123-4567)")
# Output: "Contact: j***@example.com (555-***-****)"

# Scrub dictionaries
data = {
    "user": "alice@example.com",
    "api_key": "sk_live_abcd1234efgh5678",
    "credit_card": "4532-1234-5678-9010"
}
scrubbed = PIIScrubber.scrub_dict(data)
```

**PII Patterns Detected & Masked:**
- Emails
- Phone numbers
- Credit cards
- SSNs
- IP addresses
- API keys
- Passwords

---

## 5. Health Monitoring & Failover

### Service Health Checks

```bash
# Get comprehensive health status
curl http://localhost:8000/api/health

# Response example:
{
  "overall_status": "healthy",
  "timestamp": "2026-06-21T10:30:45.123Z",
  "services": {
    "anomaly_detector": {
      "status": "healthy",
      "last_check": "2026-06-21T10:30:45.123Z",
      "response_time_ms": 1.2
    },
    "llm_provider": {
      "status": "healthy",
      "last_check": "2026-06-21T10:30:45.123Z",
      "response_time_ms": 45.3
    },
    "data_source": {
      "status": "healthy"
    },
    "api_layer": {
      "status": "healthy",
      "response_time_ms": 0.8
    }
  }
}
```

### Failover Management

Automatic provider fallback when primary LLM provider fails:

```python
from services.monitoring import get_failover_manager

fm = get_failover_manager()

# Preferred provider chain (in order):
# 1. ollama_local (fastest, free)
# 2. openai (reliable, cloud)
# 3. azure_openai (enterprise)
# 4. vertex_ai (GCP)

# Get best available provider
provider = fm.get_best_available_provider("openai")
# If OpenAI is down, automatically uses next available

# Mark provider as unavailable (e.g., on timeout)
fm.mark_provider_down("openai")

# Check provider status
status = fm.get_provider_status()
# {"ollama_local": True, "openai": False, ...}
```

### Meta-Monitoring

Monitor the platform itself:

```python
from services.monitoring import get_health_monitor

hm = get_health_monitor()

# Run comprehensive health check
status = hm.check_all_services()

# Check individual services
health = hm.check_anomaly_detector()
health = hm.check_llm_provider()
health = hm.check_data_source()
health = hm.check_api_layer()
```

---

## Configuration Files

### `governance/access_policies.yaml`

Defines role permissions, API rate limits, and access rules:

```yaml
roles:
  analyst:
    permissions:
      - view_metrics
      - run_detection
    capabilities:
      - upload_data
      - request_llm_explanations

policies:
  detection_execution:
    cooldown_seconds: 30
    max_sites_per_run: 100

rate_limiting:
  requests_per_minute:
    analyst: 300
    admin: 1000
```

### `governance/audit_rules.yaml`

Defines what events to audit and retention policies:

```yaml
audit_events:
  run_anomaly_detection:
    enabled: true
    log_details:
      - metrics
      - detection_method
      - anomalies_detected
    retention_days: 365

alerts:
  unauthorized_access_attempts:
    severity: "critical"
    action: "alert_admin"
```

---

## API Endpoints

### Health & Monitoring

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Basic health check |
| `/api/health` | GET | Detailed service health |
| `/api/metrics` | GET | Overall platform metrics |
| `/api/metrics/latency` | GET | Latency metrics (filterable) |
| `/api/metrics/tokens` | GET | Token usage & costs |
| `/api/metrics/errors` | GET | Error statistics |

### Governance

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/governance/users` | GET | List all users (admin only) |
| `/api/governance/audit-logs` | GET | Query audit trail (admin only) |

### Headers

| Header | Example | Purpose |
|--------|---------|---------|
| `X-User` | `alice@example.com` | User identity for audit |
| `X-Trace-ID` | `req_abc123def456` | Request tracing ID |

---

## Best Practices

### 1. Always Use Trace IDs

```python
import uuid
trace_id = str(uuid.uuid4())[:8]

# Pass to API calls
headers = {"X-Trace-ID": trace_id}
response = requests.post("/api/anomaly/detect", headers=headers)
```

### 2. Monitor Drift Regularly

```python
# Weekly drift check
detector = DriftDetector(baseline_df=weekly_baseline)
drift = detector.detect_kpi_drift("rsrp", current_week_data)

if drift.drift_detected and drift.severity == "severe":
    # Alert team - may need detector recalibration
    send_alert(f"Severe drift detected in RSRP: PSI={drift.psi_score}")
```

### 3. Review Audit Logs

```python
# Daily: Check for unauthorized access
logs = audit.get_audit_trail(
    action="unauthorized_access",
    limit=1000
)
if logs:
    alert_security_team(logs)
```

### 4. Monitor LLM Hallucinations

```python
# After each explanation
llm_evaluator.detect_hallucinations(explanation, context)

# Weekly: Review hallucination rate
metrics = llm_evaluator.get_metrics()
if metrics['hallucination_rate'] > 0.05:
    # >5% hallucination rate - investigate provider
    investigate_provider(metrics)
```

### 5. Track Costs

```python
# Monthly cost report
tokens = metrics_collector.get_token_usage_stats(minutes=43200)  # 30 days
total_cost = tokens['total_cost_usd']
print(f"Monthly LLM cost: ${total_cost:.2f}")
```

---

## Compliance & Security

### Data Retention

- **Audit logs**: 365+ days (compliance requirement)
- **Error logs**: 180 days
- **Performance metrics**: 90 days
- **PII**: Automatically scrubbed

### Compliance Standards

- **GDPR**: PII scrubbing, right to audit
- **SOC 2**: Immutable audit trail
- **ISO 27001**: Access control, encryption-ready
- **HIPAA**: If KPI data contains protected health info (implement additional scrubbing)

### Security Features

- API key hashing (SHA256)
- Secure random key generation
- Audit trail immutability
- Role-based access control
- PII automatic masking
- Request tracing for forensics

---

## Troubleshooting

### High Latency

```python
# Query latency metrics
latency = metrics_collector.get_latency_stats(
    module="anomaly_detector",
    minutes=60
)

if latency['p99_ms'] > 1000:
    print("95th percentile latency > 1s - investigate")
    # Check detailed logs with trace IDs for slow requests
```

### LLM Provider Failures

```python
# Check provider status
status = health_monitor.check_all_services()
if status['services']['llm_provider']['status'] != 'healthy':
    # Provider down - automatic failover active
    fm.mark_provider_down("openai")
```

### Data Drift

```python
# If anomaly rate suddenly spikes
frequency_drift = detector.detect_anomaly_frequency_drift(...)
if frequency_drift.drift_detected:
    # May indicate:
    # 1. Real network issues (investigate)
    # 2. Detector threshold too low (recalibrate)
    # 3. Data quality issue (check data source)
```

---

## Next Steps

1. **Enable Logging**: Start capturing structured logs
2. **Set Up Audit Trail**: Monitor user actions and data access
3. **Monitor Drift**: Weekly checks for data distribution changes
4. **Track Costs**: Review monthly LLM token usage and costs
5. **Implement Alerting**: Set up alerts for critical health events
6. **Integrate Monitoring**: Connect to Grafana/ELK for visualization

---

## References

- **Logging**: `services/logging/structured_logger.py`
- **Evaluation**: `services/evaluation/`
- **Observability**: `services/observability/metrics_collector.py`
- **Governance**: `services/governance/`
- **Monitoring**: `services/monitoring/health_monitor.py`
- **Config**: `governance/access_policies.yaml`, `governance/audit_rules.yaml`
