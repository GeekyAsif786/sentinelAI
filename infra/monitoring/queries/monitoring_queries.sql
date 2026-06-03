-- SentinelAI Staging Monitoring SQL Queries
-- Use these queries to monitor system health and performance

-- ============================================================================
-- 1. Scan Execution Status (Last 24 Hours)
-- ============================================================================
-- Shows scan completion rate, average duration, and status breakdown
SELECT 
  status, 
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec,
  MIN(created_at) as first_at,
  MAX(created_at) as last_at
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY count DESC;


-- ============================================================================
-- 2. Error Analysis (Last 24 Hours)
-- ============================================================================
-- Identifies error patterns and failure modes
SELECT 
  error_code, 
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours'), 2) as error_percentage,
  STRING_AGG(DISTINCT error_message, '; ' ORDER BY error_message LIMIT 3) as sample_errors,
  MAX(created_at) as last_occurrence
FROM scan_runs
WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY error_code
ORDER BY count DESC;


-- ============================================================================
-- 3. Graph Projection Job Status (Last 24 Hours)
-- ============================================================================
-- Tracks Neo4j graph projection job performance
SELECT 
  status, 
  COUNT(*) as count,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec,
  MIN(created_at) as first_at,
  MAX(created_at) as last_at
FROM graph_projection_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY status;


-- ============================================================================
-- 4. Scan Execution Rate (Hourly Breakdown)
-- ============================================================================
-- Shows scan throughput by hour
SELECT 
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as scans_completed,
  SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
  ROUND(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;


-- ============================================================================
-- 5. Host and Service Counts by Scan
-- ============================================================================
-- Inventory metrics for each scan execution
SELECT 
  sr.id as scan_run_id,
  sr.status,
  COUNT(DISTINCT h.id) as host_count,
  COUNT(DISTINCT s.id) as service_count,
  COALESCE(COUNT(DISTINCT v.id), 0) as vulnerability_count,
  EXTRACT(EPOCH FROM (sr.completed_at - sr.started_at))::integer as duration_seconds,
  sr.completed_at
FROM scan_runs sr
LEFT JOIN hosts h ON h.scan_run_id = sr.id
LEFT JOIN services s ON s.host_id = h.id
LEFT JOIN findings f ON f.scan_run_id = sr.id
LEFT JOIN vulnerabilities v ON v.id = f.vulnerability_id
WHERE sr.created_at > NOW() - INTERVAL '24 hours'
GROUP BY sr.id, sr.status, sr.completed_at
ORDER BY sr.created_at DESC
LIMIT 50;


-- ============================================================================
-- 6. Worker Performance (Last 24 Hours)
-- ============================================================================
-- Analyzes per-worker scan execution and error rates
SELECT 
  COALESCE(worker_node_id, 'unassigned') as worker_node_id,
  COUNT(*) as scans_executed,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec,
  COUNT(CASE WHEN status = 'failed' THEN 1 END)::float / COUNT(*) * 100 as error_rate_pct,
  MIN(created_at) as first_at,
  MAX(created_at) as last_at
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY worker_node_id
ORDER BY scans_executed DESC;


-- ============================================================================
-- 7. Database Connection Pool Status
-- ============================================================================
-- Real-time database activity and connection usage
SELECT 
  datname as database,
  usename as user,
  application_name,
  state,
  COUNT(*) as connection_count,
  MAX(EXTRACT(EPOCH FROM (NOW() - state_change))) as idle_seconds
FROM pg_stat_activity
WHERE datname IS NOT NULL
GROUP BY datname, usename, application_name, state
ORDER BY connection_count DESC;


-- ============================================================================
-- 8. Slow Queries (Last 24 Hours)
-- ============================================================================
-- Identifies performance bottlenecks
SELECT 
  query,
  calls,
  ROUND(total_time::numeric, 2) as total_time_ms,
  ROUND(mean_time::numeric, 2) as avg_time_ms,
  ROUND(max_time::numeric, 2) as max_time_ms,
  ROUND(stddev_time::numeric, 2) as stddev_time_ms
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY mean_time DESC
LIMIT 20;


-- ============================================================================
-- 9. Findings and Vulnerabilities Discovered (Last 24 Hours)
-- ============================================================================
-- Summarizes discovered security issues
SELECT 
  v.severity,
  COUNT(DISTINCT f.id) as finding_count,
  COUNT(DISTINCT sr.id) as affected_scans,
  COUNT(DISTINCT h.id) as affected_hosts
FROM findings f
LEFT JOIN vulnerabilities v ON v.id = f.vulnerability_id
LEFT JOIN scan_runs sr ON sr.id = f.scan_run_id
LEFT JOIN hosts h ON h.id = f.host_id
WHERE sr.created_at > NOW() - INTERVAL '24 hours'
GROUP BY v.severity
ORDER BY CASE 
  WHEN v.severity = 'critical' THEN 1
  WHEN v.severity = 'high' THEN 2
  WHEN v.severity = 'medium' THEN 3
  WHEN v.severity = 'low' THEN 4
  ELSE 5 END;


-- ============================================================================
-- 10. Recent Scan Details (Last 10 Scans)
-- ============================================================================
-- Latest scan execution details for operational overview
SELECT 
  sr.id,
  sr.status,
  sr.created_at,
  sr.started_at,
  sr.completed_at,
  EXTRACT(EPOCH FROM (sr.completed_at - sr.started_at))::integer as duration_seconds,
  sr.error_code,
  sr.error_message,
  (SELECT COUNT(*) FROM hosts WHERE scan_run_id = sr.id) as hosts_discovered,
  (SELECT COUNT(*) FROM findings WHERE scan_run_id = sr.id) as findings_count
FROM scan_runs sr
ORDER BY sr.created_at DESC
LIMIT 10;


-- ============================================================================
-- 11. Attack Path Generation Status (Last 24 Hours)
-- ============================================================================
-- Tracks attack path computation performance
SELECT 
  sr.id as scan_run_id,
  COUNT(DISTINCT ap.id) as attack_path_count,
  AVG(array_length(ap.path, 1)) as avg_path_length,
  MAX(array_length(ap.path, 1)) as max_path_length,
  MAX(ap.risk_score) as highest_risk_score
FROM scan_runs sr
LEFT JOIN attack_paths ap ON ap.scan_run_id = sr.id
WHERE sr.created_at > NOW() - INTERVAL '24 hours'
GROUP BY sr.id
ORDER BY sr.created_at DESC
LIMIT 20;


-- ============================================================================
-- 12. Health Check: System State Summary
-- ============================================================================
-- Quick system health overview
SELECT 
  'Last Scan' as metric,
  COALESCE(MAX(sr.created_at)::text, 'No scans') as value
FROM scan_runs sr
UNION ALL
SELECT 
  'Active Workers',
  COUNT(*)::text
FROM scan_runs sr
WHERE sr.status = 'in_progress'
UNION ALL
SELECT 
  'Failed Last Hour',
  COUNT(*)::text
FROM scan_runs sr
WHERE sr.status = 'failed' AND sr.created_at > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
  'Success Rate (24h)',
  ROUND(SUM(CASE WHEN sr.status = 'success' THEN 1 ELSE 0 END) * 100.0 / 
    NULLIF(COUNT(*), 0), 2)::text || '%'
FROM scan_runs sr
WHERE sr.created_at > NOW() - INTERVAL '24 hours';
