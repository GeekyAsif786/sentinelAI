#!/bin/bash
# SentinelAI Staging Log Collection Script
# Aggregates logs from all services for monitoring and debugging
# Usage: ./log_collection.sh [output_file]

set -e

OUTPUT_FILE="${1:-staging_logs_$(date +%Y%m%d_%H%M%S).txt}"

echo "=== SentinelAI Staging Log Collection ===" > "$OUTPUT_FILE"
echo "Collected at: $(date)" >> "$OUTPUT_FILE"
echo "Hostname: $(hostname)" >> "$OUTPUT_FILE"
echo "User: $(whoami)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Flask Application Logs
# ============================================================================
echo "=== Flask Application Logs ===" >> "$OUTPUT_FILE"
if [ -f /tmp/flask_server.log ]; then
    echo "Last 100 lines of Flask logs:" >> "$OUTPUT_FILE"
    tail -100 /tmp/flask_server.log >> "$OUTPUT_FILE"
else
    echo "Flask log file not found at /tmp/flask_server.log" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Celery Worker Logs
# ============================================================================
echo "=== Celery Worker Logs ===" >> "$OUTPUT_FILE"
if [ -f /tmp/celery_worker.log ]; then
    echo "Last 100 lines of Celery worker logs:" >> "$OUTPUT_FILE"
    tail -100 /tmp/celery_worker.log >> "$OUTPUT_FILE"
else
    echo "Celery log file not found at /tmp/celery_worker.log" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Redis Logs
# ============================================================================
echo "=== Redis Logs ===" >> "$OUTPUT_FILE"
if [ -f /tmp/redis.log ]; then
    echo "Last 50 lines of Redis logs:" >> "$OUTPUT_FILE"
    tail -50 /tmp/redis.log >> "$OUTPUT_FILE"
else
    echo "Redis log file not found at /tmp/redis.log" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# PostgreSQL Status
# ============================================================================
echo "=== PostgreSQL Connection Status ===" >> "$OUTPUT_FILE"
if command -v psql &> /dev/null; then
    echo "Active connections:" >> "$OUTPUT_FILE"
    psql -t -c "SELECT datname, usename, application_name, state, count(*) FROM pg_stat_activity WHERE datname IS NOT NULL GROUP BY datname, usename, application_name, state;" 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not connect to PostgreSQL" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Top tables by size:" >> "$OUTPUT_FILE"
    psql -t -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname NOT IN ('information_schema', 'pg_catalog') ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 10;" 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not query PostgreSQL" >> "$OUTPUT_FILE"
else
    echo "psql command not found" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Redis Status
# ============================================================================
echo "=== Redis Status ===" >> "$OUTPUT_FILE"
if command -v redis-cli &> /dev/null; then
    echo "Redis INFO:" >> "$OUTPUT_FILE"
    redis-cli INFO stats 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not connect to Redis" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Redis memory usage:" >> "$OUTPUT_FILE"
    redis-cli INFO memory 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not connect to Redis" >> "$OUTPUT_FILE"
else
    echo "redis-cli command not found" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Celery Task Queue Status
# ============================================================================
echo "=== Celery Task Queue Status ===" >> "$OUTPUT_FILE"
if command -v celery &> /dev/null; then
    echo "Active tasks:" >> "$OUTPUT_FILE"
    celery -A app.worker inspect active 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not connect to Celery" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Registered tasks:" >> "$OUTPUT_FILE"
    celery -A app.worker inspect registered 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not connect to Celery" >> "$OUTPUT_FILE"
else
    echo "celery command not found" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# System Resource Usage
# ============================================================================
echo "=== System Resource Usage ===" >> "$OUTPUT_FILE"
echo "Memory usage:" >> "$OUTPUT_FILE"
free -h >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Disk usage:" >> "$OUTPUT_FILE"
df -h >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Top processes by memory:" >> "$OUTPUT_FILE"
ps aux --sort=-%mem | head -20 >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "Top processes by CPU:" >> "$OUTPUT_FILE"
ps aux --sort=-%cpu | head -20 >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Network Connections
# ============================================================================
echo "=== Network Connections ===" >> "$OUTPUT_FILE"
echo "Listening ports:" >> "$OUTPUT_FILE"
netstat -tlnp 2>/dev/null | grep LISTEN >> "$OUTPUT_FILE" || ss -tlnp 2>/dev/null | grep LISTEN >> "$OUTPUT_FILE" || echo "Could not determine listening ports" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Application Metrics
# ============================================================================
echo "=== Application Health Checks ===" >> "$OUTPUT_FILE"
if command -v curl &> /dev/null; then
    echo "Flask API health check:" >> "$OUTPUT_FILE"
    curl -s http://localhost:5000/health 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not reach Flask API" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Prometheus metrics endpoint:" >> "$OUTPUT_FILE"
    curl -s http://localhost:5000/metrics 2>/dev/null | head -50 >> "$OUTPUT_FILE" || echo "Could not reach Prometheus metrics" >> "$OUTPUT_FILE"
else
    echo "curl command not found" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

# ============================================================================
# Recent Errors in Database
# ============================================================================
echo "=== Recent Database Errors ===" >> "$OUTPUT_FILE"
if command -v psql &> /dev/null; then
    echo "Scans with errors (last 24 hours):" >> "$OUTPUT_FILE"
    psql -t -c "SELECT COUNT(*), error_code FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code;" 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not query error logs" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    echo "Recent failed scans (last 10):" >> "$OUTPUT_FILE"
    psql -t -c "SELECT id, status, error_code, error_message, created_at FROM scan_runs WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;" 2>/dev/null >> "$OUTPUT_FILE" || echo "Could not query failed scans" >> "$OUTPUT_FILE"
else
    echo "psql command not found" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

echo "=== End of Log Collection ===" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "✓ Logs aggregated successfully to: $OUTPUT_FILE"
echo "  Size: $(du -h "$OUTPUT_FILE" | cut -f1)"
