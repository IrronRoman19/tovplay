import { useSelector } from "react-redux";

export function useAuth() {
  const authState = useSelector(state => state.auths);
  return {
    user: authState.user,
    isLoggedIn: authState.isLoggedIn,
    isDiscordRegistered: authState.isDiscordRegistered
    // Add other auth state properties you need
  };
}
