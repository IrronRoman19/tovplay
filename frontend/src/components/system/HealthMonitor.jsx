/**
 * Health Monitor Component
 * Displays system health status and provides debugging information
 */

import { ChevronDown, ChevronUp, RefreshCw, AlertCircle, CheckCircle, Clock, XCircle } from "lucide-react";
import { useState, useEffect } from "react";
import healthService from "../../utils/healthService";
import { Alert, AlertDescription } from "../ui/alert";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../ui/collapsible";

const StatusIcon = ({ status }) => {
  const iconProps = { size: 16 };

  switch (status) {
    case "healthy":
      return <CheckCircle className="text-green-500" {...iconProps} />;
    case "degraded":
      return <AlertCircle className="text-yellow-500" {...iconProps} />;
    case "timeout":
      return <Clock className="text-orange-500" {...iconProps} />;
    case "unhealthy":
    case "error":
      return <XCircle className="text-red-500" {...iconProps} />;
    default:
      return <AlertCircle className="text-gray-500" {...iconProps} />;
  }
};

const StatusBadge = ({ status }) => {
  const variants = {
    healthy: "default",
    degraded: "secondary",
    timeout: "secondary",
    unhealthy: "destructive",
    error: "destructive",
    unknown: "outline"
  };

  const colors = {
    healthy: "bg-green-100 text-green-800",
    degraded: "bg-yellow-100 text-yellow-800",
    timeout: "bg-orange-100 text-orange-800",
    unhealthy: "bg-red-100 text-red-800",
    error: "bg-red-100 text-red-800",
    unknown: "bg-gray-100 text-gray-800"
  };

  return (
    <Badge variant={variants[status]} className={colors[status]}>
      <StatusIcon status={status} />
      <span className="ml-1 capitalize">{status}</span>
    </Badge>
  );
};

const HealthMonitor = ({ showDetailed = false, className = "" }) => {
  const [healthData, setHealthData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const loadHealthData = async () => {
    setIsLoading(true);
    try {
      const data = showDetailed
        ? await healthService.getDetailedHealth()
        : healthService.getHealth();
      setHealthData(data);
    } catch (error) {
      healthService.logError(error, { source: "HealthMonitor.loadHealthData" });
      setHealthData({
        status: "error",
        error: error.message,
        timestamp: new Date().toISOString()
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHealthData();
  }, [showDetailed]);

  useEffect(() => {
    let interval;
    if (autoRefresh) {
      interval = setInterval(loadHealthData, 30000); // Refresh every 30 seconds
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [autoRefresh, showDetailed]);

  useEffect(() => {
    const handleHealthUpdate = event => {
      setHealthData(event.detail);
    };

    window.addEventListener("healthUpdate", handleHealthUpdate);
    return () => window.removeEventListener("healthUpdate", handleHealthUpdate);
  }, []);

  if (!healthData) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2">
            <RefreshCw className="animate-spin h-4 w-4" />
            <span>Loading health status...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const hasError = healthData.status === "error" || healthData.overall_status === "unhealthy";

  return (
    <div className={className}>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">System Health</CardTitle>
            <div className="flex items-center space-x-2">
              <StatusBadge status={healthData.overall_status || healthData.status} />
              <Button
                variant="outline"
                size="sm"
                onClick={loadHealthData}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Service:</span> {healthData.service}
              </div>
              <div>
                <span className="font-medium">Environment:</span> {healthData.environment}
              </div>
              <div>
                <span className="font-medium">Version:</span> {healthData.version}
              </div>
              <div>
                <span className="font-medium">Uptime:</span>{" "}
                {healthData.uptime_seconds ? `${Math.floor(healthData.uptime_seconds / 60)}m` : "N/A"}
              </div>
            </div>

            {/* Error Alert */}
            {hasError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {healthData.error || "System health check failed"}
                </AlertDescription>
              </Alert>
            )}

            {/* Detailed Health Information */}
            {showDetailed && healthData.checks && (
              <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
                <CollapsibleTrigger asChild>
                  <Button variant="outline" className="w-full">
                    <span>Detailed Health Information</span>
                    {isExpanded ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
                  </Button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-4 mt-4">
                  {/* Frontend Health */}
                  {healthData.checks.frontend && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-md flex items-center">
                          <StatusIcon status={healthData.checks.frontend.status} />
                          <span className="ml-2">Frontend</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 text-sm">
                          {healthData.checks.frontend.browser && (
                            <div>
                              <strong>Browser:</strong> {healthData.checks.frontend.browser.platform} -
                              {healthData.checks.frontend.browser.online ? " Online" : " Offline"}
                            </div>
                          )}
                          {healthData.checks.frontend.performance?.memory && (
                            <div>
                              <strong>Memory:</strong> {healthData.checks.frontend.performance.memory.used_mb}MB used
                            </div>
                          )}
                          {healthData.checks.frontend.storage && (
                            <div>
                              <strong>Storage:</strong>
                              {" Local: " + (healthData.checks.frontend.storage.local_storage_available ? "✓" : "✗")}
                              {" Session: " + (healthData.checks.frontend.storage.session_storage_available ? "✓" : "✗")}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Backend Health */}
                  {healthData.checks.backend && (
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-md flex items-center">
                          <StatusIcon status={healthData.checks.backend.status} />
                          <span className="ml-2">Backend API</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 text-sm">
                          <div>
                            <strong>Status:</strong> {healthData.checks.backend.backend_status || "Unknown"}
                          </div>
                          {healthData.checks.backend.response_time_ms && (
                            <div>
                              <strong>Response Time:</strong> {healthData.checks.backend.response_time_ms}ms
                            </div>
                          )}
                          {healthData.checks.backend.error && (
                            <div className="text-red-600">
                              <strong>Error:</strong> {healthData.checks.backend.error}
                            </div>
                          )}
                          <div>
                            <strong>Last Check:</strong> {new Date(healthData.checks.backend.last_check).toLocaleTimeString()}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Response Time */}
                  {healthData.response_time_ms && (
                    <div className="text-sm text-gray-600">
                      Health check completed in {healthData.response_time_ms}ms
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            )}

            {/* Controls */}
            <div className="flex items-center justify-between pt-2 border-t">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="auto-refresh"
                  checked={autoRefresh}
                  onChange={e => setAutoRefresh(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="auto-refresh" className="text-sm">
                  Auto-refresh (30s)
                </label>
              </div>
              <div className="text-xs text-gray-500">
                Last updated: {new Date(healthData.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HealthMonitor;
