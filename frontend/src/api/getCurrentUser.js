
// Retrieves user information by user ID from LocalStorage and returns the API response.
// No additional logic or side effects are performed.

import LocalStorage from "../utils/localStorage";
import { apiService } from "@/api/apiService.js";

export async function getCurrentUser() {
  const id = LocalStorage.authUserId.get();
  return apiService.get(`/users/${id}`);
}
