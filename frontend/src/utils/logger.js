/**
 * Frontend Logging Service
 * Provides structured logging for the TovPlay frontend with different log levels
 */

class Logger {
  constructor() {
    this.environment = import.meta.env.NODE_ENV || "development";
    this.logLevel = this.getLogLevel();
    this.sessionId = this.generateSessionId();
    this.logs = [];
    this.maxLogHistory = 1000;
  }

  /**
   * Generate a unique session ID for tracking user sessions
   */
  generateSessionId() {
    return "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
  }

  /**
   * Get appropriate log level based on environment
   */
  getLogLevel() {
    const envLevel = import.meta.env.VITE_LOG_LEVEL;
    if (envLevel) {
      return envLevel.toUpperCase();
    }

    switch (this.environment) {
      case "production":
        return "ERROR";
      case "staging":
        return "WARN";
      case "development":
        return "DEBUG";
      case "test":
        return "ERROR";
      default:
        return "INFO";
    }
  }

  /**
   * Check if log level should be output
   */
  shouldLog(level) {
    const levels = {
      DEBUG: 0,
      INFO: 1,
      WARN: 2,
      ERROR: 3
    };

    return levels[level] >= levels[this.logLevel];
  }

  /**
   * Create structured log entry
   */
  createLogEntry(level, message, context = {}) {
    const timestamp = new Date().toISOString();
    
    const logEntry = {
      timestamp,
      level,
      message,
      sessionId: this.sessionId,
      url: window.location.href,
      userAgent: navigator.userAgent,
      environment: this.environment,
      ...context
    };

    // Add to in-memory log history
    this.logs.push(logEntry);
    if (this.logs.length > this.maxLogHistory) {
      this.logs = this.logs.slice(-this.maxLogHistory);
    }

    return logEntry;
  }

  /**
   * Output log to console with appropriate styling
   */
  outputToConsole(logEntry) {
    const { level, timestamp, message, ...context } = logEntry;
    
    const styles = {
      DEBUG: "color: #888; font-weight: normal;",
      INFO: "color: #2196F3; font-weight: normal;",
      WARN: "color: #FF9800; font-weight: bold;",
      ERROR: "color: #F44336; font-weight: bold;"
    };

    const timeStr = new Date(timestamp).toLocaleTimeString();
    const prefix = `%c[${timeStr}] ${level}`;
    
    console.log(prefix, styles[level], message);
    
    // Log context if present and in development
    if (Object.keys(context).length > 0 && this.environment === "development") {
      console.log("Context:", context);
    }
  }

