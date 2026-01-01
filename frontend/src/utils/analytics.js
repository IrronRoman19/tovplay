import googleAnalytics from "@analytics/google-analytics";
import Analytics from "analytics";

const analytics = Analytics({
  app: "TovPlay",
  plugins: [
    googleAnalytics({
      measurementIds: ["G-PFFJY1WVL9"]
    })
  ]
});

export default analytics;
