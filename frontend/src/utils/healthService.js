/**
 * Frontend Health Monitoring Service
 * Provides health checks and system status monitoring for the TovPlay frontend
 */

class HealthService {
  constructor() {
    this.apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5001";
    this.startTime = Date.now();
    this.healthData = {
      status: "unknown",
      lastCheck: null,
      backend: null,
      performance: null,
      errors: []
    };
  }

  /**
     * Get basic health status for the frontend
     */
  getHealth() {
    const now = Date.now();
    const uptime = Math.floor((now - this.startTime) / 1000);

    return {
      service: "frontend",
      status: "healthy",
      timestamp: new Date().toISOString(),
      uptime_seconds: uptime,
      version: import.meta.env.VITE_APP_VERSION || "unknown",
      environment: import.meta.env.NODE_ENV || "development",
      build_timestamp: import.meta.env.VITE_BUILD_TIMESTAMP || "unknown"
    };
  }

  /**
     * Check backend API connectivity
     */
  async checkBackendHealth() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

      const response = await fetch(`${this.apiBaseUrl}/health`, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json"
        }
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Backend health check failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      return {
        status: "healthy",
        response_time_ms: response.headers.get("X-Response-Time"),
        backend_status: data.status,
        backend_service: data.service,
        last_check: new Date().toISOString()
      };

    } catch (error) {
      if (error.name === "AbortError") {
        return {
          status: "timeout",
          error: "Backend health check timed out after 10 seconds",
          last_check: new Date().toISOString()
        };
      }

      return {
        status: "unhealthy",
        error: error.message,
        last_check: new Date().toISOString()
      };
    }
  }

  /**
     * Check browser/client capabilities and performance
     */
  checkClientHealth() {
    const performance = window.performance;
    const navigator = window.navigator;
    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;

    const memoryInfo = performance.memory ? {
      used_mb: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
      total_mb: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
      limit_mb: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
    } : null;

    const connectionInfo = connection ? {
      effective_type: connection.effectiveType,
      downlink: connection.downlink,
      rtt: connection.rtt,
      save_data: connection.saveData
    } : null;

    return {
      status: "healthy",
      browser: {
        user_agent: navigator.userAgent,
        language: navigator.language,
        online: navigator.onLine,
        cookie_enabled: navigator.cookieEnabled,
        platform: navigator.platform
      },
      performance: {
        memory: memoryInfo,
        connection: connectionInfo,
        timing: {
          navigation_start: performance.timeOrigin,
          dom_content_loaded: performance.timing ?
            performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart : null,
          load_complete: performance.timing ?
            performance.timing.loadEventEnd - performance.timing.navigationStart : null
        }
      },
      storage: {
        local_storage_available: this.checkStorageAvailable("localStorage"),
        session_storage_available: this.checkStorageAvailable("sessionStorage"),
        indexed_db_available: "indexedDB" in window
      }
    };
  }

  /**
     * Check if a storage type is available
     */
  checkStorageAvailable(type) {
    try {
      const storage = window[type];
      const testKey = "__storage_test__";
      storage.setItem(testKey, "test");
      storage.removeItem(testKey);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
     * Comprehensive health check including backend and client
     */
  async getDetailedHealth() {
    const startTime = performance.now();

    const baseHealth = this.getHealth();
    const clientHealth = this.checkClientHealth();

    let backendHealth;
    try {
      backendHealth = await this.checkBackendHealth();
    } catch (error) {
      backendHealth = {
        status: "error",
        error: error.message,
        last_check: new Date().toISOString()
      };
    }

    const responseTime = Math.round(performance.now() - startTime);

    const overallStatus = this.determineOverallStatus(baseHealth.status, clientHealth.status, backendHealth.status);

    return {
      ...baseHealth,
      overall_status: overallStatus,
      response_time_ms: responseTime,
      checks: {
        frontend: {
          status: baseHealth.status,
          ...clientHealth
        },
        backend: backendHealth
      }
    };
  }

  /**
     * Determine overall system health status
     */
  determineOverallStatus(frontendStatus, clientStatus, backendStatus) {
    const statuses = [frontendStatus, clientStatus, backendStatus];

    if (statuses.includes("unhealthy") || statuses.includes("error")) {
      return "unhealthy";
    }

    if (statuses.includes("timeout") || statuses.includes("degraded")) {
      return "degraded";
    }

    return "healthy";
  }

  /**
     * Log error for health monitoring
     */
  logError(error, context = {}) {
    const errorInfo = {
      timestamp: new Date().toISOString(),
      message: error.message,
      stack: error.stack,
      context: context,
      url: window.location.href,
      user_agent: navigator.userAgent
    };

    this.healthData.errors.push(errorInfo);

    // Keep only last 50 errors
    if (this.healthData.errors.length > 50) {
      this.healthData.errors = this.healthData.errors.slice(-50);
    }

    // Log to console in development
    if (import.meta.env.NODE_ENV === "development") {
      console.error("Health Service - Error logged:", errorInfo);
    }
  }

  /**
     * Start periodic health monitoring
     */
  startMonitoring(intervalMs = 30000) {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    this.monitoringInterval = setInterval(async () => {
      try {
        this.healthData = await this.getDetailedHealth();

        // Dispatch custom event for components to listen to
        window.dispatchEvent(new CustomEvent("healthUpdate", {
          detail: this.healthData
        }));

      } catch (error) {
        this.logError(error, { source: "health_monitoring" });
      }
    }, intervalMs);

    console.log(`Health monitoring started with ${intervalMs}ms interval`);
  }

  /**
     * Stop health monitoring
     */
  stopMonitoring() {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
      console.log("Health monitoring stopped");
    }
  }

  /**
     * Get current cached health data
     */
  getCachedHealth() {
    return this.healthData;
  }

  /**
     * Get recent errors
     */
  getRecentErrors(limit = 10) {
    return this.healthData.errors.slice(-limit);
  }
}

// Create singleton instance
const healthService = new HealthService();

export default healthService;
