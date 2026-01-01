// LoggedInRoute.jsx
import { useSelector } from "react-redux";
import { Navigate, Outlet } from "react-router-dom";

/**
 * LoggedInRoute - protects a group of routes.
 * If logged in → renders children (via <Outlet />)
 * If not → redirects to /Welcome
 */
const LoggedInRoute = () => {
  // Access the isLoggedIn state from Redux store
  const loggedIn = useSelector(state => state.auths.isLoggedIn);

  // If not logged in, redirect to /Welcome
  if (!loggedIn) {
    return <Navigate to="/Welcome" replace />;
  }
  // render child routes
  return <Outlet />;
};

export default LoggedInRoute;
