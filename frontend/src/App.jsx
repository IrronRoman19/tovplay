import "./App.css";
import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AnalyticsConsumer } from "use-analytics";
import { apiService } from "@/api/apiService.js";
import { CommunityDialog } from "@/components/CommunityDialog";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/context/ThemeContext";
import { useAuth } from "@/hooks/useAuth";
import Pages from "@/pages/index.jsx";
import { loginSuccess } from "@/stores/authSlice";
import { createPageUrl } from "@/utils/index.ts";

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { isLoggedIn, isDiscordRegistered } = useAuth();
  const [showCommunityDialog, setShowCommunityDialog] = useState(false);
  const [hasCheckedCommunity, setHasCheckedCommunity] = useState(false);
  const [discordInviteLink, setDiscordInviteLink] = useState("");

  // Handle immediate dialog display after login
  useEffect(() => {
    const handleShowDialog = () => {
      const showDialog = sessionStorage.getItem('showCommunityDialog') === 'true';
      const inviteLink = sessionStorage.getItem('discordInviteLink');
      
      if (showDialog && inviteLink) {
        setDiscordInviteLink(inviteLink);
        setShowCommunityDialog(true);
        // Clear the flags
        sessionStorage.removeItem('showCommunityDialog');
        sessionStorage.removeItem('discordInviteLink');
      }
    };

    // Listen for the custom event
    window.addEventListener('showCommunityDialog', handleShowDialog);
    
    // Initial check
    handleShowDialog();

    return () => {
      window.removeEventListener('showCommunityDialog', handleShowDialog);
    };
  }, []);

  // Handle periodic community checks
  useEffect(() => {
    const checkCommunity = async () => {
      if (isLoggedIn) {  // Removed isDiscordRegistered check
        try {
          // Skip if we just showed the dialog from login
          if (sessionStorage.getItem('showCommunityDialog') === 'true') {
            return;
          }

          const communityData = await apiService.checkCommunityStatus();
          const isInCommunity = communityData[`User ${communityData.discord_username} in our community`] || 
                              communityData.in_community;
          
          if (!isInCommunity) {
            const inviteLink = import.meta.env.VITE_DISCORD_INVITE_LINK || 'https://discord.gg/FSVxjGAW';
            setDiscordInviteLink(inviteLink);
            setShowCommunityDialog(true);
          }
        } catch (error) {
          console.error('Error checking community status:', error);
        } finally {
          setHasCheckedCommunity(true);
        }
      } else {
        setHasCheckedCommunity(true);
      }
    };

    // Only run the check if we're not showing the dialog from login
    if (sessionStorage.getItem('showCommunityDialog') !== 'true') {
      checkCommunity();
    }

    // Check periodically (every 5 minutes)
    const interval = setInterval(checkCommunity, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [isLoggedIn]);  // Removed isDiscordRegistered from dependencies

  // Listen for theme changes from other tabs/windows and system preference changes
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'tovplay-theme' || e.key === 'tovplay-font-size' || e.key === 'tovplay-reduce-motion') {
        // Trigger a re-render to apply theme changes
        window.dispatchEvent(new Event('storage'));
      }
    };

    // Listen for system color scheme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e) => {
      const theme = localStorage.getItem('tovplay-theme');
      if (theme === 'system') {
        document.documentElement.classList.toggle('dark', e.matches);
      }
    };
    
    // Add event listeners
    window.addEventListener('storage', handleStorageChange);
    mediaQuery.addListener(handleSystemThemeChange);
    
    // Initial theme setup
    const savedTheme = localStorage.getItem('tovplay-theme') || 'light';
    if (savedTheme === 'system') {
      document.documentElement.classList.toggle('dark', mediaQuery.matches);
    }
    
    // Mark theme as loaded to prevent FOUC
    document.documentElement.classList.add('theme-loaded');
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      mediaQuery.removeListener(handleSystemThemeChange);
    };
  }, []);

  // Handle Discord OAuth redirect parameters
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const userId = params.get("user_id");
    const token = params.get("token");

    if (userId && token) {
      dispatch(loginSuccess({ user: userId, token: token, isLoggedIn: true, isDiscordRegistered: true }));
      // Clear the URL parameters to prevent them from being reused or exposed
      navigate(location.pathname, { replace: true });
    }
  }, [location, navigate, dispatch]);

  useEffect(() => {
    const handleSessionExpired = () => {
      // Close the dialog if it's open
      setShowCommunityDialog(false);
      navigate(createPageUrl("SignIn"));
    };

    addEventListener("session-expired", handleSessionExpired);

    return () => {
      removeEventListener("session-expired", handleSessionExpired);
    };
  }, [navigate]);

  // Check if user is logged in and not in community
  useEffect(() => {
    if (isLoggedIn && !isDiscordRegistered && !hasCheckedCommunity) {
      const fetchDiscordInviteLink = async () => {
        try {
          const response = await apiService.get("/auth/discord/invite-link");
          setDiscordInviteLink(response.data.invite_link);
          setShowCommunityDialog(true);
        } catch (error) {
          console.error("Error fetching Discord invite link:", error);
        }
      };
      fetchDiscordInviteLink();
      setHasCheckedCommunity(true);
    }
  }, [isLoggedIn, isDiscordRegistered, hasCheckedCommunity]);

  // Apply theme class to html element on mount and when theme changes
  useEffect(() => {
    const savedTheme = localStorage.getItem('tovplay-theme') || 'light';
    document.documentElement.classList.toggle('dark', savedTheme === 'dark');
  }, []);

  return (
    <ThemeProvider>
      <AnalyticsConsumer>
        {({ track, page, identify }) => (
          <TooltipProvider>
            <div className="min-h-screen bg-background text-foreground transition-colors duration-200 ease-in-out">
              <Pages track={track} page={page} identify={identify} />
              <Toaster 
                position="top-center" 
                richColors 
                closeButton 
                toastOptions={{
                  classNames: {
                    toast: '!bg-background !text-foreground',
                    title: '!text-foreground',
                    description: '!text-foreground/80',
                  },
                }}
              />
              <CommunityDialog 
                isOpen={isLoggedIn && showCommunityDialog && hasCheckedCommunity} 
                onClose={() => setShowCommunityDialog(false)}
                discordInviteLink={discordInviteLink}
              />
            </div>
          </TooltipProvider>
        )}
      </AnalyticsConsumer>
    </ThemeProvider>
  );
}

export default App;
