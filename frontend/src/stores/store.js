import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import notificationsReducer from "./notificationsSlice";
import profileReducer from "./profileSlice";

const store = configureStore({
  reducer: {
    profile: profileReducer,
    auths: authReducer,
    notifications: notificationsReducer
  }
});

export default store;
