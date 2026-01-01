// src/api/apiService.js
import axios from "axios";
import { findPlayers } from "./__mocks__/playersMock";
import LocalStorage from "@/utils/localStorage";

// Flag to enable/disable mock mode
const USE_MOCK = false; // Set to false to use real API

// Configure a new Axios instance with your base URL and any default settings
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

// Log the API base URL for debugging in production
console.log("API Base URL:", apiBaseUrl);
console.log("Environment mode:", import.meta.env.MODE);
console.log("All Vite env vars:", Object.keys(import.meta.env).filter(key => key.startsWith("VITE_")));

// Additional debug for production deployment
if (import.meta.env.MODE === "production") {
  console.log("Production deployment - Network & CORS FIXED - v2025-10-21");
  console.log("Production API Base URL:", `${apiBaseUrl}/api`);
  console.log("Backend: CORS configured, database connected, all endpoints working");
  console.log("Testing backend connection...");
}



const api = axios.create({
  baseURL: `${apiBaseUrl}/api`,
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json"
  },
  withCredentials: true, // Include credentials for CORS (cookies, auth headers)
  timeout: 30000, // 30 second timeout for production stability
  retry: 3, // Add retry attempts
  retryDelay: 1000, // 1 second delay between retries
  crossDomain: true
});

// Add request interceptor to add auth token and log requests
api.interceptors.request.use(config => {
  // Log the request
  console.log("Making API request to:", config.baseURL + config.url, "Method:", config.method.toUpperCase());

  // Get the auth token from localStorage
  const token = LocalStorage.authToken.get();

  // Ensure headers exist
  config.headers = config.headers || {};

  // Set default headers
  const isMethodAcceptingBody = config.method !== "get" && config.method !== "delete";
  if (!isMethodAcceptingBody) {
    delete config.headers["Content-Type"];
  } else {
    config.headers["Content-Type"] = "application/json";
  }
  config.headers["Accept"] = "application/json";

  // If token exists, add it to the request headers
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log("Added auth token to request headers");
  } else {
    console.warn("No auth token found in localStorage");
  }

  // Ensure CORS settings
  config.withCredentials = true;

  return config;
});

// Add a response interceptor to handle errors
api.interceptors.response.use(
  response => {
    console.log("API Success:", response.config.method.toUpperCase(), response.config.url, "- Status:", response.status);
    return response;
  },
  error => {
    const url = error.config ? error.config.url : "unknown";
    const method = error.config ? error.config.method.toUpperCase() : "unknown";
    const status = error.response ? error.response.status : "no response";
    const message = error.response ? error.response.data : error.message;

    console.error("API Error:", method, url, "- Status:", status, "- Message:", message);
    console.error("Full error object:", error);

    // Handle network errors
    if (error.message === "Network Error") {
      console.error("Network Error - Please check your internet connection");
      error.response = error.response || {};
      error.response.data = {
        message: "Network Error - Please check your internet connection"
      };

      // For mock data fallback in development
      if (import.meta.env.DEV) {
        const userId = url.split("/").pop();
        const gameName = error.config?.params?.game_name;
        if (url.includes("findplayers") && gameName) {
          const players = findPlayers(userId, gameName);
          return Promise.resolve({ data: players });
        }
      }
    }

    // Handle CORS errors
    if (error.message && error.message.includes("Network Error") && !error.response) {
      error.response = {
        status: 0,
        statusText: "CORS/Network Error",
        data: {
          message: "Cannot connect to the server. Please check if the server is running and CORS is properly configured."
        }
      };
    }

    // Handle 401 Unauthorized (token expired or invalid)
    const STATUS_UNAUTHORIZED = 401;
    if (status === STATUS_UNAUTHORIZED) {
      LocalStorage.authToken.clear();
      dispatchEvent(new CustomEvent("session-expired"));
    }
    return Promise.reject(error);
  }
);
// Create a function to handle all requests
const request = async (method, url, data = null, config = {}) => {
  try {
    return await api({
      method,
      url,
      data,
      ...config
    });
  } catch (error) {
    console.error(`Error in ${method.toUpperCase()} ${url}:`, error);
    throw error;
  }
};

