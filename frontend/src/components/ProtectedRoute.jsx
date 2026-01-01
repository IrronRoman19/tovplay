import { Navigate } from "react-router-dom";
import LocalStorage from "@/utils/localStorage";

// Minimal JWT decoder (no external deps)
function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const decoded = atob(payload.replaceAll("-", "+").replaceAll("_", "/"));
    // Use TextDecoder to avoid deprecated escape()
    const utf8Arr = Uint8Array.from(decoded, c => c.charCodeAt(0));
    const jsonStr = new TextDecoder("utf-8").decode(utf8Arr);
    return JSON.parse(jsonStr);
  } catch {
    return null;
  }
}
export default function ProtectedRoute({ children }) {
  const token = LocalStorage.authToken.get();
  const payload = token ? decodeJwt(token) : null;

  if (!token) {
    LocalStorage.authToken.clear();
    return <Navigate to="/login" replace />;
  }

  if (!payload || !payload.exp) {
    LocalStorage.authToken.clear();
    return <Navigate to="/login" replace />;
  }

  const now = Math.floor(Date.now() / 1000);

  if (now >= payload.exp) {
    LocalStorage.authToken.clear();
    return <Navigate to="/login" replace />;
  }

  return children;
}
