import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { apiService } from "@/api/apiService";
import GameRequestCard from "@/components/GameRequestCard";
import GameRequestSentCard from "@/components/GameRequestSentCard";
import QuickActions from "@/components/dashboard/QuickActions";
import UpcomingSessionCard from "@/components/dashboard/UpcomingSessionCard";
import { samplePlayers } from "@/components/data/samplePlayers";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { CancelSessionDialog } from "@/components/CancleSessionDialog";
import { delayPromise } from "@/lib/utils";

function transformGameRequests(apiResponse, userMap, gameMap
) {
  if (!apiResponse) {
    return [];
  }
  return apiResponse.map(req =>
    ({
      ...req,
      game: gameMap.get(req.game_id).game_name || req.game_id
    }));

}

export default function Dashboard() {
  const { t } = useContext(LanguageContext);
  const [currentUser, setCurrentUser] = useState(null);
  const [gameRequests, setGameRequests] = useState([]);
  const [gameRequestsSent, setGameRequestsSent] = useState([]);
  const [isLoadingGameRequests, setIsLoadingGameRequests] = useState(true);
  const [actionState, setActionState] = useState({});
  const [upcomingSession, setUpcomingSession] = useState(null);
  const [upcomingSessions, setUpcomingSessions] = useState([]);
  const [upcomingIndex, setUpcomingIndex] = useState(0);
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [showCancelSessionDialog, setShowCancelSessionDialog] = useState(false);

  const now = new Date();

  console.log("upcomingSession", upcomingSession);

  useEffect(() => {
    // Fetch user info and other dashboard data on mount
    const fetchInitialData = async () => {
      try {
        try{// Fetch current user
          const responseUser = await apiService.getCurrentUser();
          setCurrentUser(responseUser);
          setOnlinePlayers(
            samplePlayers.filter(
              p =>
                p.username !== responseUser.username &&
              new Date(p.last_seen) > new Date(Date.now() - 15 * 60 * 1000)
            )
          );
        } catch(error){
          console.error("Failed to fetch current user", error);
          setCurrentUser({ username: "!!!Error getting username!!" });
        }
        // Fetch game requests
        fetchRequests();
        // Fetch upcoming session (replace with API if available)
        const now = new Date();
        // Fetch online friends (replace with API if available)
      } catch (error) {
      //debugger
        showToast("Failed to load dashboard data", error);
      }
    };
    fetchInitialData();
  }, []);

  // Accept/Decline logic
  const notificationRef = useRef();

  const showToast = (msg, type = "success") => {
    if (notificationRef.current) {
      notificationRef.current.show(msg, type, { dismissible: true });
    }
  };

  function cancleGameButton() {
    console.log("cancleGame called for session:", upcomingSession);
    // Implement cancel game logic here, e.g., call API to cancel the session
    setShowCancelSessionDialog(true);
  }

  async function sendCancelMessage(message) {
    console.log("sendCancelMessage called with message:", message);
    try {
      await apiService.session.cancel(upcomingSession.id, message);
      // Update the UI immediately by setting upcomingSession to null
      setUpcomingSession(null);
      setShowCancelSessionDialog(false);
      showToast("Session cancelled successfully", "success");
      // Still fetch the latest data to ensure consistency
      await delayPromise(1000);
      fetchRequests();
    } catch(error) {
      console.error("Failed to send cancel message", error);
      showToast("Failed to cancel session", "error");
      setShowCancelSessionDialog(false);
    }
  }

  
  async function fetchScheduledSessions() {
    function getSessionEndDate(session) {
      return new Date(`${session.scheduled_date}T${session.end_time}`);
    }

    const response = await apiService.get("/scheduled_sessions/");
    const data = response.data || [];
    const now = new Date();
    const filtered = data.filter(session => {
      if (!["accepted","pending",undefined].includes(session.status)) return false;
      const sessionDate = getSessionEndDate(session);
      return sessionDate >= now;
    });
    // sort ascending by start (scheduled_date + start_time)
    filtered.sort((a,b) => {
      const da = new Date(`${a.scheduled_date}T${a.start_time}`);
      const db = new Date(`${b.scheduled_date}T${b.start_time}`);
      return da - db;
    });
    return filtered;
  }

  const fetchRequests = async () => {
    try {


      //const response2 = await apiService.get("/game_requests/received_requests");
      //console.log("game_requests/received_requests", response2.data)
      const response = await apiService.get("/game_requests/");
      // Collect all unique user IDs (sender + recipient) and game IDs
      const userIds = new Set();
      const gameIds = new Set();
      console.log("game_requests", response.data);


      function getAllUserAndGameIds(requests) {
        for (const req of requests) {
          // userIds.add(req.sender_user_id);
          // userIds.add(req.recipient_user_id);
          gameIds.add(req.game_id);
        }
      }

      if(response.data.recipient) {
        getAllUserAndGameIds(Object.values(response.data.recipient));
        getAllUserAndGameIds(Object.values(response.data.sender));
      } else {
        getAllUserAndGameIds(Object.values(response.data));
      }

      const scheduledList = await fetchScheduledSessions();
      const scheduled = scheduledList && scheduledList.length>0;
      if (scheduled) {
        scheduledList.forEach(scheduled => {
          userIds.add(scheduled.organizer_user_id);
          userIds.add(scheduled.second_player_id);
          gameIds.add(scheduled.game_id);
        });
      }

      // Fetch user info for each ID
      const userMap = new Map();
      await Promise.all(
        Array.from(userIds).map(async id => {
          const res = await apiService.get(`/users/${id}`);
          userMap.set(id, res.data.username);
        })
      );
      // Note: that's not how you do Memonization reacts reloads this component several times
      // and the cache will be lost on each fetch

      // Memoized fetch for game info
      const gameMap = new Map();
      const gameCache = new Map();
      await Promise.all(
        Array.from(gameIds).map(async id => {
          if (gameCache.has(id)) {
            gameMap.set(id, gameCache.get(id));
          } else {
            const res = await apiService.get(`/games/${id}`);
            gameMap.set(id, res.data);
            gameCache.set(id, res.data);
            console.log(res.data)
          }
        })
      );
      if (scheduledList && scheduledList.length>0) {
        // Map list into transformed sessions with game and participants
        const transformedList = scheduledList.map(scheduled => ({
          ...scheduled,
          game_name: gameMap.get(scheduled.game_id)?.game_name || scheduled.game_id,
          game_site_url: gameMap.get(scheduled.game_id)?.game_site_url || "",
          participants: [
            userMap.get(scheduled.organizer_user_id),
            userMap.get(scheduled.second_player_id)
          ],
          organizer_user_name: userMap.get(scheduled.organizer_user_id),
          second_player_name: userMap.get(scheduled.second_player_id)
        }));
        setUpcomingSessions(transformedList);
        setUpcomingIndex(0);
        setUpcomingSession(transformedList[0]);
      }
      
      response.data.recipient = response.data.recipient.filter(requestStillPendingAndRelevant);
      response.data.sender = response.data.sender.filter(requestStillPendingAndRelevant);
      let tmp = transformGameRequests(response.data.recipient, userMap, gameMap);
      setGameRequests(tmp);
      tmp = transformGameRequests(response.data.sender, userMap, gameMap);
      setGameRequestsSent(tmp);

    } catch (error) {
      //debugger
      console.log("Failed to fetch game requests",error);
      showToast("Failed to fetch game requests");
    }
    setIsLoadingGameRequests(false);
  };

  function goToNextUpcoming() {
    setUpcomingIndex(prev => {
      const next = Math.min(prev + 1, upcomingSessions.length - 1);
      const sess = upcomingSessions[next];
      if (sess) setUpcomingSession(sess);
      return next;
    });
  }

  function goToPrevUpcoming() {
    setUpcomingIndex(prev => {
      const next = Math.max(prev - 1, 0);
      const sess = upcomingSessions[next];
      if (sess) setUpcomingSession(sess);
      return next;
    });
  }

  function requestStillPendingAndRelevant(req) {
    if (req.status !== "pending") {
      return false;
  }
  // Check if the scheduled date is in the future
  const scheduledDate = new Date(req.suggested_time);
  return scheduledDate >= now;
}
  // Combined Accept/Decline handler
  const handleRequestAction = async (gameRequestId, accept) => {
    setActionState(prev => ({
      ...prev,
      [gameRequestId]: {
        loading: true,
        error: false,
        type: accept ? "accept" : "decline"
      }
    }));

    const finish = success => {
      setActionState(prev => ({
        ...prev,
        [gameRequestId]: {
          loading: false,
          error: !success,
          type: success ? null : accept ? "accept" : "decline"
        }
      }));
    };

    try {
      const { data } = await apiService.put(
        `/game_requests/accept_invite/${gameRequestId}`,
        {
          accept_invite: accept
        }
      );
      showToast(
        data.message ||
        (accept ? "Accepted successfully" : "Declined successfully"),
        "success"
      );

      await fetchRequests();
      finish(true);
    } catch (err) {
      if (err.status < 400 || err.status === 409) {
        await fetchRequests();
        finish(true);
        return;
      }
      finish(false);
      showToast("Failed to update game request", err);
    }
    setIsLoadingGameRequests(false);
  };

  const handleRequestCancel = async (gameRequestId) => {
    //set UI state to loading
    setActionState(prev => ({
      ...prev,
      [gameRequestId]: {
        loading: true,
        error: false,
      }
    }));
    const finish = success => {
      setActionState(prev => ({
        ...prev,
        [gameRequestId]: {
          loading: false,
          error: !success,
        }
      }));
    };
    try {
      finish(false);
      const { data } = await apiService.put(
        `/game_requests/${gameRequestId}`,
        {status: "cancelled"}
      );
      showToast(
        data?.message ||
        "request cancelled successfully",
        "success"
      );
    } catch (err) {
      showToast("Failed to cancel game request", err);
      finish(true);
      return;
    }
    finish(true);
    await fetchRequests();
  }

  if (!currentUser) {
    return (
      <div className="flex items-center justify-center h-screen bg-white dark:bg-gray-900">
        <p className="text-gray-800 dark:text-gray-200">{t("loading")}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 min-h-screen bg-white dark:bg-gray-900">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
          {t("welcomeBack", { username: currentUser.username })}
        </h1>
        <p
          className="text-gray-600 dark:text-gray-400"
          dangerouslySetInnerHTML={{
            __html: t("pendingRequests", { count: gameRequests.length })
          }}
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <UpcomingSessionCard
            session={upcomingSession}
            cancleGameFn={cancleGameButton}
            joinGameFn={() => ({})}
            onNext={goToNextUpcoming}
            onPrev={goToPrevUpcoming}
            canNext={upcomingSessions.length > 0 && upcomingIndex < upcomingSessions.length - 1}
            canPrev={upcomingSessions.length > 0 && upcomingIndex > 0}
            currentUser={currentUser}
            t={t}
          />
          <div className="flex flex-col md:flex-row gap-8">
            <div className="w-full md:w-1/2">
              <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">
                {t("pendingGameRequests")}
              </h2>
              {isLoadingGameRequests ? (
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-center">
                  <span
                    className="animate-spin inline-block w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full mb-2"></span>
                  <p className="text-gray-600 dark:text-gray-300">{t("loading")}</p>
                </div>
              ) : gameRequests.length > 0 ? (
                <div className="space-y-4">
                  {gameRequests.map(req => (
                    <GameRequestCard
                      key={req.id}
                      request={req}
                      onAccept={id => handleRequestAction(id, true)}
                      onDecline={id => handleRequestAction(id, false)}
                      actionState={
                        actionState[req.id] || {
                          loading: false,
                          error: false,
                          type: null
                        }
                      }
                    />
                  ))}
                </div>
              ) : (
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-center">
                  <p className="text-gray-600 dark:text-gray-300">{t("noPendingRequests")}</p>
                </div>
              )}
            </div>
            <div className="w-full md:w-1/2">
              <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">
                {t("pendingGameRequestsSent")}
              </h2>
              {isLoadingGameRequests ? (
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-center">
                  <span
                    className="animate-spin inline-block w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full mb-2"></span>
                  <p className="text-gray-600 dark:text-gray-300">{t("loading")}</p>
                </div>
              ) : gameRequestsSent.length > 0 ? (
                <div className="space-y-4">
                  {gameRequestsSent.map(req => (
                    <GameRequestSentCard
                      key={req.id}
                      request={req}
                      onCancel={id => handleRequestCancel(id)}
                      actionState={
                        actionState[req.id] || {
                          loading: false,
                          error: false,
                          type: null
                        }
                      }
                    />
                  ))}
                </div>
              ) : (
                <div className="bg-gray-50 dark:bg-gray-800 p-6 rounded-lg text-center">
                  <p className="text-gray-600 dark:text-gray-300">{t("noPendingRequests")}</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-1 space-y-8">
          {/* <OnlineFriends onlinePlayers={onlinePlayers} t={t} /> */}
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
            <QuickActions t={t} />
          </div>
        </div>
      </div>
      <CancelSessionDialog
                      isOpen={showCancelSessionDialog}
                      session={upcomingSession}
                      onClose={() => setShowCancelSessionDialog(false)}
                      onSend={(message) => sendCancelMessage(message)}
                    />
    </div>
  );
}