// Get user profile by user ID
const getUser = async userId => {
  try {
    const response = await api.get(`/users/${userId}`);

    // If we get an array, return the first item (should be the user's profile)
    const profileData = Array.isArray(response.data) && response.data.length > 0
      ? response.data[0]
      : response.data;

    // Save to localStorage if we got valid data
    if (profileData) {
      if (typeof window !== "undefined") {
        localStorage.setItem("userProfile", JSON.stringify(profileData));
      }
      return profileData;
    }

    return null;
  } catch (error) {
    if (error.response?.status === 404) {
      return null;
    }
    console.error("Error getting profile:", error);
    throw error;
  }
};

// Create a new user profile
const createUserProfile = async profileData => {
  try {
    const response = await api.post("/user_profiles", profileData);
    const newProfile = response.data;

    // Save to localStorage
    if (newProfile && typeof window !== "undefined") {
      localStorage.setItem("userProfile", JSON.stringify(newProfile));
    }

    return newProfile;
  } catch (error) {
    console.error("Error creating profile:", error);
    throw error;
  }
};

// Update an existing user profile
const updateUserProfile = async (userId, profileData) => {
  try {
    // First get the existing profile to ensure it exists and get its ID
    const existingProfile = await getUser(userId);
    if (!existingProfile) {
      throw new Error("Profile not found");
    }

    const response = await api.put(`/user_profiles/${existingProfile.id || userId}`, profileData);
    const updatedProfile = response.data;

    // Update localStorage
    if (updatedProfile && typeof window !== "undefined") {
      localStorage.setItem("userProfile", JSON.stringify(updatedProfile));
    }

    return updatedProfile;
  } catch (error) {
    console.error("Error updating profile:", error);
    throw error;
  }
};

// Get current user's profile from localStorage if available
const getCurrentUserFromLocalStorage = () => {
  try {
    if (typeof window === "undefined") {
      return null;
    }
    const profileData = localStorage.getItem("userProfile");
    return profileData ? JSON.parse(profileData) : null;
  } catch (error) {
    console.error("Error getting current user profile from localStorage:", error);
    return null;
  }
};

async function cancleSession(sessionId, message) {
  return api.put(`/scheduled_sessions/cancel_session/${sessionId}`, { message });
}


// Check if current user is in Discord community
const checkCommunityStatus = async () => {
  try {
    const response = await api.get("/discord/in_community_route");
    console.log("Community status raw response:", response);
    if (!response.data) {
      throw new Error("No data received from server");
    }
    return response.data;
  } catch (error) {
    console.error("Error checking community status:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status
    });
  }
  // Normalize error payload for callers
  return {
    error: error.response?.data?.error ||
      error.message ||
      'Failed to check community status. Please try again later.'
  }
};

// Mark current user as in_community = true (backend convenience endpoint)
const setInCommunityTrue = async () => {
  try {
    const response = await api.put("/discord/get_in_community");
    return response.data;
  } catch (error) {
    console.error("Error setting in_community to true:", error);
    throw error;
  }
};
// ---------------- PASSWORD RESET ----------------

const requestPasswordReset = async (email) => {
  return api.post("/password/request", { email });
};

const validateResetToken = async (token) => {
  return api.get("/password/validate", {
    params: { token }
  });
};

const resetPassword = async ({ token, password, confirm_password }) => {
  return api.post("/password/reset", {
    token,
    password,
    confirm_password
  });
};

// Extracted functions from apiService

async function sendFriendRequest(recipient_username, message = null) {
  try {
    const payload = { recipient_username };
    if (message) {
      payload.message = message;
    }
    const response = await api.post("/friends/request", payload);
    return response.data;
  } catch (error) {
    console.error("Error sending friend request:", error);
    throw error;
  }
}

