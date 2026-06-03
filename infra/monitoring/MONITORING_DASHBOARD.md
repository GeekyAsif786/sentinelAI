# SentinelAI Staging Monitoring Dashboard

## Overview
Comprehensive monitoring infrastructure for Phase 2-4 SentinelAI deployment tracking scan execution, error rates, performance, and system health.

## Key Metrics to Track

### Scan Execution Metrics
- **Scan Execution Success Rate**: Percentage of scans completing without errors
- **Average Scan Execution Time**: Mean duration from start to completion
- **Scan Status Distribution**: Breakdown by success, failure, pending, in-progress
- **Error Rate by Error Code**: Categorized failure reasons
- **Scans per Worker**: Distribution of workload across Celery workers

### System Performance Metrics
- **Celery Task Queue Depth**: Number of pending tasks in Redis
- **Worker Utilization**: Active vs. idle workers
- **Task Processing Rate**: Tasks completed per minute
- **Task Processing Duration**: P50, P95, P99 latencies

### Infrastructure Metrics
- **Database Connection Pool Usage**: Active vs. available connections
- **Database Query Performance**: Slow query identification
- **Redis Memory Usage**: Memory consumption and eviction events
- **API Response Time**: HTTP response latencies
- **Neo4j Connection Health**: Graph database connectivity

### Graph Processing Metrics
- **Graph Projection Job Status**: Completed, failed, in-progress counts
- **Graph Projection Duration**: Average time to complete projections
- **Graph Projection Failure Rate**: Error rate for graph operations
- **Network Latency to Neo4j**: Round-trip time to graph database

### Application Health
- **Flask API Uptime**: Service availability
- **Celery Worker Count**: Active worker nodes
- **Error Logs Count**: Application errors per hour
- **Authentication Failures**: Failed login attempts

## Dashboard Configuration

### Prometheus Targets
- Flask Application: `:5000/metrics`
- Celery Workers: Celery events via Redis
- PostgreSQL: Via postgres_exporter
- Redis: Via redis_exporter
- Neo4j: Via neo4j_exporter (if available)

### Alert Thresholds
| Alert | Threshold | Duration | Action |
|-------|-----------|----------|--------|
| High Error Rate | > 10% | 5 minutes | Immediate notification |
| Worker Disconnected | Status = offline | Instant | Critical alert |
| Graph Projection Failure | > 5% | 10 minutes | Warning |
| DB Connection Pool | > 80% usage | 5 minutes | Warning |
| API Latency | > 5 seconds | 2 minutes | Warning |
| Redis Memory | > 90% | 5 minutes | Warning |
| Celery Queue Depth | > 1000 tasks | 5 minutes | Warning |

## Grafana Dashboards

### 1. Scan Execution Overview
- Recent scans status (success/failure/pending)
- Success rate trend (24-hour)
- Average execution time trend
- Error rate by code

### 2. Worker Performance
- Active workers count
- Task processing rate by worker
- Worker CPU and memory usage
- Failed tasks by worker

### 3. System Health
- API response time distribution
- Database connection pool utilization
- Redis memory and command latency
- Neo4j connectivity and query performance

### 4. Error Analysis
- Error rate timeline
- Error distribution by type
- Failed scan details
- Error message patterns

## Real-time Monitoring

### Live Dashboards
1. **Main Overview**: System health, active scans, worker status
2. **Detailed Scan Metrics**: Individual scan performance data
3. **System Performance**: Infrastructure resource utilization
4. **Alerts**: Active and historical alerts
5. **Error Log Viewer**: Real-time error tracking

## Data Retention

- **Prometheus Metrics**: 15 days
- **Grafana Dashboards**: Indefinite (queries stored)
- **PostgreSQL Logs**: 90 days retention
- **Application Logs**: 30 days
- **Alert History**: 60 days

## Access Points

- **Prometheus**: http://localhost:9090 (staging)
- **Grafana**: http://localhost:3000 (staging)
- **Application Logs**: See log collection scripts
- **Database Queries**: Direct SQL queries via monitoring_queries.sql
