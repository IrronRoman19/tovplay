import { GoogleOAuthProvider } from "@react-oauth/google";
import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { AnalyticsProvider } from "use-analytics";

import App from "@/App.jsx";
import store from "@/stores/store.js";
import analytics from "@/utils/analytics";
import { LanguageProvider } from "@/components/lib/LanguageContext";

import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      <Provider store={store}>
        <AnalyticsProvider instance={analytics}>
          <LanguageProvider>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </LanguageProvider>
        </AnalyticsProvider>
      </Provider>
    </GoogleOAuthProvider>
  </React.StrictMode>
);
