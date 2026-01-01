"""
Holistic Prometheus metrics for the TovPlay backend.

This module instruments every layer required for zero-blind-spot observability:
authentication, database, realtime sockets, CI/CD automation, integrations,
business logic KPIs, client RUM signals, log pipeline health, and FinOps posture.
"""

from __future__ import annotations

import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

import psycopg2
from flask import request
from prometheus_client import Counter, Gauge, Histogram


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def current_environment() -> str:
    """Return the current environment label."""
    return os.getenv("FLASK_ENV", "production")


def _labels(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    data = {"environment": current_environment()}
    if extra:
        data.update(extra)
    return data


# ---------------------------------------------------------------------------
# 1. Authentication, Security & Access Control
# ---------------------------------------------------------------------------
auth_login_attempts = Counter(
    "auth_login_attempts_total",
    "Total login attempts",
    ["environment", "status", "method"],
)

auth_login_duration = Histogram(
    "auth_login_duration_seconds",
    "Login endpoint duration",
    ["environment", "status"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, float("inf")),
)

auth_jwt_validations = Counter(
    "auth_jwt_validations_total",
    "JWT validation attempts",
    ["environment", "status"],
)

auth_active_sessions = Gauge(
    "auth_active_sessions",
    "Active user sessions",
    ["environment"],
)

auth_password_reset_requests = Counter(
    "auth_password_reset_requests_total",
    "Password reset requests",
    ["environment", "status"],
)

auth_email_verification_sent = Counter(
    "auth_email_verification_sent_total",
    "Email verification mails sent",
    ["environment", "status"],
)

auth_login_failure_reasons = Counter(
    "auth_login_failure_reasons_total",
    "Login failure reasons",
    ["environment", "reason", "method"],
)

auth_signup_attempts = Counter(
    "auth_signup_attempts_total",
    "User signup attempts",
    ["environment", "status"],
)

auth_signup_duration = Histogram(
    "auth_signup_duration_seconds",
    "Signup endpoint duration",
    ["environment", "status"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, float("inf")),
)

auth_email_verification_attempts = Counter(
    "auth_email_verification_attempts_total",
    "Email verification attempts",
    ["environment", "status"],
)

auth_password_change_attempts = Counter(
    "auth_password_change_attempts_total",
    "Password change attempts",
    ["environment", "status"],
)

user_profile_fetches = Counter(
    "user_profile_fetches_total",
    "User profile fetch attempts",
    ["environment", "status"],
)

user_deletion_attempts = Counter(
    "user_deletion_attempts_total",
    "User deletion attempts",
    ["environment", "status"],
)

username_availability_checks = Counter(
    "username_availability_checks_total",
    "Username availability checks",
    ["environment", "result"],
)

security_bruteforce_total = Counter(
    "security_bruteforce_total",
    "Detected brute force attempts",
    ["environment", "source"],
)

security_sql_injection_matches_total = Counter(
    "security_sql_injection_matches_total",
    "SQL injection payloads blocked",
    ["environment", "route"],
)

security_xss_detected_total = Counter(
    "security_xss_detected_total",
    "XSS payloads blocked",
    ["environment", "route"],
)

security_privilege_escalation_attempts_total = Counter(
    "security_privilege_escalation_attempts_total",
    "403 attempts to privileged routes",
    ["environment", "route", "user_id"],
)

security_geo_anomaly_events_total = Counter(
    "security_geo_anomaly_events_total",
    "Traffic from unexpected geo regions",
    ["environment", "country"],
)

security_password_reset_flood_total = Counter(
    "security_password_reset_flood_total",
    "Password reset flood detections",
    ["environment"],
)

security_account_lockouts_total = Counter(
    "security_account_lockouts_total",
    "Accounts locked due to abuse",
    ["environment"],
)

tls_version_downgrade_total = Counter(
    "tls_version_downgrade_total",
    "Deprecated TLS usage attempts",
    ["environment", "client_version"],
)

security_csp_violations_total = Counter(
    "security_csp_violations_total",
    "Content Security Policy violations",
    ["environment", "directive"],
)

security_payload_anomaly_bytes_total = Counter(
    "security_payload_anomaly_bytes_total",
    "Bytes flagged by payload anomaly detection",
    ["environment", "route"],
)

security_admin_activity_total = Counter(
    "security_admin_activity_total",
    "Volume of admin actions",
    ["environment", "action"],
)

rate_limit_hits = Counter(
    "rate_limit_hits_total",
    "Rate limiter decisions",
    ["environment", "endpoint", "result"],
)

rate_limit_blocks_total = Counter(
    "rate_limit_blocks_total",
    "Blocked requests by rate limiter",
    ["environment", "endpoint", "reason"],
)


# ---------------------------------------------------------------------------
# 2. Discord OAuth & External Integrations
# ---------------------------------------------------------------------------
discord_oauth_callbacks = Counter(
    "discord_oauth_callbacks_total",
    "Discord OAuth callbacks",
    ["environment", "status"],
)

discord_token_exchange_duration = Histogram(
    "discord_token_exchange_duration_seconds",
    "Discord OAuth token exchange duration",
    ["environment", "status"],
    buckets=(0.25, 0.5, 1, 2, 3, 5, 10, float("inf")),
)

discord_api_requests = Counter(
    "discord_api_requests_total",
    "Discord API requests",
    ["environment", "endpoint", "status"],
)

discord_api_errors = Counter(
    "discord_api_errors_total",
    "Discord API errors",
    ["environment", "error_type", "endpoint"],
)

discord_guild_operations = Counter(
    "discord_guild_operations_total",
    "Guild operations (role add/remove etc.)",
    ["environment", "operation", "status"],
)

discord_rate_limit_hits = Counter(
    "discord_rate_limit_hits_total",
    "Discord API rate limit hits",
    ["environment", "endpoint"],
)

oauth_state_mismatch_total = Counter(
    "oauth_state_mismatch_total",
    "OAuth state/token mismatches",
    ["environment"],
)

email_delivery_failures_total = Counter(
    "email_delivery_failures_total",
    "SMTP delivery failures",
    ["environment", "reason"],
)

integration_latency_seconds = Histogram(
    "integration_latency_seconds",
    "Latency of third party API calls",
    ["environment", "service"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 1.5, 2, 5, 10, float("inf")),
)

integration_failures_total = Counter(
    "integration_failures_total",
    "Failed calls to third party APIs",
    ["environment", "service", "reason"],
)

integration_retries_total = Counter(
    "integration_retries_total",
    "Retry attempts for integrations",
    ["environment", "service", "reason"],
)

integration_quota_remaining = Gauge(
    "integration_quota_remaining",
    "Remaining quota ratio (0-1) per integration",
    ["environment", "service"],
)

integration_credential_expiry_days = Gauge(
    "integration_credential_expiry_days",
    "Days until credential expiration",
    ["environment", "credential"],
)

integration_malformed_payload_total = Counter(
    "integration_malformed_payload_total",
    "Malformed payloads received from partners",
    ["environment", "service"],
)

integration_event_lag_seconds = Gauge(
    "integration_event_lag_seconds",
    "Lag between webhook receipt and processing",
    ["environment", "service"],
)


# ---------------------------------------------------------------------------
# 3. Database Metrics
# ---------------------------------------------------------------------------
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["environment", "operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, float("inf")),
)

db_query_errors = Counter(
    "db_query_errors_total",
    "Database query errors",
    ["environment", "error_type", "table"],
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Database connection pool state",
    ["environment", "state"],
)

db_slow_queries = Counter(
    "db_slow_queries_total",
    "Queries exceeding 1s",
    ["environment", "table", "operation"],
)

db_long_running_transactions = Counter(
    "db_long_running_transactions_total",
    "Transactions exceeding threshold",
    ["environment", "table", "operation"],
)

db_deadlocks = Counter(
    "db_deadlocks_total",
    "Application detected deadlocks",
    ["environment", "table"],
)

db_connection_retries = Counter(
    "db_connection_retries_total",
    "Retries opening DB connections",
    ["environment", "status"],
)

api_route_db_duration = Histogram(
    "api_route_db_duration_seconds",
    "DB time spent per API endpoint",
    ["environment", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, float("inf")),
)


# ---------------------------------------------------------------------------
# 4. API / Backend Runtime / Gunicorn / Socket.IO
# ---------------------------------------------------------------------------
api_endpoint_calls = Counter(
    "api_endpoint_calls_total",
    "API endpoint invocations",
    ["environment", "endpoint", "method", "status_code"],
)

api_endpoint_duration = Histogram(
    "api_endpoint_duration_seconds",
    "API endpoint latency",
    ["environment", "endpoint", "method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, float("inf")),
)

api_endpoint_errors = Counter(
    "api_endpoint_errors_total",
    "Unhandled exceptions per endpoint",
    ["environment", "endpoint", "error_type", "status_code"],
)

api_request_size = Histogram(
    "api_request_size_bytes",
    "Incoming request payload sizes",
    ["environment", "endpoint"],
    buckets=(128, 512, 1024, 4096, 16384, 65536, 262144, 1048576, float("inf")),
)

gunicorn_request_queue_depth = Gauge(
    "gunicorn_request_queue_depth",
    "Pending requests queued ahead of workers",
    ["environment"],
)

backend_gc_pause_seconds = Counter(
    "backend_gc_pause_seconds_total",
    "Python GC pause time",
    ["environment"],
)

backend_worker_memory_bytes = Gauge(
    "backend_worker_memory_bytes",
    "Memory used by each Gunicorn worker",
    ["environment", "worker"],
)

jwt_processing_duration = Histogram(
    "jwt_processing_duration_seconds",
    "JWT encode/decode duration",
    ["environment", "operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, float("inf")),
)

socketio_packets_total = Counter(
    "socketio_packets_total",
    "Socket.IO packets processed",
    ["environment", "direction"],
)

socketio_disconnects_total = Counter(
    "socketio_disconnects_total",
    "Socket.IO disconnect events",
    ["environment", "reason"],
)

socketio_active_rooms = Gauge(
    "socketio_active_rooms",
    "Active Socket.IO rooms",
    ["environment"],
)


# ---------------------------------------------------------------------------
# 5. External Dependency Latency (SMTP, Discord, other REST APIs)
# ---------------------------------------------------------------------------
external_dependency_latency = Histogram(
    "external_dependency_latency_seconds",
    "Latency per dependency call",
    ["environment", "dependency"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, float("inf")),
)

external_dependency_failures = Counter(
    "external_dependency_failures_total",
    "Failures by dependency",
    ["environment", "dependency", "reason"],
)


# ---------------------------------------------------------------------------
# 6. CI/CD, GitHub Actions, Docker Hub
# ---------------------------------------------------------------------------
cicd_workflow_runs_total = Counter(
    "cicd_workflow_runs_total",
    "Workflow run outcomes",
    ["environment", "workflow", "status", "branch"],
)

cicd_workflow_duration = Histogram(
    "cicd_workflow_duration_seconds",
    "Workflow runtime seconds",
    ["environment", "workflow"],
    buckets=(60, 120, 300, 600, 900, 1200, 1800, 2700, 3600, float("inf")),
)

cicd_runner_queue_length = Gauge(
    "cicd_runner_queue_length",
    "Queued jobs per runner pool",
    ["environment", "runner"],
)

cicd_pending_jobs = Gauge(
    "cicd_pending_jobs",
    "Pending jobs waiting for runners",
    ["environment", "runner"],
)

cicd_artifact_storage_bytes = Gauge(
    "cicd_artifact_storage_bytes",
    "Artifact/cache storage consumption",
    ["environment", "repository"],
)

cicd_api_rate_limit_remaining = Gauge(
    "cicd_api_rate_limit_remaining",
    "Remaining API quota ratio (0-1)",
    ["environment", "service"],
)

cicd_deployments_total = Counter(
    "cicd_deployments_total",
    "Deploy outcomes per environment",
    ["environment", "target", "result"],
)

cicd_mttr_minutes = Gauge(
    "cicd_mttr_minutes",
    "Mean time to recovery (minutes)",
    ["environment", "target"],
)

cicd_security_vulnerabilities_total = Gauge(
    "cicd_security_vulnerabilities_total",
    "Outstanding vulnerabilities from CI scans",
    ["environment", "severity"],
)

cicd_environment_drift_findings_total = Counter(
    "cicd_environment_drift_findings_total",
    "Drift findings detected by CI",
    ["environment", "target"],
)

cicd_image_pull_latency = Histogram(
    "cicd_image_pull_latency_seconds",
    "Time required to pull Docker images",
    ["environment", "image"],
    buckets=(1, 2, 5, 10, 20, 30, 60, 120, float("inf")),
)


# ---------------------------------------------------------------------------
# 7. Frontend / RUM telemetry
# ---------------------------------------------------------------------------
frontend_client_errors_total = Counter(
    "frontend_client_errors_total",
    "window.onerror / client error buckets",
    ["environment", "type"],
)

frontend_asset_failures_total = Counter(
    "frontend_asset_failures_total",
    "Failed static asset loads",
    ["environment", "asset_type"],
)

frontend_geo_requests_total = Counter(
    "frontend_geo_requests_total",
    "Requests grouped by client country",
    ["environment", "country"],
)

frontend_user_agent_breakdown_total = Counter(
    "frontend_user_agent_breakdown_total",
    "Traffic grouped by UA class",
    ["environment", "agent_class"],
)

frontend_request_size_bytes = Histogram(
    "frontend_request_size_bytes",
    "Request payload sizes from clients",
    ["environment", "route"],
    buckets=(1024, 4096, 16384, 65536, 262144, 1048576, float("inf")),
)

frontend_route_transition_seconds = Histogram(
    "frontend_route_transition_seconds",
    "Client-side route transition durations",
    ["environment", "route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, float("inf")),
)

frontend_concurrent_connections = Gauge(
    "frontend_concurrent_connections",
    "Client connections observed by frontend telemetry",
    ["environment"],
)

rum_page_load_seconds = Histogram(
    "rum_page_load_seconds",
    "Real user page load timings",
    ["environment", "route", "device_class"],
    buckets=(0.5, 1, 1.5, 2, 3, 4, 5, float("inf")),
)

rum_js_errors_total = Counter(
    "rum_js_errors_total",
    "Client-side JS errors",
    ["environment", "route"],
)

rum_api_failures_total = Counter(
    "rum_api_failures_total",
    "Client API call failures",
    ["environment", "route"],
)

rum_asset_failures_total = Counter(
    "rum_asset_failures_total",
    "Client asset load failures",
    ["environment", "asset_type"],
)

rum_route_transition_seconds = Histogram(
    "rum_route_transition_seconds",
    "SPA navigation latency",
    ["environment", "route"],
    buckets=(0.1, 0.25, 0.5, 1, 2, float("inf")),
)

rum_device_latency_seconds = Histogram(
    "rum_device_latency_seconds",
    "Device class specific latency",
    ["environment", "device_class"],
    buckets=(0.5, 1, 2, 4, 6, float("inf")),
)

rum_input_latency_seconds = Histogram(
    "rum_input_latency_seconds",
    "Time from user input to response",
    ["environment"],
    buckets=(0.05, 0.1, 0.15, 0.2, 0.3, float("inf")),
)

rum_websocket_disconnects_total = Counter(
    "rum_websocket_disconnects_total",
    "Client initiated WebSocket disconnects",
    ["environment", "reason"],
)

rum_pwa_installs_total = Counter(
    "rum_pwa_installs_total",
    "PWA installation events",
    ["environment"],
)


# ---------------------------------------------------------------------------
# 8. Business Logic & Gameplay KPIs
# ---------------------------------------------------------------------------
game_sessions_active = Gauge(
    "game_sessions_active",
    "Active game sessions",
    ["environment"],
)

game_session_outcomes_total = Counter(
    "game_session_outcomes_total",
    "Game session outcomes",
    ["environment", "status"],
)

matchmaking_wait_time_seconds = Histogram(
    "matchmaking_wait_time_seconds",
    "Queue wait time for matchmaking",
    ["environment"],
    buckets=(1, 5, 15, 30, 60, 120, 300, float("inf")),
)

player_daily_active_users = Gauge(
    "player_daily_active_users",
    "Daily active users snapshot",
    ["environment"],
)

player_retention_rate = Gauge(
    "player_retention_rate",
    "Retention ratio (0-1)",
    ["environment"],
)

virtual_currency_transfers_total = Counter(
    "virtual_currency_transfers_total",
    "Virtual currency transfers",
    ["environment", "direction"],
)

virtual_currency_anomalies_total = Counter(
    "virtual_currency_anomalies_total",
    "Currency integrity anomalies",
    ["environment", "reason"],
)

chat_messages_total = Counter(
    "chat_messages_total",
    "Chat messages and moderation flags",
    ["environment", "channel", "flag"],
)

progression_events_total = Counter(
    "progression_events_total",
    "Progression milestones (level-ups, achievements)",
    ["environment", "event"],
)

registration_funnel_total = Counter(
    "registration_funnel_total",
    "Signup funnel progression",
    ["environment", "stage"],
)

session_abandonment_total = Counter(
    "session_abandonment_total",
    "Scheduled sessions abandoned early",
    ["environment", "reason"],
)

moderation_events_total = Counter(
    "moderation_events_total",
    "Moderation actions or reports",
    ["environment", "action"],
)


# ---------------------------------------------------------------------------
# 9. Log Health & Observability
# ---------------------------------------------------------------------------
log_ingestion_lag_seconds = Gauge(
    "log_ingestion_lag_seconds",
    "Seconds of lag between emit and ingest",
    ["environment"],
)

log_events_total = Counter(
    "log_events_total",
    "Structured log events by level",
    ["environment", "level"],
)

log_parsing_failures_total = Counter(
    "log_parsing_failures_total",
    "Failed structured log parses",
    ["environment"],
)

log_panic_events_total = Counter(
    "log_panic_events_total",
    "Detected panic/fatal log keywords",
    ["environment"],
)

log_stream_silence_seconds = Gauge(
    "log_stream_silence_seconds",
    "How long a stream has been silent",
    ["environment", "stream"],
)

log_debug_leak_total = Counter(
    "log_debug_leak_total",
    "Debug log entries in production",
    ["environment"],
)

log_pii_detected_total = Counter(
    "log_pii_detected_total",
    "PII patterns detected in logs",
    ["environment", "pii_type"],
)

log_rotation_failures_total = Counter(
    "log_rotation_failures_total",
    "Log rotation job failures",
    ["environment"],
)

log_correlation_id_ratio = Gauge(
    "log_correlation_id_ratio",
    "Ratio of logs including correlation IDs",
    ["environment"],
)


# ---------------------------------------------------------------------------
# 10. Cost & Resource Efficiency (FinOps)
# ---------------------------------------------------------------------------
finops_resource_utilization_ratio = Gauge(
    "finops_resource_utilization_ratio",
    "Utilization ratio per resource class",
    ["environment", "resource"],
)

finops_idle_container_minutes = Gauge(
    "finops_idle_container_minutes",
    "Minutes containers stayed idle",
    ["environment", "container"],
)

finops_network_egress_bytes_total = Counter(
    "finops_network_egress_bytes_total",
    "Network egress bytes counted for cost",
    ["environment"],
)

finops_storage_growth_bytes = Gauge(
    "finops_storage_growth_bytes",
    "Projected storage growth per day",
    ["environment", "mount"],
)

finops_build_minutes_total = Counter(
    "finops_build_minutes_total",
    "Build minutes consumed",
    ["environment", "provider"],
)

finops_cost_per_user_usd = Gauge(
    "finops_cost_per_user_usd",
    "Cost per active user (USD)",
    ["environment"],
)

finops_cache_roi_ratio = Gauge(
    "finops_cache_roi_ratio",
    "Estimated cache ROI (hit/cost ratio)",
    ["environment", "cache"],
)

finops_connection_efficiency_ratio = Gauge(
    "finops_connection_efficiency_ratio",
    "Useful vs idle DB connections ratio",
    ["environment"],
)


# ---------------------------------------------------------------------------
# Background Jobs
# ---------------------------------------------------------------------------
background_jobs_executed = Counter(
    "background_jobs_executed_total",
    "Background job executions",
    ["environment", "job_name", "status"],
)

background_job_duration = Histogram(
    "background_job_duration_seconds",
    "Duration of background jobs",
    ["environment", "job_name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, float("inf")),
)


# ---------------------------------------------------------------------------
# Decorators & helper APIs
# ---------------------------------------------------------------------------
def track_db_query(table: str, operation: str, slow_threshold: float = 1.0) -> Callable:
    """Decorator for DB helper functions to emit query metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            env = current_environment()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                db_query_duration.labels(env, operation, table).observe(duration)
                if duration >= slow_threshold:
                    db_slow_queries.labels(env, table, operation).inc()
                return result
            except psycopg2.DatabaseError as exc:
                duration = time.time() - start
                db_query_duration.labels(env, operation, table).observe(duration)
                error_type = getattr(exc, "__class__", type(exc)).__name__
                db_query_errors.labels(env, error_type, table).inc()
                if "deadlock" in str(exc).lower():
                    db_deadlocks.labels(env, table).inc()
                raise

        return wrapper

    return decorator


def track_endpoint(endpoint_name: str) -> Callable:
    """Decorator to wrap Flask endpoints and emit metrics."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            env = current_environment()
            method = request.method if hasattr(request, "method") else "UNKNOWN"
            if request and getattr(request, "content_length", None):
                api_request_size.labels(env, endpoint_name).observe(request.content_length)

            start = time.time()
            try:
                response = func(*args, **kwargs)
                duration = time.time() - start
                status_code = _extract_status_code(response)
                api_endpoint_calls.labels(env, endpoint_name, method, status_code).inc()
                api_endpoint_duration.labels(env, endpoint_name, method).observe(duration)
                return response
            except Exception as exc:
                duration = time.time() - start
                status_code = getattr(exc, "code", 500)
                api_endpoint_duration.labels(env, endpoint_name, method).observe(duration)
                api_endpoint_errors.labels(
                    env,
                    endpoint_name,
                    type(exc).__name__,
                    status_code,
                ).inc()
                raise

        return wrapper

    return decorator


def track_background_job(job_name: str) -> Callable:
    """Decorator to measure APScheduler / worker jobs."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            env = current_environment()
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                background_jobs_executed.labels(env, job_name, "success").inc()
                background_job_duration.labels(env, job_name).observe(duration)
                return result
            except Exception:
                duration = time.time() - start
                background_jobs_executed.labels(env, job_name, "failure").inc()
                background_job_duration.labels(env, job_name).observe(duration)
                raise

        return wrapper

    return decorator


def _extract_status_code(response: Any) -> int:
    if hasattr(response, "status_code"):
        return int(response.status_code)
    if isinstance(response, tuple) and len(response) >= 2:
        return int(response[1])
    return 200


# ---------------------------------------------------------------------------
# Metric update helpers used throughout the app
# ---------------------------------------------------------------------------
def track_active_sessions(count: int) -> None:
    auth_active_sessions.labels(current_environment()).set(count)


def track_rate_limit(endpoint: str, allowed: bool, reason: str = "allowed") -> None:
    env = current_environment()
    result = "allowed" if allowed else reason
    rate_limit_hits.labels(env, endpoint, result).inc()
    if not allowed:
        rate_limit_blocks_total.labels(env, endpoint, reason).inc()


def track_socketio_event(direction: str, packets: int = 1, rooms: Optional[int] = None) -> None:
    env = current_environment()
    socketio_packets_total.labels(env, direction).inc(packets)
    if rooms is not None:
        socketio_active_rooms.labels(env).set(max(rooms, 0))


def record_socketio_disconnect(reason: str) -> None:
    socketio_disconnects_total.labels(current_environment(), reason).inc()


def record_external_dependency_call(
    dependency: str,
    duration_seconds: float,
    success: bool = True,
    failure_reason: Optional[str] = None,
) -> None:
    env = current_environment()
    external_dependency_latency.labels(env, dependency).observe(duration_seconds)
    if not success:
        external_dependency_failures.labels(env, dependency, failure_reason or "unknown").inc()


def record_integration_latency(service: str, duration_seconds: float, success: bool, reason: str = "ok") -> None:
    env = current_environment()
    integration_latency_seconds.labels(env, service).observe(duration_seconds)
    if not success:
        integration_failures_total.labels(env, service, reason).inc()


def record_integration_retry(service: str, reason: str) -> None:
    integration_retries_total.labels(current_environment(), service, reason).inc()


def update_integration_quota(service: str, remaining_ratio: float) -> None:
    integration_quota_remaining.labels(current_environment(), service).set(max(min(remaining_ratio, 1.0), 0.0))


def update_credential_expiry(name: str, days_remaining: float) -> None:
    integration_credential_expiry_days.labels(current_environment(), name).set(days_remaining)


def observe_oauth_state_mismatch() -> None:
    oauth_state_mismatch_total.labels(current_environment()).inc()


def record_email_delivery_failure(reason: str) -> None:
    email_delivery_failures_total.labels(current_environment(), reason).inc()


def update_runner_queue(runner: str, queued: int, pending: int) -> None:
    env = current_environment()
    cicd_runner_queue_length.labels(env, runner).set(queued)
    cicd_pending_jobs.labels(env, runner).set(pending)


def update_artifact_storage(repository: str, bytes_used: float) -> None:
    cicd_artifact_storage_bytes.labels(current_environment(), repository).set(bytes_used)


def update_ci_rate_limit(service: str, ratio_remaining: float) -> None:
    cicd_api_rate_limit_remaining.labels(current_environment(), service).set(max(min(ratio_remaining, 1.0), 0.0))


def record_ci_workflow_run(workflow: str, status: str, duration_seconds: float, branch: str) -> None:
    env = current_environment()
    cicd_workflow_runs_total.labels(env, workflow, status, branch).inc()
    cicd_workflow_duration.labels(env, workflow).observe(duration_seconds)


def record_ci_deployment(target: str, result: str) -> None:
    cicd_deployments_total.labels(current_environment(), target, result).inc()


def update_ci_mttr(target: str, minutes: float) -> None:
    cicd_mttr_minutes.labels(current_environment(), target).set(minutes)


def update_ci_vulnerabilities(severity: str, count: int) -> None:
    cicd_security_vulnerabilities_total.labels(current_environment(), severity).set(count)


def record_environment_drift(target: str) -> None:
    cicd_environment_drift_findings_total.labels(current_environment(), target).inc()


def record_image_pull_latency(image: str, duration_seconds: float) -> None:
    cicd_image_pull_latency.labels(current_environment(), image).observe(duration_seconds)


def record_frontend_error(error_type: str) -> None:
    frontend_client_errors_total.labels(current_environment(), error_type).inc()


def record_frontend_asset_failure(asset_type: str) -> None:
    frontend_asset_failures_total.labels(current_environment(), asset_type).inc()


def record_frontend_geo(country: str, count: int = 1) -> None:
    frontend_geo_requests_total.labels(current_environment(), country).inc(count)


def record_frontend_user_agent(agent_class: str, count: int = 1) -> None:
    frontend_user_agent_breakdown_total.labels(current_environment(), agent_class).inc(count)


def update_frontend_connections(active_connections: int) -> None:
    frontend_concurrent_connections.labels(current_environment()).set(active_connections)


def record_rum_event(
    route: str,
    page_load: Optional[float] = None,
    device_class: Optional[str] = None,
    js_error: bool = False,
    api_error: bool = False,
    asset_error: Optional[str] = None,
    route_transition: Optional[float] = None,
    input_latency: Optional[float] = None,
    websocket_disconnect_reason: Optional[str] = None,
    pwa_install: bool = False,
) -> None:
    env = current_environment()
    if page_load is not None:
        rum_page_load_seconds.labels(env, route, device_class or "unknown").observe(page_load)
    if js_error:
        rum_js_errors_total.labels(env, route).inc()
    if api_error:
        rum_api_failures_total.labels(env, route).inc()
    if asset_error:
        rum_asset_failures_total.labels(env, asset_error).inc()
    if route_transition is not None:
        rum_route_transition_seconds.labels(env, route).observe(route_transition)
    if device_class is not None and page_load is not None:
        rum_device_latency_seconds.labels(env, device_class).observe(page_load)
    if input_latency is not None:
        rum_input_latency_seconds.labels(env).observe(input_latency)
    if websocket_disconnect_reason:
        rum_websocket_disconnects_total.labels(env, websocket_disconnect_reason).inc()
    if pwa_install:
        rum_pwa_installs_total.labels(env).inc()


def record_matchmaking_wait(seconds_waited: float) -> None:
    matchmaking_wait_time_seconds.labels(current_environment()).observe(seconds_waited)


def update_session_metrics(active_sessions: int, completion_status: Optional[str] = None) -> None:
    env = current_environment()
    game_sessions_active.labels(env).set(active_sessions)
    if completion_status:
        game_session_outcomes_total.labels(env, completion_status).inc()


def update_player_metrics(active_users: Optional[int] = None, retention_ratio: Optional[float] = None) -> None:
    env = current_environment()
    if active_users is not None:
        player_daily_active_users.labels(env).set(active_users)
    if retention_ratio is not None:
        player_retention_rate.labels(env).set(retention_ratio)


def record_virtual_currency_transfer(direction: str, amount: float, anomalous: bool = False, reason: str = "normal") -> None:
    env = current_environment()
    virtual_currency_transfers_total.labels(env, direction).inc(amount)
    if anomalous:
        virtual_currency_anomalies_total.labels(env, reason).inc()


def record_chat_message(channel: str, flag: str = "clean") -> None:
    chat_messages_total.labels(current_environment(), channel, flag).inc()


def record_progression_event(event: str) -> None:
    progression_events_total.labels(current_environment(), event).inc()


def record_registration_stage(stage: str) -> None:
    registration_funnel_total.labels(current_environment(), stage).inc()


def record_session_abandonment(reason: str) -> None:
    session_abandonment_total.labels(current_environment(), reason).inc()


def record_moderation_event(action: str) -> None:
    moderation_events_total.labels(current_environment(), action).inc()


def update_log_ingestion_lag(seconds_lag: float) -> None:
    log_ingestion_lag_seconds.labels(current_environment()).set(seconds_lag)


def record_log_event(level: str, correlation_id_present: bool) -> None:
    env = current_environment()
    log_events_total.labels(env, level).inc()
    log_correlation_id_ratio.labels(env).set(1.0 if correlation_id_present else 0.0)


def set_log_silence(stream: str, seconds_silent: float) -> None:
    log_stream_silence_seconds.labels(current_environment(), stream).set(seconds_silent)


def record_log_parsing_failure() -> None:
    log_parsing_failures_total.labels(current_environment()).inc()


def record_log_panic() -> None:
    log_panic_events_total.labels(current_environment()).inc()


def record_log_debug_leak() -> None:
    log_debug_leak_total.labels(current_environment()).inc()


def record_log_pii(pii_type: str) -> None:
    log_pii_detected_total.labels(current_environment(), pii_type).inc()


def record_log_rotation_failure() -> None:
    log_rotation_failures_total.labels(current_environment()).inc()


def update_log_correlation_ratio(ratio: float) -> None:
    log_correlation_id_ratio.labels(current_environment()).set(max(min(ratio, 1.0), 0.0))


def record_finops_snapshot(
    resource_utilization: Optional[Dict[str, float]] = None,
    idle_container_minutes: Optional[Dict[str, float]] = None,
    network_egress_bytes: Optional[float] = None,
    storage_growth: Optional[Dict[str, float]] = None,
    build_minutes: Optional[Dict[str, float]] = None,
    cost_per_user: Optional[float] = None,
    cache_roi: Optional[Dict[str, float]] = None,
    connection_efficiency: Optional[float] = None,
) -> None:
    env = current_environment()
    if resource_utilization:
        for resource, ratio in resource_utilization.items():
            finops_resource_utilization_ratio.labels(env, resource).set(ratio)
    if idle_container_minutes:
        for container, minutes in idle_container_minutes.items():
            finops_idle_container_minutes.labels(env, container).set(minutes)
    if network_egress_bytes is not None:
        finops_network_egress_bytes_total.labels(env).inc(network_egress_bytes)
    if storage_growth:
        for mount, growth in storage_growth.items():
            finops_storage_growth_bytes.labels(env, mount).set(growth)
    if build_minutes:
        for provider, minutes in build_minutes.items():
            finops_build_minutes_total.labels(env, provider).inc(minutes)
    if cost_per_user is not None:
        finops_cost_per_user_usd.labels(env).set(cost_per_user)
    if cache_roi:
        for cache, ratio in cache_roi.items():
            finops_cache_roi_ratio.labels(env, cache).set(ratio)
    if connection_efficiency is not None:
        finops_connection_efficiency_ratio.labels(env).set(connection_efficiency)


def update_security_bruteforce(source: str) -> None:
    security_bruteforce_total.labels(current_environment(), source).inc()


def record_security_event(counter: Counter, **labels: str) -> None:
    counter.labels(**_labels(labels)).inc()
