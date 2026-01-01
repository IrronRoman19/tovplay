/**
 * Frontend Monitoring and Observability utilities
 * Production-ready monitoring for performance, errors, and user analytics
 */

import React from "react";

class MonitoringService {
  constructor() {
    this.isProduction = process.env.NODE_ENV === "production";
    this.sessionId = this.generateSessionId();
    this.errorQueue = [];
    this.performanceMetrics = {};
    
    // Initialize monitoring
    this.initializeErrorTracking();
    this.initializePerformanceMonitoring();
    this.initializeUserAnalytics();
  }

  generateSessionId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // Error Tracking
  initializeErrorTracking() {
    window.addEventListener("error", event => {
      this.trackError({
        type: "javascript_error",
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent,
        sessionId: this.sessionId
      });
    });

    window.addEventListener("unhandledrejection", event => {
      this.trackError({
        type: "unhandled_promise_rejection",
        message: event.reason?.message || "Unhandled promise rejection",
        stack: event.reason?.stack,
        timestamp: new Date().toISOString(),
        url: window.location.href,
        sessionId: this.sessionId
      });
    });
  }

  trackError(errorDetails) {
    console.error("Error tracked:", errorDetails);
    
    this.errorQueue.push(errorDetails);
    
    // Send errors in production
    if (this.isProduction) {
      this.sendToEndpoint("/api/monitoring/errors", errorDetails);
    }
    
    // Send critical errors immediately
    if (errorDetails.type === "critical" || errorDetails.message.includes("ChunkLoadError")) {
      this.flushErrors();
    }
  }

  // Performance Monitoring
  initializePerformanceMonitoring() {
    // Web Vitals tracking
    this.trackWebVitals();
    
    // Navigation timing
    window.addEventListener("load", () => {
      setTimeout(() => this.trackNavigationTiming(), 0);
    });

    // Resource timing
    this.trackResourceTiming();
  }

  trackWebVitals() {
    // Largest Contentful Paint (LCP)
    new PerformanceObserver(entryList => {
      const entries = entryList.getEntries();
      const lastEntry = entries[entries.length - 1];
      
      this.performanceMetrics.lcp = lastEntry.startTime;
      this.sendMetric("web_vitals_lcp", lastEntry.startTime);
    }).observe({ entryTypes: ["largest-contentful-paint"] });

    // First Input Delay (FID)
    new PerformanceObserver(entryList => {
      const firstInput = entryList.getEntries()[0];
      if (firstInput) {
        const fid = firstInput.processingStart - firstInput.startTime;
        this.performanceMetrics.fid = fid;
        this.sendMetric("web_vitals_fid", fid);
      }
    }).observe({ entryTypes: ["first-input"] });

    // Cumulative Layout Shift (CLS)
    let clsScore = 0;
    new PerformanceObserver(entryList => {
      for (const entry of entryList.getEntries()) {
        if (!entry.hadRecentInput) {
          clsScore += entry.value;
        }
      }
      this.performanceMetrics.cls = clsScore;
      this.sendMetric("web_vitals_cls", clsScore);
    }).observe({ entryTypes: ["layout-shift"] });
  }

  trackNavigationTiming() {
    const navigation = performance.getEntriesByType("navigation")[0];
    if (navigation) {
      const metrics = {
        dns_lookup: navigation.domainLookupEnd - navigation.domainLookupStart,
        tcp_connect: navigation.connectEnd - navigation.connectStart,
        request_response: navigation.responseEnd - navigation.requestStart,
        dom_processing: navigation.domContentLoadedEventEnd - navigation.responseEnd,
        total_load_time: navigation.loadEventEnd - navigation.fetchStart
      };

      Object.entries(metrics).forEach(([key, value]) => {
        this.sendMetric(`navigation_${key}`, value);
      });
    }
  }

  trackResourceTiming() {
    new PerformanceObserver(entryList => {
      const entries = entryList.getEntries();
      
      entries.forEach(entry => {
        // Track slow resources
        if (entry.duration > 1000) {
          this.sendMetric("slow_resource", {
            name: entry.name,
            duration: entry.duration,
            size: entry.transferSize,
            type: entry.initiatorType
          });
        }
      });
    }).observe({ entryTypes: ["resource"] });
  }

  // User Analytics
  initializeUserAnalytics() {
    // Page views
    this.trackPageView();
    
    // User interactions
    document.addEventListener("click", this.trackUserInteraction.bind(this));
    
    // Session duration
    this.startTime = Date.now();
    window.addEventListener("beforeunload", () => {
      const sessionDuration = Date.now() - this.startTime;
      this.sendMetric("session_duration", sessionDuration);
    });
  }

  trackPageView() {
    const pageData = {
      url: window.location.href,
      title: document.title,
      referrer: document.referrer,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      screen: {
        width: screen.width,
        height: screen.height
      }
    };

    this.sendToEndpoint("/api/monitoring/pageviews", pageData);
  }

  trackUserInteraction(event) {
    // Track meaningful interactions
    const targetTag = event.target.tagName.toLowerCase();
    const meaningfulTags = ["button", "a", "input", "select", "textarea"];
    
    if (meaningfulTags.includes(targetTag)) {
      const interactionData = {
        type: "click",
        target: targetTag,
        id: event.target.id,
        className: event.target.className,
        text: event.target.textContent?.substr(0, 100),
        timestamp: new Date().toISOString(),
        sessionId: this.sessionId
      };

      // Debounced sending
      clearTimeout(this.interactionTimeout);
      this.interactionTimeout = setTimeout(() => {
        this.sendToEndpoint("/api/monitoring/interactions", interactionData);
      }, 1000);
    }
  }

  // Custom metrics
  trackCustomEvent(eventName, data = {}) {
    const eventData = {
      event: eventName,
      data,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      url: window.location.href
    };

    this.sendToEndpoint("/api/monitoring/events", eventData);
  }

  // API response monitoring
  trackApiCall(url, method, duration, status, error = null) {
    const apiData = {
      url,
      method,
      duration,
      status,
      error: error?.message,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId
    };

    this.sendToEndpoint("/api/monitoring/api-calls", apiData);
  }

  // Utility methods
  sendMetric(name, value) {
    if (this.isProduction) {
      this.sendToEndpoint("/api/monitoring/metrics", { name, value, timestamp: new Date().toISOString() });
    }
  }

  async sendToEndpoint(endpoint, data) {
    try {
      await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });
    } catch (error) {
      // Fail silently in monitoring to avoid cascading errors
      console.warn("Monitoring endpoint failed:", error);
    }
  }

  flushErrors() {
    if (this.errorQueue.length > 0 && this.isProduction) {
      this.sendToEndpoint("/api/monitoring/errors/batch", {
        errors: this.errorQueue,
        sessionId: this.sessionId
      });
      this.errorQueue = [];
    }
  }

  // Health check
  getHealthMetrics() {
    return {
      sessionId: this.sessionId,
      errorCount: this.errorQueue.length,
      performance: this.performanceMetrics,
      memory: performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null,
      connection: navigator.connection ? {
        type: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      } : null
    };
  }
}

// Create global monitoring instance
const monitoring = new MonitoringService();

// Export for use in components
export default monitoring;

// Helper function for React components
export const withMonitoring = WrappedComponent => {
  return function MonitoredComponent(props) {
    React.useEffect(() => {
      monitoring.trackCustomEvent("component_mount", {
        component: WrappedComponent.name
      });

      return () => {
        monitoring.trackCustomEvent("component_unmount", {
          component: WrappedComponent.name
        });
      };
    }, []);

    return <WrappedComponent {...props} />;
  };
};