  /**
   * Send logs to backend (for important logs)
   */
  async sendToBackend(logEntry) {
    // Only send ERROR and WARN logs to backend in production
    if (!["ERROR", "WARN"].includes(logEntry.level)) {
      return;
    }

    if (this.environment === "development") {
      return;
    }

    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL;
      if (!apiUrl) {
        return;
      }

      await fetch(`${apiUrl}/logs/frontend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(logEntry)
      });
    } catch (error) {
      // Fail silently to avoid infinite loops
      console.error("Failed to send log to backend:", error);
    }
  }

  /**
   * Main logging method
   */
  log(level, message, context = {}) {
    if (!this.shouldLog(level)) {
      return;
    }

    const logEntry = this.createLogEntry(level, message, context);
    
    // Always output to console if level is appropriate
    this.outputToConsole(logEntry);
    
    // Send to backend for important logs
    this.sendToBackend(logEntry);

    return logEntry;
  }

  /**
   * Debug level logging
   */
  debug(message, context = {}) {
    return this.log("DEBUG", message, context);
  }

  /**
   * Info level logging
   */
  info(message, context = {}) {
    return this.log("INFO", message, context);
  }

  /**
   * Warning level logging
   */
  warn(message, context = {}) {
    return this.log("WARN", message, context);
  }

  /**
   * Error level logging
   */
  error(message, context = {}) {
    // If message is an Error object, extract details
    if (message instanceof Error) {
      context = {
        ...context,
        error_name: message.name,
        error_message: message.message,
        stack_trace: message.stack
      };
      message = `Error: ${message.message}`;
    }

    return this.log("ERROR", message, context);
  }

  /**
   * Log user actions for analytics
   */
  logUserAction(action, details = {}) {
    return this.info(`User action: ${action}`, {
      action_type: "user_action",
      action,
      details,
      timestamp: Date.now()
    });
  }

  /**
   * Log API requests
   */
  logApiRequest(method, url, status, duration, details = {}) {
    const level = status >= 400 ? "ERROR" : status >= 300 ? "WARN" : "INFO";
    
    return this.log(level, `API ${method} ${url} - ${status}`, {
      request_type: "api_request",
      method,
      url,
      status_code: status,
      duration_ms: duration,
      ...details
    });
  }

  /**
   * Log navigation events
   */
  logNavigation(from, to, details = {}) {
    return this.info(`Navigation: ${from} -> ${to}`, {
      navigation_type: "route_change",
      from_route: from,
      to_route: to,
      ...details
    });
  }

  /**
   * Log performance metrics
   */
  logPerformance(metric, value, details = {}) {
    return this.info(`Performance: ${metric} = ${value}`, {
      performance_metric: metric,
      value,
      ...details
    });
  }

  /**
   * Log security events
   */
  logSecurity(event, details = {}) {
    return this.warn(`Security event: ${event}`, {
      security_event: true,
      event_type: event,
      ...details
    });
  }

  /**
   * Get recent logs
   */
  getRecentLogs(limit = 50) {
    return this.logs.slice(-limit);
  }

  /**
   * Get logs by level
   */
  getLogsByLevel(level, limit = 50) {
    return this.logs
      .filter(log => log.level === level)
      .slice(-limit);
  }

  /**
   * Clear log history
   */
  clearLogs() {
    this.logs = [];
  }

  /**
   * Export logs for debugging
   */
  exportLogs() {
    const data = {
      sessionId: this.sessionId,
      environment: this.environment,
      logLevel: this.logLevel,
      exportedAt: new Date().toISOString(),
      logs: this.logs
    };

    return JSON.stringify(data, null, 2);
  }

  /**
   * Set up global error handling
   */
  setupGlobalErrorHandling() {
    // Handle unhandled promise rejections
    window.addEventListener("unhandledrejection", event => {
      this.error(event.reason, {
        error_type: "unhandled_promise_rejection",
        promise: event.promise
      });
    });

    // Handle uncaught errors
    window.addEventListener("error", event => {
      this.error(event.error || event.message, {
        error_type: "uncaught_error",
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      });
    });

    // Handle React error boundaries (if using React)
    if (typeof window !== "undefined") {
      window.logError = (error, errorInfo) => {
        this.error(error, {
          error_type: "react_error_boundary",
          component_stack: errorInfo?.componentStack
        });
      };
    }
  }

  /**
   * Monitor performance
   */
  startPerformanceMonitoring() {
    // Monitor page load performance
    window.addEventListener("load", () => {
      setTimeout(() => {
        if (window.performance) {
          const timing = window.performance.timing;
          const loadTime = timing.loadEventEnd - timing.navigationStart;
          
          this.logPerformance("page_load_time", loadTime, {
            dns_time: timing.domainLookupEnd - timing.domainLookupStart,
            connect_time: timing.connectEnd - timing.connectStart,
            response_time: timing.responseEnd - timing.requestStart,
            dom_parse_time: timing.domInteractive - timing.responseEnd,
            dom_ready_time: timing.domContentLoadedEventEnd - timing.navigationStart
          });
        }
      }, 0);
    });

    // Monitor long tasks
    if ("PerformanceObserver" in window) {
      try {
        const longTaskObserver = new PerformanceObserver(entries => {
          entries.getEntries().forEach(entry => {
            if (entry.duration > 50) { // Tasks longer than 50ms
              this.warn(`Long task detected: ${entry.duration}ms`, {
                performance_issue: "long_task",
                duration: entry.duration,
                start_time: entry.startTime
              });
            }
          });
        });
        
        longTaskObserver.observe({ entryTypes: ["longtask"] });
      } catch (e) {
        // PerformanceObserver not supported
      }
    }
  }
}

// Create singleton instance
const logger = new Logger();

// Set up global error handling and performance monitoring
logger.setupGlobalErrorHandling();
logger.startPerformanceMonitoring();

// Log initial page load
logger.info("Frontend application initialized", {
  environment: logger.environment,
  log_level: logger.logLevel,
  session_id: logger.sessionId,
  user_agent: navigator.userAgent,
  viewport: `${window.innerWidth}x${window.innerHeight}`
});

export default logger;
