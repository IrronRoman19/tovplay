// src/components/PublicRoute.jsx
import { Navigate } from "react-router-dom";
import LocalStorage from "@/utils/localStorage";

// Minimal JWT decoder (no external deps)
function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(decoded)));
  } catch {
    return null;
  }
}

function isTokenValid(token) {
  if (!token) {
    return false;
  }
  const payload = decodeJwt(token);
  if (!payload || !payload.exp) {
    return false;
  }
  // exp is in seconds since epoch
  const now = Math.floor(Date.now() / 1000);
  return now < payload.exp;
}

export default function PublicRoute({ children }) {
  // Try both LocalStorage helper and direct localStorage for robustness
  const token =
    LocalStorage?.authToken?.get?.() || localStorage.getItem("authToken");
  if (isTokenValid(token)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
