// =============================================================================
// TovPlay Frontend Redux Store - Consolidated
// =============================================================================

import { configureStore, createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiService } from "@/api";
import { LocalStorage } from "@/utils";
import axios from "@/lib";

// =============================================================================
// Auth Slice
// =============================================================================
export const loginUser = createAsyncThunk(
  "auths/loginUser",
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const response = await apiService.post(
        "/users/login", { Email: username, Password: password });
      if (response.data && response.data.jwt_token) {
        const userProfile = await apiService.getUser(response.data.user_id);
        return {
          user: response.data.user_id,
          token: response.data.jwt_token,
          isLoggedIn: true,
          isDiscordRegistered: userProfile?.is_discord_registered || false
        };
      } else {
        return rejectWithValue("Didn't receive token.");
      }
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || "Login failed.");
    }
  }
);

function setAuthState(state, action) {
  state.user = action.payload.user;
  state.isLoggedIn = action.payload.isLoggedIn;
  state.token = action.payload.token;
  state.isDiscordRegistered = action.payload.isDiscordRegistered;
  if (state.token) {
    LocalStorage.authToken.set(state.token);
    LocalStorage.authUserId.set(state.user);
    LocalStorage.authisLoggedIn.set(true);
    LocalStorage.isDiscordRegistered.set(state.isDiscordRegistered);
  }
}

function clearAuthState(state) {
  state.user = null;
  state.isLoggedIn = false;
  state.token = null;
  state.isDiscordRegistered = false;
  LocalStorage.authToken.clear();
  LocalStorage.authUserId.clear();
  LocalStorage.authisLoggedIn.clear();
  LocalStorage.isDiscordRegistered.clear();
  sessionStorage.removeItem('showCommunityDialog');
  sessionStorage.removeItem('discordInviteLink');
  localStorage.removeItem("discordUserInfo");
}

const authSlice = createSlice({
  name: "auths",
  initialState: {
    user: LocalStorage.authUserId.get(),
    token: LocalStorage.authToken.get(),
    isLoggedIn: LocalStorage.authisLoggedIn.get(),
    isDiscordRegistered: LocalStorage.isDiscordRegistered.get()
  },
  reducers: {
    loginSuccess: setAuthState,
    logout: clearAuthState
  },
  extraReducers: builder => {
    builder
      .addCase(loginUser.fulfilled, setAuthState)
      .addCase(loginUser.rejected, (state, action) => {
        clearAuthState(state);
        state.error = action.payload;
      });
  }
});

export const { loginSuccess, logout } = authSlice.actions;

// =============================================================================
// Notifications Slice
// =============================================================================
export const fetchNotifications = createAsyncThunk(
  "notifications/fetchNotifications",
  async (_, { rejectWithValue }) => {
    try {
      const res = await apiService.get("/notifications/");
      return res.data.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } catch {
      return rejectWithValue("Failed to fetch notifications");
    }
  }
);

export const markNotificationsAsRead = createAsyncThunk(
  "notifications/markNotificationsAsRead",
  async (ids, { rejectWithValue }) => {
    try {
      await apiService.post("/notifications/mark_read", ids);
      return ids;
    } catch {
      return rejectWithValue("Failed to mark notifications as read");
    }
  }
);

const notificationsSlice = createSlice({
  name: "notifications",
  initialState: {
    notifications: [],
    unreadCount: 0,
    loading: false,
    error: null
  },
  reducers: {
    receiveNotification(state, action) {
      const n = action.payload;
      if (n.type === "session_cancellation" && typeof n.cancellationReason === "string") {
        state.notifications = [{ ...n, cancellationReason: n.cancellationReason }, ...state.notifications];
      } else {
        state.notifications = [n, ...state.notifications];
      }
      if (!n.is_read) {
        state.unreadCount += 1;
      }
    },
    markAllAsReadLocal(state) {
      state.notifications = state.notifications.map(n => ({ ...n, is_read: true }));
      state.unreadCount = 0;
    }
  },
  extraReducers: builder => {
    builder
      .addCase(fetchNotifications.pending, state => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchNotifications.fulfilled, (state, action) => {
        state.notifications = action.payload;
        state.unreadCount = action.payload.filter(n => !n.is_read).length;
        state.loading = false;
      })
      .addCase(fetchNotifications.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || "Unknown error";
      })
      .addCase(markNotificationsAsRead.fulfilled, (state, action) => {
        const ids = action.payload;
        state.notifications = state.notifications.map(n =>
          ids.includes(n.id) ? { ...n, is_read: true } : n
        );
        state.unreadCount = state.notifications.filter(n => !n.is_read).length;
      });
  }
});

export const { receiveNotification, markAllAsReadLocal } = notificationsSlice.actions;

// =============================================================================
// Profile Slice
// =============================================================================
export const checkUserNameAvailability = createAsyncThunk(
  "profile/checkUserNameAvailability",
  async (username, { rejectWithValue }) => {
    if (username && username.length >= 3) {
      try {
        const response = await axios.post("/api/users/username-availability", { "Username": username });
        return response.data;
      } catch (error) {
        if (error.response) {
          return rejectWithValue(error.response.data);
        } else if (error.request) {
          return rejectWithValue({ message: "Network error" });
        } else {
          return rejectWithValue({ message: error.message });
        }
      }
    } else {
      return rejectWithValue({ message: "Username too short" });
    }
  }
);

const profileSlice = createSlice({
  name: "profile",
  initialState: {
    username: "",
    email: "",
    password: "",
    isChecking: false,
    isAvailable: null,
    usernameLastChecked: "",
    userId: null
  },
  reducers: {
    setEmailAndPassword: (state, action) => {
      state.email = action.payload.email;
      state.password = action.payload.password;
    },
    setUsername: (state, action) => {
      state.username = action.payload.username;
    },
    setUserId: (state, action) => {
      state.userId = action.payload.userId;
    },
    setIsAvailable: (state, action) => {
      state.isAvailable = action.payload.isAvailable;
    }
  },
  extraReducers: builder => {
    builder
      .addCase(checkUserNameAvailability.pending, state => {
        state.isChecking = true;
        state.isAvailable = null;
      })
      .addCase(checkUserNameAvailability.fulfilled, (state, action) => {
        state.isChecking = false;
        state.username = action.meta.arg;
        state.isAvailable = action.payload.isAvailable;
      })
      .addCase(checkUserNameAvailability.rejected, (state) => {
        state.isChecking = false;
        state.isAvailable = null;
      });
  }
});

export const { setEmailAndPassword, setUsername, setUserId, setIsAvailable } = profileSlice.actions;

// =============================================================================
// Store Configuration
// =============================================================================
const store = configureStore({
  reducer: {
    profile: profileSlice.reducer,
    auths: authSlice.reducer,
    notifications: notificationsSlice.reducer
  }
});

export default store;
