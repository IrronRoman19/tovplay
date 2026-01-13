import googleAnalytics from "@analytics/google-analytics";
import Analytics from "analytics";

const isAnalyticsEnabled = import.meta.env.VITE_ENABLE_ANALYTICS === "true";

const analytics = Analytics({
  app: "TovPlay",
  plugins: isAnalyticsEnabled ? [
    googleAnalytics({
      measurementIds: ["G-PFFJY1WVL9"]
    })
  ] : []
});

export default analytics;