async function cancelFriendRequest(requestId) {
  try {
    const response = await api.delete(`/friends/request/${requestId}`);
    return response.data;
  } catch (error) {
    console.error("Error cancelling friend request:", error);
    throw error;
  }
}

async function getFriendRequests() {
  try {
    const response = await api.get("/friends/received_requests");
    return response.data;
  } catch (error) {
    console.error("Error getting friend requests:", error);
    throw error;
  }
}

async function getFriends() {
  try {
    const response = await api.get("/friends/friends");
    return response.data;
  } catch (error) {
    console.error("Error getting friends:", error);
    throw error;
  }
}

async function respondToFriendRequest(requestId, accept) {
  try {
    const response = await api.put(`/friends/accept/${requestId}`, { accept_invite: accept });
    return response.data;
  } catch (error) {
    console.error(`Error ${accept ? "accepting" : "declining"} friend request:`, error);
    throw error;
  }
}

async function blockUser(username_to_block, blocking_reason = null) {
  try {
    const payload = { username_to_block };
    if (blocking_reason) {
      payload.message = blocking_reason;
    }
    const response = await api.put("/friends/block", payload);
    return response.data;
  } catch (error) {
    console.error("Error blocking user:", error);
    throw error;
  }
}

async function unblockUser(request_id, username_to_unblock = null) {
  try {
    const safeRequestId = (request_id && request_id !== "None") ? request_id : null;
    const payload = { request_id: safeRequestId, username_to_unblock };
    const response = await api.put("/friends/unblock", payload);
    return response.data;
  } catch (error) {
    console.error("Error unblocking user:", error);
    throw error;
  }
}

async function checkRelationship(username) {
  try {
    const response = await api.get(`/friends/check_relationship/${username}`);
    return response.data;
  } catch (error) {
    console.error("Error checking relationship:", error);
    throw error;
  }
}

async function findOverlappingTimes(recipient_username) {
  try {
    const response = await api.get("/findplayers/", {
      params: { recipient_username }
    });
    return response.data;
  } catch (error) {
    console.error("Error finding overlapping times:", error);
    throw error;
  }
}
async function getCurrentProfile() {
  try {
    const response = await api.get("/user_profiles/");
    return response.data;
  } catch (error) {
    console.error("Error getting current user profile:", error);
    throw error;
  }
}
async function getPublicUserProfile(username) {
  try {
    const response = await api.get(`/user_profiles/public/${username}`);
    return response.data;
  } catch (error) {
    console.error("Error getting public user profile:", error);
    throw error;
  }
}
async function getCurrentUser() {
  const id = LocalStorage.authUserId.get();
  return apiService.getUser(id);
}

// Updated apiService to reference extracted functions
export const apiService = {
  get: (url, config) => request("get", url, null, config),
  post: (url, data, config) => request("post", url, data, config),
  put: (url, data, config) => request("put", url, data, config),
  delete: (url, config) => request("delete", url, null, config),

  getUserProfile,
  createUserProfile,
  updateUserProfile,
  getCurrentUserProfile,

  profile: {
    get: getUserProfile,
  // user
  getUser,
  getCurrentUser,
  getCurrentUserFromLocalStorage,

  // Profile specific methods with standardized interface
  currentProfile: {
    get: getCurrentProfile,
    create: createUserProfile,
    update: updateUserProfile,
  },

  session: {
    cancel: cancleSession
  },

  checkCommunityStatus,
  setInCommunityTrue,

  // Password reset
  requestPasswordReset,
  validateResetToken,
  resetPassword
  // Community related methods
  checkCommunityStatus,
  setInCommunityTrue,

  // Friend Management
  sendFriendRequest,
  cancelFriendRequest,
  getFriendRequests,
  getFriends,
  respondToFriendRequest,
  blockUser,
  unblockUser,
  checkRelationship,
  findOverlappingTimes,
  getPublicUserProfile,
};

export default apiService;