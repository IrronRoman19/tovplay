import { Bell, X } from "lucide-react";
import PropTypes from "prop-types";
import { useEffect, useState, useCallback, useContext } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { apiService } from "@/api/apiService.js";
import { useToast } from "@/components/ui/use-toast";
import { SocketContext } from "@/context/SocketContext.jsx";
import { fetchNotifications, markNotificationsAsRead } from "@/stores/notificationsSlice";
import LocalStorage from "@/utils/localStorage.js";
import { LanguageContext } from "@/components/lib/LanguageContext";


const currentUserId = LocalStorage.authUserId.get();

const NotificationSystem = () => {
  const { toast, dismiss } = useToast();
  const { t } = useContext(LanguageContext);
  const dispatch = useDispatch();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [disconnectToastId, setDisconnectToastId] = useState(null);
  const { socket, isConnected } = useContext(SocketContext);

  // Show toaster when websocket disconnects, dismiss when reconnected
  useEffect(() => {
    if (!isConnected && !disconnectToastId) {
      const { id, update } = toast({
        title: t("disconnectTitle"),
        description: t("disconnectDescription"),
        variant: "destructive",
        duration: Infinity,
        action: (
          <button
            aria-label={t("dismiss")}
            className="p-1 rounded-[50%] outline outline-1 top-2 end-2 absolute focus-visible:outline-2 focus-within:outline-2"
            onClick={() => {
              dismiss(id);
              setDisconnectToastId(null);
            }}
          >
            <X className="w-4 h-4" />
          </button>
        )
      });
      setDisconnectToastId(id);
      // store update function locally for removal
      NotificationSystem.disconnectToastUpdate = update;
    }

    if (isConnected && disconnectToastId) {
      if (NotificationSystem.disconnectToastUpdate) {
        NotificationSystem.disconnectToastUpdate({ open: false });
        NotificationSystem.disconnectToastUpdate = null;
      } else {
        dismiss(disconnectToastId);
      }
      setDisconnectToastId(null);
    }
    // Only depend on isConnected to avoid update loop
  }, [isConnected, disconnectToastId, toast, dismiss]);
  const [markAllLoading, setMarkAllLoading] = useState(false);
  const [markAllDisabled, setMarkAllDisabled] = useState(true);

  // Ensure button is only enabled if there are unread notifications and not loading
  // notifications will only contain unread notifications (per server response)
  const notifications = useSelector(state => state.notifications.notifications);
  const unreadCount = useSelector(state => state.notifications.unreadCount);
  const navigate = useNavigate();

  // Button enabled only if there is at least one notification and not loading
  // Only enable button if there are notifications (server only returns unread)
  useEffect(() => {
    setMarkAllDisabled(notifications.length === 0 || markAllLoading);
  }, [notifications, markAllLoading]);

  useEffect(() => {
    dispatch(fetchNotifications());
  }, [dispatch]);

  const handleNotification = useCallback(async data => {
    if (data && data.type === "session_cancelled" && data.message) {
      await dispatch({ type: "notifications/receiveNotification", payload: data });
    } else {
      await dispatch(fetchNotifications());
    }
    setMarkAllDisabled(false);
  }, [dispatch]);

  useEffect(() => {
    if (!socket) {
      return;
    }
    socket.on("notification", handleNotification);
    return () => {
      socket.off("notification", handleNotification);
    };
  }, [socket, handleNotification]);

  useEffect(() => {
    if (socket && isConnected && currentUserId) {
      socket.emit("register", { userId: currentUserId });
    }
  }, [socket, isConnected, currentUserId]);

  const handleBellClick = async () => {
    setIsSidebarOpen(true);
    await dispatch(fetchNotifications());
  };

  const handleCloseSidebar = () => {
    setIsSidebarOpen(false);
  };

  const handleMarkAllRead = async () => {
    setMarkAllLoading(true);
    const notificationIds = notifications.map(notification => notification.id);

    try {
      await dispatch(markNotificationsAsRead(notificationIds));
      await dispatch(fetchNotifications());
      // Button state now managed by useEffect above
    } catch (error) {
      setMarkAllDisabled(false);
      console.error("Error marking notifications as read:", error);
    }
    setMarkAllLoading(false);
  };

  const handleNotificationClick = async notificationId => {
    if (notificationId) {
      await dispatch(markNotificationsAsRead([notificationId]));
      await dispatch(fetchNotifications());
      navigate(`/gamerequest/${notificationId}`);
      setIsSidebarOpen(false);
    }
  };


  return (
    <>
      {/* Toaster notification handled globally in App.jsx */}
      {/* Bell icon in the navigation bar */}
      <div className="relative">
        <button
          onClick={handleBellClick}
          className="relative p-2 rounded-full text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-all duration-200"
        >
          <Bell className="h-6 w-6" />
          {unreadCount > 0 && (
            <span
              className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Notification Sidebar */}
      <aside
        dir={t('dir') || 'ltr'}
        className={`fixed top-0 right-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl z-30 flex flex-col p-4 transform transition-transform duration-300 ${
          isSidebarOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="relative pb-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 text-center">{t("notificationsTitle")}</h2>
          <button 
            onClick={handleCloseSidebar} 
            className={`absolute top-0 p-1 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
              t('dir') === 'rtl' ? 'left-4' : 'right-4'
            }`}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto mt-4 space-y-3">
          {notifications.length === 0 ? (
            <p className="text-gray-500 dark:text-gray-400 text-center mt-8">{t("notificationsEmpty")}</p>
          ) : (
            notifications.map(notification => {
              let data = {};
              let isJson = false;
              try {
                const parsed = JSON.parse(notification.message);
                if (typeof parsed === "object" && parsed !== null) {
                  data = parsed;
                  isJson = true;
                }
              } catch (_e) {
                // Not a JSON string, treat as plain text
                data = { message: notification.message };
              }
              const isDeclined = isJson && data.payload === "declined";
              if (notification.id && !isDeclined) {
                return (
                  <button
                    key={notification.id}
                    className={`p-3 rounded-md shadow-sm transition-colors duration-200 text-left w-full cursor-pointer border border-blue-200 dark:border-gray-700 hover:bg-blue-50 dark:hover:bg-gray-700`}
                    onClick={() => handleNotificationClick(notification.id)}
                  >
                    <p className={`font-semibold text-sm ${
                      notification.is_read 
                        ? "text-gray-600 dark:text-gray-400" 
                        : "text-gray-900 dark:text-white"
                    }`}>
                      {isJson ? <AsyncNotificationMessage message={notification.message} /> : notification.message}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </button>
                );
              } else {
                return (
                  <div
                    key={notification.id + crypto.randomUUID()}
                    className="p-3 rounded-md shadow-sm bg-gray-100 dark:bg-gray-700/50 text-left w-full opacity-75"
                  >
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {isJson ? <AsyncNotificationMessage message={notification.message} /> : notification.message}
                    </p>
                    {isJson && data.type === "session_cancelled" && data.reason && (
                      <p className="text-xs text-red-600 mt-1 font-medium">
                        {t("cancellationReason", { reason: data.reason })}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>
                );
              }
            })
          )}
        </div>

        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleMarkAllRead}
            disabled={markAllDisabled}
            className={`w-full py-2 px-4 text-sm font-medium rounded-md transition-colors duration-200 ${
              markAllDisabled
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50'
            }`}
          >
            {markAllLoading ? (
              <span className="flex items-center justify-center">
                <span className="animate-spin mr-2 w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></span>
                {t("marking")}
              </span>
            ) : t("markAllAsRead")}
          </button>
        </div>
      </aside>

      {/* Backdrop for the sidebar */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 dark:bg-black/70 z-20" 
          onClick={handleCloseSidebar}
          aria-hidden="true"
        />
      )}
    </>
  );
};

async function getNotificationMessage({ message }) {
  const notificationData = message;
  let userName = notificationData.user_name;
  if (notificationData.user_id) {
    try {
      const user = await apiService.get(`/users/${notificationData.user_id}`);
      userName = user?.name || userName;
    } catch (_e) {

      console.error(_e);
    }
  }

  if (notificationData.payload === "accepted") {
    return `${userName} accepted your game request!`;
  }
  return `${userName} declined your game request because ${notificationData.reason || "they couldn't make it"}`;
}

function AsyncNotificationMessage({ message }) {
  const [notificationText, setNotificationText] = useState("");
  useEffect(() => {
    let isMounted = true;
    (async () => {
      const msg = await getNotificationMessage({ message });
      if (isMounted) {
        setNotificationText(msg);
      }
    })();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);
  return <>{notificationText}</>;
}

AsyncNotificationMessage.propTypes = {
  message: PropTypes.string.isRequired
};

export default NotificationSystem;
