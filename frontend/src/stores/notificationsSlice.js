// src/stores/notificationsSlice.js
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiService } from "@/api/apiService";

/**
 * @typedef {Object} Notification
 * @property {string} id
 * @property {string} message
 * @property {string} created_at
 * @property {boolean} is_read
 * @property {string} recipient_user_id
 * @property {string} [requestId] - Unique identifier for game request notifications
 * @property {string} [cancellationReason] - Reason for session cancellation, if applicable
 */

// Thunks
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

const initialState = {
  notifications: [],
  unreadCount: 0,
  loading: false,
  error: null
};

const notificationsSlice = createSlice({
  name: "notifications",
  initialState,
  reducers: {
    receiveNotification(state, action) {
      const n = action.payload;
      // If notification is a cancellation, ensure cancellationReason is present
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
      state.notifications = state.notifications.map(n => ({
        ...n,
        is_read: true
      }));
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
export default notificationsSlice.reducer;
