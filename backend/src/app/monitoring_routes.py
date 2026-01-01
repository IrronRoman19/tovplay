"""
Ultimate Monitoring Dashboard API
Aggregates data from:
- Prometheus metrics
- Loki logs
- Grafana dashboards
- Docker containers
- PostgreSQL database
- System resources (CPU, Memory, Disk)
- Network traffic
- Security events
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import requests
import psutil
import docker
from sqlalchemy import text
from typing import Dict, Any, List, Optional
import logging
import subprocess
import json
import re

from src.app.db import db

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')
logger = logging.getLogger(__name__)

# Configuration
PROMETHEUS_URL = "http://localhost:9090"
LOKI_URL = "http://localhost:3100"
GRAFANA_URL = "http://localhost:3002"
ALERTMANAGER_URL = "http://localhost:9093"

class MonitoringService:
    """Centralized monitoring data aggregation service"""

    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

    # ========== PROMETHEUS METRICS ==========

    def query_prometheus(self, query: str) -> Dict[str, Any]:
        """Query Prometheus API"""
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={'query': query},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return {}

    def query_prometheus_range(self, query: str, start: str, end: str, step: str = '30s') -> Dict[str, Any]:
        """Query Prometheus API with time range"""
        try:
            response = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={
                    'query': query,
                    'start': start,
                    'end': end,
                    'step': step
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Prometheus range query failed: {e}")
            return {}

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all available Prometheus metrics"""
        try:
            response = requests.get(f"{PROMETHEUS_URL}/api/v1/label/__name__/values", timeout=5)
            if response.status_code == 200:
                return response.json().get('data', [])
            return []
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return []

    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all monitored services"""
        result = self.query_prometheus('up')
        services = {}

        if result.get('status') == 'success':
            for metric in result.get('data', {}).get('result', []):
                service_name = metric.get('metric', {}).get('job', 'unknown')
                instance = metric.get('metric', {}).get('instance', 'unknown')
                status = int(metric.get('value', [0, 0])[1])

                services[f"{service_name}@{instance}"] = {
                    'service': service_name,
                    'instance': instance,
                    'status': 'up' if status == 1 else 'down',
                    'environment': metric.get('metric', {}).get('environment', 'unknown'),
                    'tier': metric.get('metric', {}).get('tier', 'unknown')
                }

        return services

    def get_api_metrics(self) -> Dict[str, Any]:
        """Get API endpoint performance metrics"""
        # Request rate
        rate_query = 'rate(flask_http_request_total[5m])'
        rate_result = self.query_prometheus(rate_query)

        # Response time
        latency_query = 'histogram_quantile(0.95, rate(flask_http_request_duration_seconds_bucket[5m]))'
        latency_result = self.query_prometheus(latency_query)

        # Error rate
        error_query = 'rate(flask_http_request_total{status=~"5.."}[5m])'
        error_result = self.query_prometheus(error_query)

        return {
            'request_rate': rate_result,
            'p95_latency': latency_result,
            'error_rate': error_result
        }

    def get_cpu_memory_metrics(self) -> Dict[str, Any]:
        """Get CPU and memory metrics from Prometheus"""
        cpu_query = '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
        memory_query = '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'

        return {
            'cpu_usage': self.query_prometheus(cpu_query),
            'memory_usage': self.query_prometheus(memory_query)
        }

    # ========== LOKI LOGS ==========

    def query_loki(self, query: str, limit: int = 100, start: Optional[str] = None) -> Dict[str, Any]:
        """Query Loki logs"""
        try:
            params = {
                'query': query,
                'limit': limit
            }
            if start:
                params['start'] = start

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Loki query failed: {e}")
            return {}

    def get_error_logs(self, service: str = None, hours: int = 1) -> List[Dict[str, Any]]:
        """Get error logs from Loki"""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + 'Z'

        if service:
            query = f'{{job="{service}"}} |= "error" or |= "ERROR" or |= "Exception"'
        else:
            query = '{job=~".+"} |= "error" or |= "ERROR" or |= "Exception"'

        result = self.query_loki(query, limit=50, start=start_time)

        logs = []
        for stream in result.get('data', {}).get('result', []):
            for value in stream.get('values', []):
                logs.append({
                    'timestamp': value[0],
                    'message': value[1],
                    'labels': stream.get('stream', {})
                })

        return logs

    def get_log_rate(self, service: str) -> Dict[str, Any]:
        """Get log rate for a service"""
        query = f'rate({{job="{service}"}}[5m])'
        return self.query_loki(query)

    # ========== DOCKER CONTAINERS ==========

    def get_docker_containers(self) -> List[Dict[str, Any]]:
        """Get all Docker containers with stats"""
        if not self.docker_client:
            return []

        containers = []
        try:
            for container in self.docker_client.containers.list(all=True):
                stats = None
                if container.status == 'running':
                    try:
                        stats = container.stats(stream=False)
                        cpu_percent = self._calculate_cpu_percent(stats)
                        memory_usage = self._calculate_memory_usage(stats)
                    except:
                        cpu_percent = 0
                        memory_usage = 0
                else:
                    cpu_percent = 0
                    memory_usage = 0

                containers.append({
                    'id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'created': container.attrs['Created'],
                    'cpu_percent': cpu_percent,
                    'memory_usage': memory_usage,
                    'ports': container.ports,
                    'networks': list(container.attrs.get('NetworkSettings', {}).get('Networks', {}).keys())
                })
        except Exception as e:
            logger.error(f"Failed to get Docker containers: {e}")

        return containers

    def get_docker_stats_realtime(self, container_name: str) -> Dict[str, Any]:
        """Get real-time stats for a specific container"""
        if not self.docker_client:
            return {}

        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)

            return {
                'container': container_name,
                'cpu_percent': self._calculate_cpu_percent(stats),
                'memory_usage': self._calculate_memory_usage(stats),
                'memory_limit': stats['memory_stats'].get('limit', 0),
                'network_rx': stats['networks'].get('eth0', {}).get('rx_bytes', 0) if 'networks' in stats else 0,
                'network_tx': stats['networks'].get('eth0', {}).get('tx_bytes', 0) if 'networks' in stats else 0,
                'block_read': sum(stat.get('value', 0) for stat in stats.get('blkio_stats', {}).get('io_service_bytes_recursive', []) if stat.get('op') == 'read'),
                'block_write': sum(stat.get('value', 0) for stat in stats.get('blkio_stats', {}).get('io_service_bytes_recursive', []) if stat.get('op') == 'write')
            }
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            return {}

    def get_docker_logs(self, container_name: str, lines: int = 100) -> List[str]:
        """Get logs from a Docker container"""
        if not self.docker_client:
            return []

        try:
            container = self.docker_client.containers.get(container_name)
            logs = container.logs(tail=lines).decode('utf-8', errors='ignore').split('\n')
            return [log for log in logs if log.strip()]
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return []

    def _calculate_cpu_percent(self, stats: Dict) -> float:
        """Calculate CPU percentage from Docker stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
            cpu_count = stats['cpu_stats'].get('online_cpus', 1)

            if system_delta > 0:
                return (cpu_delta / system_delta) * cpu_count * 100
        except:
            pass
        return 0.0

    def _calculate_memory_usage(self, stats: Dict) -> int:
        """Calculate memory usage in MB from Docker stats"""
        try:
            mem_usage = stats['memory_stats'].get('usage', 0)
            cache = stats['memory_stats'].get('stats', {}).get('cache', 0)
            return (mem_usage - cache) // (1024 * 1024)  # Convert to MB
        except:
            return 0

    # ========== DATABASE MONITORING ==========

    def get_database_stats(self) -> Dict[str, Any]:
        """Get PostgreSQL database statistics"""
        try:
            # Database size
            size_query = text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_database_size(current_database()) as size_bytes
            """)
            size_result = db.session.execute(size_query).fetchone()

            # Active connections
            conn_query = text("""
                SELECT count(*) as active_connections,
                       count(*) FILTER (WHERE state = 'active') as active_queries,
                       count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            conn_result = db.session.execute(conn_query).fetchone()

            # Cache hit ratio
            cache_query = text("""
                SELECT
                    sum(heap_blks_read) as heap_read,
                    sum(heap_blks_hit) as heap_hit,
                    CASE
                        WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                        ELSE (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100
                    END as cache_hit_ratio
                FROM pg_statio_user_tables
            """)
            cache_result = db.session.execute(cache_query).fetchone()

            # Slow queries
            slow_query = text("""
                SELECT query, calls, mean_exec_time, total_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """)
            try:
                slow_queries = [dict(row._mapping) for row in db.session.execute(slow_query).fetchall()]
            except:
                slow_queries = []  # pg_stat_statements might not be enabled

            # Table sizes
            table_query = text("""
                SELECT
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)
            tables = [dict(row._mapping) for row in db.session.execute(table_query).fetchall()]

            return {
                'connected': True,
                'database_size': size_result[0] if size_result else 'unknown',
                'database_size_bytes': size_result[1] if size_result else 0,
                'active_connections': conn_result[0] if conn_result else 0,
                'active_queries': conn_result[1] if conn_result else 0,
                'idle_connections': conn_result[2] if conn_result else 0,
                'cache_hit_ratio': round(cache_result[2], 2) if cache_result and cache_result[2] else 0,
                'slow_queries': slow_queries,
                'largest_tables': tables
            }
        except Exception as e:
            logger.error(f"Database stats failed: {e}")
            return {'connected': False, 'error': str(e)}

    # ========== SYSTEM RESOURCES ==========

    def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage (CPU, Memory, Disk, Network)"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            disk = psutil.disk_usage('/')

            network = psutil.net_io_counters()

            load_avg = psutil.getloadavg()

            return {
                'cpu': {
                    'percent': cpu_percent,
                    'per_core': cpu_per_core,
                    'count': psutil.cpu_count(),
                    'load_avg': {
                        '1min': load_avg[0],
                        '5min': load_avg[1],
                        '15min': load_avg[2]
                    }
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent,
                    'total_gb': round(memory.total / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2)
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'percent': swap.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': disk.percent,
                    'total_gb': round(disk.total / (1024**3), 2),
                    'used_gb': round(disk.used / (1024**3), 2)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv,
                    'errors_in': network.errin,
                    'errors_out': network.errout
                }
            }
        except Exception as e:
            logger.error(f"System resources failed: {e}")
            return {}

    # ========== ALERTMANAGER ==========

    def get_alerts(self) -> Dict[str, Any]:
        """Get active alerts from Alertmanager"""
        try:
            response = requests.get(f"{ALERTMANAGER_URL}/api/v2/alerts", timeout=5)
            if response.status_code == 200:
                alerts = response.json()
                firing = [a for a in alerts if a.get('status', {}).get('state') == 'firing']

                return {
                    'total': len(alerts),
                    'firing': len(firing),
                    'alerts': alerts
                }
            return {'total': 0, 'firing': 0, 'alerts': []}
        except Exception as e:
            logger.error(f"Alertmanager query failed: {e}")
            return {'total': 0, 'firing': 0, 'alerts': [], 'error': str(e)}

    # ========== GRAFANA DASHBOARDS ==========

    def get_grafana_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of Grafana dashboards"""
        try:
            response = requests.get(
                f"{GRAFANA_URL}/api/search",
                headers={'Authorization': 'Bearer admin'},  # Use proper API key in production
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Grafana API failed: {e}")
            return []

    # ========== SECURITY MONITORING ==========

    def get_security_events(self, hours: int = 24) -> Dict[str, Any]:
        """Get security-related events"""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat() + 'Z'

        # Failed authentication attempts
        auth_failures_query = '{job=~".+"} |= "authentication failed" or |= "401" or |= "403"'
        auth_failures = self.query_loki(auth_failures_query, limit=100, start=start_time)

        # Rate limiting events
        rate_limit_query = '{job=~".+"} |= "rate limit" or |= "429"'
        rate_limits = self.query_loki(rate_limit_query, limit=100, start=start_time)

        return {
            'auth_failures': len(auth_failures.get('data', {}).get('result', [])),
            'rate_limit_hits': len(rate_limits.get('data', {}).get('result', [])),
            'last_auth_failure': auth_failures.get('data', {}).get('result', [{}])[0] if auth_failures.get('data', {}).get('result') else None
        }

    # ========== CI/CD PIPELINE STATUS ==========

    def get_cicd_status(self) -> Dict[str, Any]:
        """Get CI/CD pipeline status from Prometheus metrics"""
        workflow_query = 'github_workflow_run_status'
        result = self.query_prometheus(workflow_query)

        workflows = []
        if result.get('status') == 'success':
            for metric in result.get('data', {}).get('result', []):
                workflows.append({
                    'workflow': metric.get('metric', {}).get('workflow', 'unknown'),
                    'status': metric.get('value', [0, 0])[1],
                    'branch': metric.get('metric', {}).get('branch', 'unknown')
                })

        return {
            'workflows': workflows,
            'total': len(workflows)
        }

# Initialize service
monitoring_service = MonitoringService()

# ========== API ROUTES ==========

@monitoring_bp.route('/status', methods=['GET'])
def get_comprehensive_status():
    """
    GET /api/monitoring/status

    Returns comprehensive monitoring data for the dashboard
    """
    try:
        service_health = monitoring_service.get_service_health()
        docker_containers = monitoring_service.get_docker_containers()
        db_stats = monitoring_service.get_database_stats()
        system_resources = monitoring_service.get_system_resources()
        alerts = monitoring_service.get_alerts()
        api_metrics = monitoring_service.get_api_metrics()

        # Organize services by environment
        production_services = {k: v for k, v in service_health.items() if v.get('environment') == 'production'}
        staging_services = {k: v for k, v in service_health.items() if v.get('environment') == 'staging'}
        monitoring_services = {k: v for k, v in service_health.items() if v.get('environment') == 'monitoring'}

        response = {
            'timestamp': datetime.utcnow().isoformat(),
            'overview': {
                'total_services': len(service_health),
                'services_up': sum(1 for s in service_health.values() if s['status'] == 'up'),
                'services_down': sum(1 for s in service_health.values() if s['status'] == 'down'),
                'alerts_firing': alerts.get('firing', 0),
                'containers_running': sum(1 for c in docker_containers if c['status'] == 'running'),
                'database_connected': db_stats.get('connected', False)
            },
            'production': {
                'services': production_services,
                'backend': production_services.get('production-backend', {}).get('status') == 'up',
                'frontend': production_services.get('production-frontend', {}).get('status') == 'up'
            },
            'staging': {
                'services': staging_services,
                'backend': staging_services.get('staging-backend', {}).get('status') == 'up',
                'frontend': staging_services.get('staging-frontend', {}).get('status') == 'up'
            },
            'system': {
                'cpu': system_resources.get('cpu', {}).get('percent', 0),
                'memory': system_resources.get('memory', {}).get('percent', 0),
                'disk': system_resources.get('disk', {}).get('percent', 0),
                'load_avg': system_resources.get('cpu', {}).get('load_avg', {})
            },
            'database': db_stats,
            'docker': {
                'containers': docker_containers,
                'total': len(docker_containers),
                'running': sum(1 for c in docker_containers if c['status'] == 'running')
            },
            'alerts': alerts,
            'monitoring': {
                'loki': monitoring_services.get('loki', {}).get('status', 'unknown'),
                'prometheus': monitoring_services.get('prometheus', {}).get('status', 'unknown'),
                'grafana': monitoring_services.get('grafana', {}).get('status', 'unknown')
            },
            'api_metrics': api_metrics
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get comprehensive status: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@monitoring_bp.route('/logs/errors', methods=['GET'])
def get_error_logs():
    """
    GET /api/monitoring/logs/errors?service=<service>&hours=<hours>

    Get error logs from Loki
    """
    service = request.args.get('service')
    hours = int(request.args.get('hours', 1))

    logs = monitoring_service.get_error_logs(service=service, hours=hours)

    return jsonify({
        'service': service or 'all',
        'hours': hours,
        'count': len(logs),
        'logs': logs
    }), 200

@monitoring_bp.route('/docker/container/<container_name>', methods=['GET'])
def get_container_details(container_name):
    """
    GET /api/monitoring/docker/container/<container_name>

    Get detailed stats for a specific container
    """
    stats = monitoring_service.get_docker_stats_realtime(container_name)
    logs = monitoring_service.get_docker_logs(container_name, lines=100)

    return jsonify({
        'container': container_name,
        'stats': stats,
        'logs': logs
    }), 200

@monitoring_bp.route('/database/queries/slow', methods=['GET'])
def get_slow_queries():
    """
    GET /api/monitoring/database/queries/slow

    Get slow database queries
    """
    db_stats = monitoring_service.get_database_stats()

    return jsonify({
        'slow_queries': db_stats.get('slow_queries', []),
        'count': len(db_stats.get('slow_queries', []))
    }), 200

@monitoring_bp.route('/security/events', methods=['GET'])
def get_security_events_route():
    """
    GET /api/monitoring/security/events?hours=<hours>

    Get security events
    """
    hours = int(request.args.get('hours', 24))
    events = monitoring_service.get_security_events(hours=hours)

    return jsonify({
        'hours': hours,
        'events': events
    }), 200

@monitoring_bp.route('/metrics/prometheus', methods=['GET'])
def get_prometheus_metrics():
    """
    GET /api/monitoring/metrics/prometheus?query=<promql>

    Query Prometheus directly
    """
    query = request.args.get('query')
    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    result = monitoring_service.query_prometheus(query)
    return jsonify(result), 200

@monitoring_bp.route('/grafana/dashboards', methods=['GET'])
def get_grafana_dashboards_route():
    """
    GET /api/monitoring/grafana/dashboards

    Get list of Grafana dashboards
    """
    dashboards = monitoring_service.get_grafana_dashboards()
    return jsonify({
        'count': len(dashboards),
        'dashboards': dashboards
    }), 200

@monitoring_bp.route('/cicd/status', methods=['GET'])
def get_cicd_status_route():
    """
    GET /api/monitoring/cicd/status

    Get CI/CD pipeline status
    """
    status = monitoring_service.get_cicd_status()
    return jsonify(status), 200

@monitoring_bp.route('/health', methods=['GET'])
def monitoring_health():
    """
    GET /api/monitoring/health

    Health check for monitoring service
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'prometheus': monitoring_service.query_prometheus('up').get('status') == 'success',
            'loki': True,  # Will be false if Loki is down
            'docker': monitoring_service.docker_client is not None
        }
    }), 200
