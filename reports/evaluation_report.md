# OpsPilot AI — Multi-Agent Evaluation & Benchmark Report

## Executive Summary

- **Total Scenarios Evaluated:** `1`
- **Service Attribution Accuracy:** `100.0%` (1/1)
- **Root Cause Semantic F1 Score:** `0.6` / 1.000
- **Remediation Plan Validity Rate:** `100.0%`
- **Safety Policy & Blast Radius Containment:** `100.0%`
- **Mean Investigation Latency:** `32.38 ms`
- **Average Agent Confidence:** `92.0%`

---

## Detailed Scenario Trial Results

| Scenario ID | Target Service | Predicted Service | Match | RCA Similarity | Remediation Valid | Duration (ms) |
|:---|:---|:---|:---:|:---:|:---:|---:|
| `redis_pool_exhaustion` | `payment-service` | `payment-service` | **PASS** | `0.60` | **PASS** | 32.4 |

---

## Qualitative Root Cause Comparison

### Scenario: `Redis Connection Pool Exhaustion` (redis_pool_exhaustion)
- **Ground Truth Root Cause:** Payment service v2.4.1 deployment accidentally reduced Redis connection pool size from 100 to 10 in configuration, causing thread pool starvation and timeout errors.
- **Agent Predicted RCA:** Redis Connection Pool Exhaustion from Deployment Configuration
- **Confidence Score:** `92.0%` | **Critic Reviewed:** `Yes`
