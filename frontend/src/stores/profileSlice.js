import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import axios from "@/lib/axios-config";


export const checkUserNameAvailability = createAsyncThunk(
  "profile/checkUserNameAvailability",
  async (username, { rejectWithValue }) => {
    if (username && username.length >= 3) {

      // make an axios request to check availability
      try {
        const response = await axios.post("/api/users/username-availability", { "Username": username });
        return response.data;
      } catch (error) {
        if (error.response) {
          // Server responded with error status (e.g., 404, 500)
          console.log(error.data);
          return rejectWithValue(error.response.data);
        } else if (error.request) {
          // Request was made but no response received
          console.log(error.request);
          return rejectWithValue({ message: "Network error" });
        } else {
          console.log(error.message);
          // Something else happened
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
    //
    username: "",
    email: "",
    password: "",

    //
    isChecking: false,
    isAvailable: null,
    usernameLastChecked: "",

    // User ID from backend after signup
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
      });

    builder
      .addCase(checkUserNameAvailability.fulfilled, (state, action) => {
        state.isChecking = false;
        state.username = action.meta.arg;
        state.isAvailable = action.payload.isAvailable;
        console.log(action.payload);
      });

    builder
      .addCase(checkUserNameAvailability.rejected, (state, action) => {
        state.isChecking = false;
        state.isAvailable = null;
      });
  }
});

export const { setEmailAndPassword, setUsername, setUserId, setIsAvailable } = profileSlice.actions;
export default profileSlice.reducer;
