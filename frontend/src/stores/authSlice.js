import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiService } from "@/api/apiService";
import LocalStorage from "@/utils/localStorage";

export const loginUser = createAsyncThunk(
  "auths/loginUser",
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const response = await apiService.post(
        "/users/login", { Email: username, Password: password });

      if (response.data && response.data.jwt_token) {
        const userData = await apiService.getUser(response.data.user_id);
        return {
          user: response.data.user_id,
          token: response.data.jwt_token,
          isLoggedIn: true,
          isDiscordRegistered: userData?.is_discord_registered || false
        };
      } else {
        return rejectWithValue("Didn't receive token.");
      }
    } catch (error) {
      return rejectWithValue(error.response?.data?.message|| error.message || "Login failed.");
    }
  }
);

// Shared logic for login
function setAuthState(state, action) {
  state.user = action.payload.user;
  state.isLoggedIn = action.payload.isLoggedIn;
  state.token = action.payload.token;
  state.isDiscordRegistered = action.payload.isDiscordRegistered;
  if (state.token) {
    LocalStorage.authToken.set(state.token); // Save token to localStorage
    LocalStorage.authUserId.set(state.user); // Save userId to localStorage
    LocalStorage.authisLoggedIn.set(true); // Save isLoggedIn to localStorage
    LocalStorage.isDiscordRegistered.set(state.isDiscordRegistered); // Save isDiscordRegistered to localStorage
  }
}

// Shared logic for logout
function clearAuthState(state) {
  state.user = null;
  state.isLoggedIn = false;
  state.token = null;
  state.isDiscordRegistered = false;  // Reset discord registered state
  LocalStorage.authToken.clear();
  LocalStorage.authUserId.clear();
  LocalStorage.authisLoggedIn.clear();
  LocalStorage.isDiscordRegistered.clear();
  // Clear any dialog-related session storage
  sessionStorage.removeItem('showCommunityDialog');
  sessionStorage.removeItem('discordInviteLink');
  // Also clear Discord user info if it exists
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
export default authSlice.reducer;
