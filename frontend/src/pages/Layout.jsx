import {
  Calendar,
  Users,
  Edit,
  LogOut,
  Settings,
  User as UserIcon
} from "lucide-react";
import { useState, useEffect, useContext, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { SocketProvider } from "../context/SocketContext.jsx";
import NotificationSystem from "@/components/NotificationSystem";
import LanguageProvider from "@/components/lib/LanguageContext";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { logout as logoutAction } from "@/stores/authSlice";
import { createPageUrl } from "@/utils";
import apiServices from "@/api/apiService";

const Navigation = ({ children, currentPageName }) => {
  const { t, language } = useContext(LanguageContext);
  const location = useLocation();
  const [theme, setTheme] = useState("light");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const [profileData, setProfileData] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Get auth state from Redux
  const { user: userId, isLoggedIn } = useSelector(state => state.auths);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // Function to fetch user data
  const fetchCurrentUser = useCallback(async () => {
    if (!userId || !isLoggedIn) {
      setProfileData({});
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const response = await apiServices.getCurrentUser();
      
      if (response?.data) {
        setProfileData(response.data);
        setError(null);
      } else {
        setError("No user data received");
      }
    } catch (err) {
      console.error("Failed to fetch user:", err);
      setError("Failed to load user data");
      // If there's an error, clear the auth state
      dispatch(logoutAction());
      navigate("/SignIn");
    } finally {
      setIsLoading(false);
    }
  }, [userId, isLoggedIn, dispatch, navigate]);

  // Fetch user data when auth state changes
  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  // Handle logout
  const handleLogout = () => {
    dispatch(logoutAction());
    navigate("/SignIn");
  };

  const navigationItems = [
    { nameKey: "mySchedule", path: "Schedule", icon: Calendar },
    { nameKey: "findPlayers", path: "FindPlayers", icon: Users }
    // { nameKey: "friends", path: "Friends", icon: Heart }
  ];

  useEffect(() => {
    const applyTheme = () => {
      const savedTheme = localStorage.getItem("tovplay-theme") || "light";
      setTheme(savedTheme);
      const root = window.document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(savedTheme);
    };

    const applyFontSize = () => {
      const savedFontSize =
        localStorage.getItem("tovplay-font-size") || "medium";
      const root = window.document.documentElement;
      root.classList.remove(
        "font-size-small",
        "font-size-medium",
        "font-size-large"
      );
      root.classList.add(`font-size-${savedFontSize}`);
    };

    applyTheme();
    applyFontSize();

    window.addEventListener("theme-changed", applyTheme);
    window.addEventListener("font-size-changed", applyFontSize);

    return () => {
      window.removeEventListener("theme-changed", applyTheme);
      window.removeEventListener("font-size-changed", applyFontSize);
    };
  }, []);

  // handleLogout is already defined above with the correct action (logoutAction)

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen);
  const closeMenu = () => setIsMenuOpen(false);

  const isOnboarding = [
    "Welcome",
    "CreateAccount",
    "ChooseUsername",
    "SelectGames",
    "OnboardingSchedule",
    "OnboardingComplete",
    "SignIn"
  ].includes(currentPageName);

  if (isOnboarding) {
    return <main className="flex-1">{children}</main>;
  }

  const isRTL = language === 'he';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link
              to={createPageUrl("Dashboard")}
              className={`flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-3 hover:opacity-80 transition-opacity`}
            >
              <img
                src="https://qtrypzzcjebvfcihiynt.supabase.co/storage/v1/object/public/base44-prod/public/a2fc6dcfc_logo.png"
                alt="TovPlay Logo"
                className="w-8 h-8 rounded-lg"
              />
              <span className="text-xl font-semibold text-gray-800 dark:text-white">
                TovPlay
              </span>
            </Link>

            <div className={`hidden md:flex items-center gap-6`}>
              {navigationItems.map(item => (
                <Link
                  key={item.nameKey}
                  to={createPageUrl(item.path)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-200 text-sm whitespace-nowrap ${
                    location.pathname === createPageUrl(item.path)
                      ? "bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-300 font-semibold"
                      : "text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 font-medium"
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  <span>{t(item.nameKey)}</span>
                </Link>
              ))}
              {/* Notification system component */}
              <NotificationSystem />

              <div className="relative">
                <button
                  onClick={toggleMenu}
                  className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  <UserIcon className="w-5 h-5" />
                </button>

                {isMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={closeMenu} />
                    <div className={`absolute end-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-100 dark:border-gray-700 py-2 z-50 animate-in fade-in-0 zoom-in-95`}>
                      <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                        <p className="text-sm font-semibold text-gray-800 dark:text-white">
                          {profileData.username}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {profileData.email}
                        </p>
                      </div>
                      <div className="mt-1">
                        <Link
                          to={createPageUrl("MyProfile")}
                          onClick={closeMenu}
                          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                        >
                          <Edit className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          <span>{t("editProfile")}</span>
                        </Link>
                        <Link
                          to={createPageUrl("Settings")}
                          onClick={closeMenu}
                          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                        >
                          <Settings className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          <span>{t("settings")}</span>
                        </Link>
                        <button
                          onClick={handleLogout}
                          type="button"
                          className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-200 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-left"
                        >
                          <LogOut className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          <span>{t("logout")}</span>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1 bg-white dark:bg-gray-900">{children}</main>
    </div>
  );
};

export default function Layout({ children, currentPageName }) {
  return (
    <LanguageProvider>
      <SocketProvider>
        <Navigation currentPageName={currentPageName}>{children}</Navigation>
      </SocketProvider>
    </LanguageProvider>
  );
}
