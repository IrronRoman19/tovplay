import { createClient } from "@base44/sdk";
// import { getAccessToken } from '@base44/sdk/utils/auth-utils';

// Create a client with authentication required
export const base44 = createClient({
  appId: "6888a3356e9743b99fd8b2ea", 
  requiresAuth: false, // Ensure authentication is required for all operations
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:5001"
});
