/**
 * Frontend Security Utilities
 * Provides client-side security measures for the TovPlay frontend
 */

import logger from "./logger";

class SecurityUtils {
  constructor() {
    this.csrfToken = null;
    this.apiKey = null;
    this.rateLimitTracker = new Map();
    
    // Initialize security measures
    this.initializeSecurity();
  }

  /**
   * Initialize security measures
   */
  initializeSecurity() {
    this.setupCSRFProtection();
    this.setupXSSProtection();
    this.setupContentSecurityPolicy();
    this.monitorSecurityHeaders();
    
    logger.info("Frontend security initialized", {
      security_initialized: true,
      csrf_enabled: !!this.csrfToken,
      environment: import.meta.env.NODE_ENV
    });
  }

  /**
   * Setup CSRF protection
   */
  setupCSRFProtection() {
    // Generate CSRF token if not exists
    this.csrfToken = localStorage.getItem("csrf_token") || this.generateCSRFToken();
    localStorage.setItem("csrf_token", this.csrfToken);
  }

  /**
   * Generate CSRF token
   */
  generateCSRFToken() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, "0")).join("");
  }

  /**
   * Get CSRF token for API requests
   */
  getCSRFToken() {
    return this.csrfToken;
  }

  /**
   * Setup XSS protection through input sanitization
   */
  setupXSSProtection() {
    // Override dangerous DOM methods in development
    if (import.meta.env.NODE_ENV === "development") {
      const originalInnerHTML = Element.prototype.innerHTML;
      
      Object.defineProperty(Element.prototype, "innerHTML", {
        get: function() {
          return originalInnerHTML.call(this);
        },
        set: function(value) {
          const securityUtils = new SecurityUtils();
          if (typeof value === "string" && securityUtils.isXSSSuspicious(value)) {
            logger.warn("Potentially dangerous HTML content detected", {
              security_event: "xss_attempt",
              element: this.tagName,
              content_preview: value.substring(0, 100)
            });
          }
          originalInnerHTML.call(this, value);
        }
      });
    }
  }

  /**
   * Check for suspicious content
   */
  isXSSSuspicious(content) {
    const suspiciousPatterns = [
      /<script[^>]*>/i,
      /javascript:/i,
      /vbscript:/i,
      /onload\s*=/i,
      /onerror\s*=/i,
      /onclick\s*=/i,
      /eval\s*\(/i,
      /expression\s*\(/i
    ];

    return suspiciousPatterns.some(pattern => pattern.test(content));
  }

  /**
   * Sanitize user input
   */
  sanitizeInput(input, options = {}) {
    if (typeof input !== "string") {
      return input;
    }

    const {
      maxLength = 1000,
      allowHTML = false,
      allowLinks = true
    } = options;

    // Limit length
    let sanitized = input.substring(0, maxLength);

    if (!allowHTML) {
      // HTML escape
      sanitized = sanitized
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#x27;");
    }

    if (!allowLinks) {
      // Remove potential malicious URLs
      sanitized = sanitized.replace(/https?:\/\/[^\s]+/gi, "[URL removed]");
    }

    // Remove null bytes and control characters using character codes
    // eslint-disable-next-line no-control-regex
    sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");

    return sanitized;
  }

  /**
   * Setup Content Security Policy monitoring
   */
  setupContentSecurityPolicy() {
    // Monitor CSP violations
    document.addEventListener("securitypolicyviolation", e => {
      logger.error("Content Security Policy violation", {
        security_event: "csp_violation",
        violated_directive: e.violatedDirective,
        blocked_uri: e.blockedURI,
        document_uri: e.documentURI,
        effective_directive: e.effectiveDirective,
        original_policy: e.originalPolicy,
        referrer: e.referrer,
        status_code: e.statusCode
      });
    });
  }

  /**
   * Monitor security headers
   */
  monitorSecurityHeaders() {
    // Check if security headers are properly set
    fetch("/health.json", { method: "HEAD" })
      .then(response => {
        const headers = {
          "X-Frame-Options": response.headers.get("X-Frame-Options"),
          "X-Content-Type-Options": response.headers.get("X-Content-Type-Options"),
          "X-XSS-Protection": response.headers.get("X-XSS-Protection"),
          "Strict-Transport-Security": response.headers.get("Strict-Transport-Security"),
          "Content-Security-Policy": response.headers.get("Content-Security-Policy"),
          "Referrer-Policy": response.headers.get("Referrer-Policy")
        };

        const missingHeaders = Object.entries(headers)
          .filter(([name, value]) => !value)
          .map(([name]) => name);

        if (missingHeaders.length > 0) {
          logger.warn("Missing security headers", {
            security_issue: "missing_headers",
            missing_headers: missingHeaders
          });
        } else {
          logger.info("Security headers properly configured");
        }
      })
      .catch(error => {
        logger.error("Failed to check security headers", { error });
      });
  }

  /**
   * Secure fetch wrapper with automatic security headers
   */
  async secureFetch(url, options = {}) {
    const startTime = performance.now();
    
    // Rate limiting check
    if (this.isRateLimited(url)) {
      const error = new Error("Rate limit exceeded");
      error.status = 429;
      throw error;
    }

    // Prepare secure headers
    const secureHeaders = {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRF-Token": this.csrfToken,
      ...options.headers
    };

    // Add API key if available
    if (this.apiKey) {
      secureHeaders["X-API-Key"] = this.apiKey;
    }

    // Prepare secure options
    const secureOptions = {
      ...options,
      headers: secureHeaders,
      credentials: "same-origin", // Ensure cookies are sent for same-origin requests
      cache: "no-cache" // Prevent caching of sensitive data
    };

    // Validate URL for security
    if (!this.isValidURL(url)) {
      logger.warn("Invalid URL detected", {
        security_event: "invalid_url",
        url: url
      });
      throw new Error("Invalid URL");
    }

    try {
      const response = await fetch(url, secureOptions);
      const duration = performance.now() - startTime;

      // Log API request
      logger.logApiRequest(
        secureOptions.method || "GET",
        url,
        response.status,
        duration
      );

      // Check for security headers in response
      this.validateResponseHeaders(response);

      return response;
    } catch (error) {
      const duration = performance.now() - startTime;
      
      logger.error("Secure fetch failed", {
        url,
        error: error.message,
        duration
      });
      
      throw error;
    }
  }

  /**
   * Check if URL is valid and safe
   */
  isValidURL(url) {
    try {
      const parsedURL = new URL(url, window.location.origin);
      
      // Only allow HTTPS in production
      if (import.meta.env.NODE_ENV === "production" && parsedURL.protocol !== "https:") {
        return false;
      }

      // Check allowed origins
      const allowedOrigins = [
        window.location.origin,
        import.meta.env.VITE_API_BASE_URL
      ].filter(Boolean);

      return allowedOrigins.some(origin => parsedURL.origin === origin);
    } catch {
      return false;
    }
  }

  /**
   * Validate security headers in response
   */
  validateResponseHeaders(response) {
    const securityHeaders = [
      "X-Content-Type-Options",
      "X-Frame-Options",
      "X-XSS-Protection"
    ];

    const missingHeaders = securityHeaders.filter(header => 
      !response.headers.get(header)
    );

    if (missingHeaders.length > 0) {
      logger.warn("API response missing security headers", {
        security_issue: "missing_response_headers",
        missing_headers: missingHeaders,
        url: response.url
      });
    }
  }

  /**
   * Simple rate limiting
   */
  isRateLimited(url) {
    const now = Date.now();
    const key = new URL(url, window.location.origin).pathname;
    
    if (!this.rateLimitTracker.has(key)) {
      this.rateLimitTracker.set(key, { requests: [], burst: [] });
    }

    const tracker = this.rateLimitTracker.get(key);
    
    // Clean old requests
    const hourAgo = now - 3600000; // 1 hour
    const minuteAgo = now - 60000;  // 1 minute
    
    tracker.requests = tracker.requests.filter(time => time > hourAgo);
    tracker.burst = tracker.burst.filter(time => time > minuteAgo);

    // Check limits (100/hour, 20/minute)
    if (tracker.requests.length >= 100 || tracker.burst.length >= 20) {
      logger.warn("Rate limit exceeded", {
        security_event: "rate_limit_exceeded",
        endpoint: key,
        hourly_requests: tracker.requests.length,
        minute_requests: tracker.burst.length
      });
      return true;
    }

    // Add current request
    tracker.requests.push(now);
    tracker.burst.push(now);
    
    return false;
  }

  /**
   * Set API key for authenticated requests
   */
  setAPIKey(key) {
    this.apiKey = key;
    logger.info("API key configured for secure requests");
  }

  /**
   * Clear sensitive data
   */
  clearSecurityData() {
    this.csrfToken = null;
    this.apiKey = null;
    localStorage.removeItem("csrf_token");
    sessionStorage.clear();
    
    logger.info("Security data cleared");
  }

  /**
   * Validate form data before submission
   */
  validateFormData(formData, schema = {}) {
    const errors = {};

    Object.entries(schema).forEach(([field, rules]) => {
      const value = formData[field];

      if (rules.required && !value) {
        errors[field] = "This field is required";
        return;
      }

      if (value && rules.maxLength && value.length > rules.maxLength) {
        errors[field] = `Maximum length is ${rules.maxLength}`;
      }

      if (value && rules.pattern && !rules.pattern.test(value)) {
        errors[field] = "Invalid format";
      }

      if (value && rules.sanitize) {
        formData[field] = this.sanitizeInput(value, rules.sanitize);
      }
    });

    if (Object.keys(errors).length > 0) {
      logger.warn("Form validation failed", {
        security_event: "form_validation_failed",
        errors: Object.keys(errors)
      });
    }

    return { isValid: Object.keys(errors).length === 0, errors };
  }

  /**
   * Generate secure random string
   */
  generateSecureRandom(length = 32) {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    
    return Array.from(array, byte => chars[byte % chars.length]).join("");
  }
}

// Create singleton instance
const security = new SecurityUtils();

export default security;

// Export individual functions for convenience
export const {
  sanitizeInput,
  secureFetch,
  validateFormData,
  generateSecureRandom,
  getCSRFToken
} = security;
