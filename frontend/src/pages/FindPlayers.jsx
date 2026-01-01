import * as LucideIcons from "lucide-react";
import { useCallback, useContext, useEffect, useState } from "react";
import PlayerCard from "../components/PlayerCard";
import { apiService } from "@/api/apiService";
import RequestModal from "@/components/RequestModal";
import RequirementsDialog from "@/components/RequirementsDialog";
import { SocketContext } from "@/context/SocketContext";
import { useCheckAvailability } from "@/hooks/useCheckAvailability";
import { useCheckGames } from "@/hooks/useCheckGames";
import { LanguageContext } from "@/components/lib/LanguageContext";

const { Gamepad2, Sparkles, Users, ...restIcons } = LucideIcons;

export default function FindPlayers() {
  const { t, language } = useContext(LanguageContext);
  const isRTL = language === 'he';
  const [searchResults, setSearchResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchedGame, setSearchedGame] = useState("");
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [offlinePlayers, setOfflinePlayers] = useState([]); // Added this line
  const [currentUser, setCurrentUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [gamePlayerCounts, setGamePlayerCounts] = useState({});
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [games, setGames] = useState([]);
  const [loadingGames, setLoadingGames] = useState(true);
  const [userHasGames, setUserHasGames] = useState(true);

  // Socket context
  const { socket, isConnected, isError } = useContext(SocketContext);
  console.log("Socket status: isConnected", isConnected, "isError", isError);


  // Check requirements
  const [showRequirementsDialog, setShowRequirementsDialog] = useState(false);
  const [requirements, setRequirements] = useState({
    missingAvailability: false,
    missingGames: false,
    checked: false
  });

  const { checkAvailability } = useCheckAvailability();
  const { checkGames } = useCheckGames();

  // List of game names that have dark logos and need inversion in dark mode
  const isDarkLogo = (gameName) => {
    const darkLogoGames = [
      'Fortnite',
      'Apex Legends',
      'Among Us',
      'Rocket League',
      'Overwatch'
      // Add more game names with dark logos as needed
    ];
    return darkLogoGames.includes(gameName);
  };

  // Check all requirements when component mounts
  useEffect(() => {
    let isMounted = true;

    const checkRequirements = async () => {
      try {
        const [hasAvail, hasGamesSelected] = await Promise.all([
          checkAvailability(),
          checkGames()
        ]);

        if (!isMounted) {
          return;
        }

        const missingAvailability = !hasAvail;
        const missingGames = !hasGamesSelected;

        setRequirements({
          missingAvailability,
          missingGames,
          checked: true
        });

        // Show dialog if any requirements are not met
        if (missingAvailability || missingGames) {
          setShowRequirementsDialog(true);
        }
      } catch (error) {
        console.error("Error checking requirements:", error);
        // If there's an error, assume requirements are met to avoid blocking the UI
        if (isMounted) {
          setRequirements({
            missingAvailability: false,
            missingGames: false,
            checked: true
          });
        }
      }
    };

    checkRequirements();

    return () => {
      isMounted = false;
    };
  }, []); // Empty dependency array to run only once on mount

  // Fetch games from API
  useEffect(() => {
    const fetchGames = async () => {
      try {
        const response = await apiService.get("/games/");
        setGames(response.data);
      } catch (error) {
        console.error("Error fetching games:", error);
        setError("Failed to load games. Please try again later.");
      } finally {
        setLoadingGames(false);
      }
    };

    fetchGames();
  }, []);

  // Memoize the countPlayersForGames function to prevent recreation on every render
  const countPlayersForGames = useCallback((players, currentUsername) => {
    const gameCounts = {};
    games.forEach(game => {
      gameCounts[game.game_name] = 0;
    });

    players.forEach(player => {
      if (player.games && player.username !== currentUsername) {
        player.games.forEach(game => {
          if (gameCounts.hasOwnProperty(game)) {
            gameCounts[game]++;
          }
        });
      }
    });
    return gameCounts;
  }, [games]); // Only recreate if games changes

  // Update search results when players or searchedGame changes
  useEffect(() => {
    if (players.length > 0 && currentUser) {
      setGamePlayerCounts(countPlayersForGames(players, currentUser.username));
    }
  }, [players, currentUser, countPlayersForGames]);

  // Socket.IO listener for player list updates
  useEffect(() => {
    if (socket) {
      console.log("Socket instance available.");
      socket.on("player_list_update", data => {
        console.log("player_list_update received data:", data);

        const onlinePlayersData = data.onlinePlayers || [];
        const offlinePlayersData = data.offlinePlayers || [];

        // Check if player is friend helper (you might need to fetch friends list or check an 'isFriend' property if the backend provides it)
        // Since we don't have direct friend status in the socket data usually, 
        // we might rely on the backend sending it or we need to check against a local friends list.
        // Assuming the backend 'findplayers' socket event sends 'is_friend' or similar, 
        // OR we can fetch friends list on mount and compare. 
        // *However*, to keep it simple and assuming backend *might* not send it yet, 
        // let's check if the 'player' object has 'isFriend'. If not, we might need to update backend.
        // **Update**: The user asked for "matches that are my friends". 
        // Ideally, the backend should send this flag. 
        // If the backend sends 'is_friend' (boolean), we sort by that.

        const sortPlayers = (playersList) => {
          return playersList.sort((a, b) => {
            // Priority 1: Is Friend (true comes first)
            if (a.is_friend && !b.is_friend) return -1;
            if (!a.is_friend && b.is_friend) return 1;
            return 0;
          });
        };

        const processedOnlinePlayers = onlinePlayersData
          .filter(player => player.username !== currentUser?.username)
          .map(player => ({
            ...player,
            isOnline: true,
            languages: player.languages || "Not specified",
            user_profile_pic: player.user_profile_pic,
            last_seen: player.last_seen,
            username: player.username || "Unknown",
            discord_username: player.discord_username || "Not provided",
            communication_preferences: player.communication_preferences || "Not specified",
            games: Array.isArray(player.games) ? player.games : [],
            available_slots: Array.isArray(player.available_slots) ? player.available_slots : []
          }));

        const processedOfflinePlayers = offlinePlayersData
          .filter(player => player.username !== currentUser?.username)
          .map(player => ({
            ...player,
            isOnline: false, // Explicitly set to false for offline players
            languages: player.languages || "Not specified",
            user_profile_pic: player.user_profile_pic,
            last_seen: player.last_seen,
            username: player.username || "Unknown",
            discord_username: player.discord_username || "Not provided",
            communication_preferences: player.communication_preferences || "Not specified",
            games: Array.isArray(player.games) ? player.games : [],
            available_slots: Array.isArray(player.available_slots) ? player.available_slots : []
          }));

        // Sort both lists ensuring friends are at the top
        const sortedOnline = sortPlayers(processedOnlinePlayers);
        const sortedOffline = sortPlayers(processedOfflinePlayers);

        // Combine all players for the main 'players' state and searchResults
        const allProcessedPlayers = [...sortedOnline, ...sortedOffline];

        setPlayers(allProcessedPlayers);
        setSearchResults(allProcessedPlayers);
        setOnlinePlayers(sortedOnline); // Set sorted online players
        setOfflinePlayers(sortedOffline); // Set sorted offline players
        console.log("onlinePlayers updated (sorted):", sortedOnline);
        console.log("offlinePlayers updated (sorted):", sortedOffline);
        setHasSearched(true);
        setLoading(false); // Stop loading after receiving socket data
      });

      return () => {
        socket.off("player_list_update");
      };
    }
  }, [socket, currentUser]);

  // Log onlinePlayers and offlinePlayers whenever they change
  useEffect(() => {
    console.log("Current onlinePlayers:", onlinePlayers);
  }, [onlinePlayers]);

  const fetchPlayersForGame = useCallback(async (gameName) => {
    if (!gameName) {
      setPlayers([]);
      setSearchResults([]);
      setLoading(false);
      return;
    }

    if (isConnected && socket) {
      console.log("Socket connected, emitting 'get_players' for game:", gameName);
      socket.emit("get_players", { game_name: gameName, current_user_id: currentUser.id });
    } else if (!isConnected || isError) {
      console.log("Fallback to REST API triggered for game:", gameName);
      try {
        console.log("Making REST API call for game:", gameName);
        const response = await apiService.get(
          `/findplayers/`,
          {
            params: {
              game_name: gameName
            },
            headers: {
              "Accept": "application/json"
            }
          }
        );

        console.log("Fetched players via REST:", response.data);

        const processedPlayers = response.data
          .filter(player => player.username !== currentUser?.username)
          .map(player => ({
            ...player,
            lastSeen: new Date().toISOString(),
            isOnline: false,
            languages: player.languages || "Not specified",
            user_profile_pic: player.user_profile_pic,
            last_seen: new Date().toISOString(),
            username: player.username || "Unknown",
            discord_username: player.discord_username || "Not provided",
            communication_preferences: player.communication_preferences || "Not specified",
            games: Array.isArray(player.games) ? player.games : [],
            available_slots: Array.isArray(player.available_slots) ? player.available_slots : []
          }));

        setPlayers(processedPlayers);
        setSearchResults(processedPlayers);
        setOnlinePlayers([]);
        setOfflinePlayers(processedPlayers);
        console.log("onlinePlayers set to empty array (REST fallback)");
        setHasSearched(true);

      } catch (err) {
        console.error("Error fetching players via REST:", {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          headers: err.config
        });
        setError(`Failed to fetch players via REST: ${err.message}`);
        setSearchResults([]);
        setPlayers([]);
      } finally {
        setLoading(false);
        console.log("Loading set to false after REST fallback.");
      }
    }
  }, [isConnected, socket, currentUser, isError, setPlayers, setSearchResults, setOnlinePlayers, setOfflinePlayers, setHasSearched, setError, setLoading]);

  const handleGameClick = useCallback(async game => {
    const newSearchedGame = game;
    console.log("Setting searchedGame to:", newSearchedGame);
    setSearchedGame(newSearchedGame);
    setHasSearched(!!newSearchedGame);
    setLoading(true); // Start loading
    fetchPlayersForGame(newSearchedGame);
  }, [fetchPlayersForGame]);


  // Listen for player_status_changed event to trigger a refresh
  useEffect(() => {
    if (socket) {
      socket.on("player_status_changed", data => {
        console.log("player_status_changed received:", data);
        // If a game is currently searched, re-fetch players to update the list
        if (searchedGame) {
          console.log("Player status changed, re-fetching players for game:", searchedGame);
          fetchPlayersForGame(searchedGame);
        }
      });

      return () => {
        socket.off("player_status_changed");
      };
    }
  }, [socket, searchedGame, fetchPlayersForGame]); // Add fetchPlayersForGame to dependencies

  // Initial fetch of players if a game is already selected (e.g., from URL or previous state)
  useEffect(() => {
    if (searchedGame && currentUser) {
      console.log("Initial fetch triggered for game:", searchedGame);
      fetchPlayersForGame(searchedGame);
    }
  }, [searchedGame, isConnected, socket, currentUser, fetchPlayersForGame]);


  useEffect(() => {
    async function handleUserProfile(currentUser){
      const profileData = await apiService.currentProfile.get();
      currentUser.profile = profileData;
      setCurrentUser(currentUser);
    }
    const fetchCurrentUser = async () => {
      setIsLoading(true);
      try {
        const currentUserData = await apiService.getCurrentUser();
        setCurrentUser(currentUserData);
        handleUserProfile(currentUserData);

      } catch (err) {
        console.error("Error fetching user data:", err);
        setError("Failed to load user data.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchCurrentUser();
  }, []);

  // Show loading state while checking requirements
  if (!requirements.checked) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-teal-500"></div>
      </div>
    );
  }

  return (
    <>
      <RequirementsDialog
        isOpen={showRequirementsDialog}
        onClose={() => setShowRequirementsDialog(false)}
        missingAvailability={requirements.missingAvailability}
        missingGames={requirements.missingGames}
      />
      <div className="max-w-5xl mx-auto p-6">
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100 mb-3">{t("findYourTeammate")}</h1>
          <p className="text-lg text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            {t("findPlayersSubtitle")}
          </p>
        </div>

        {/* Popular Games Quick Access */}
        <div className="mb-10">
          <div className={`flex items-center mb-6 ${isRTL ? 'space-x-reverse' : ''} space-x-3`}>
            <Sparkles className="w-6 h-6 text-teal-600 dark:text-teal-400" />
            <h2 className="text-2xl font-semibold text-gray-800 dark:text-gray-100">{t("findPlayersByGame")}</h2>
          </div>

          {/* Popular Games Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {loadingGames ? (
              <div>{t("loading")}</div>
            ) : error ? (
              <div className="text-red-500">{error}</div>
            ) : (
              games.map(game => (
                <button
                  key={game.id}
                  onClick={() => handleGameClick(game.game_name)}
                  className={`text-left transition-all ${searchedGame === game.game_name ? "ring-2 ring-teal-400" : ""
                    }`}
                >
                  <div
                    className="p-4 bg-teal-50 dark:bg-teal-900/30 hover:bg-teal-100 dark:hover:bg-teal-800/50 rounded-lg transition-colors text-center h-full w-full">
                    {game.icon_url ? (
                      <div className="flex justify-center mb-3">
                        <div className="w-50 h-50 flex items-center justify-center">
                          <div className="relative w-full h-full flex items-center justify-center">
                            <img
                              src={game.icon_url}
                              alt={game.game_name}
                              className={`w-full h-full object-contain ${isDarkLogo(game.game_name) ? 'dark:invert dark:brightness-0 dark:opacity-90' : ''}`}
                              onError={e => {
                                e.target.onerror = null;
                                e.target.style.display = "none";
                                const fallback = document.createElement("div");
                                fallback.className = "w-50 h-50 bg-teal-100 dark:bg-teal-800/80 rounded-full flex items-center justify-center";
                                e.target.parentNode.parentNode.insertBefore(fallback, e.target.parentNode);
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="w-12 h-12 flex items-center justify-center mx-auto mb-3">
                        <Gamepad2 className="w-8 h-8 text-teal-600 dark:text-teal-400" />
                      </div>
                    )}
                    <h3 className="font-medium text-gray-800 dark:text-gray-100">{game.game_name}</h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                      {game.category}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Search Results - Positioned directly below game buttons */}
          {hasSearched && (
            <div className="mt-8">
              <div className="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200 dark:border-gray-700 rounded-xl p-6">
                <div className={`flex items-center mb-6 ${isRTL ? 'space-x-reverse' : ''} space-x-3`}>
                  <Users className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                  <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    {t("playersWithMatchingAvailability", { game: searchedGame })}
                  </h2>
                </div>

                {loading ? (
                  <div className="text-center py-12">
                    <div
                      className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-teal-500 mx-auto mb-4"></div>
                    <p className="text-gray-600 dark:text-gray-300">{t("searchingForPlayers")}</p>
                  </div>
                ) : (onlinePlayers.length > 0 || offlinePlayers.length > 0) ? (
                  <div className="space-y-8">
                    {/* Friends Section */}
                    {(onlinePlayers.some(p => p.is_friend) || offlinePlayers.some(p => p.is_friend)) && (
                      <div className="space-y-4">
                        <div className="flex items-center space-x-2">
                          <Users className="w-5 h-5 text-teal-600 dark:text-teal-400" />
                          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                            {t("profile.friendsTab", "Friends")}
                          </h3>
                        </div>
                        <div className="grid md:grid-cols-2 gap-6">
                          {onlinePlayers.filter(p => p.is_friend).map(player => (
                            <PlayerCard
                              key={player.id} className="relative ring-2 ring-teal-400/30"
                              player={player}
                              currentUser={currentUser}
                              contextGame={searchedGame}
                              isOnline={true}
                              onPlayClick={() => {
                                const handlePlayerSelect = player => {
                                  if (!userHasAvailability) { alert("Please set your availability before sending requests"); return; }
                                  if (!userHasGames) { alert("Please select at least one game before sending requests"); return; }
                                  setSelectedPlayer(player);
                                  setShowRequestModal(true);
                                };
                                handlePlayerSelect(player);
                              }}
                            />
                          ))}
                          {offlinePlayers.filter(p => p.is_friend).map(player => (
                            <PlayerCard
                              key={player.id} className="relative ring-2 ring-teal-400/30"
                              player={player}
                              currentUser={currentUser}
                              contextGame={searchedGame}
                              isOnline={false}
                              onPlayClick={() => {
                                const handlePlayerSelect = player => {
                                  if (!userHasAvailability) { alert("Please set your availability before sending requests"); return; }
                                  if (!userHasGames) { alert("Please select at least one game before sending requests"); return; }
                                  setSelectedPlayer(player);
                                  setShowRequestModal(true);
                                };
                                handlePlayerSelect(player);
                              }}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Other Players Section */}
                    <div className="space-y-4">
                      {(onlinePlayers.some(p => p.is_friend) || offlinePlayers.some(p => p.is_friend)) && (
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                          {t("otherPlayers", "Other Players")}
                        </h3>
                      )}
                      <div className="grid md:grid-cols-2 gap-6">
                        {onlinePlayers.filter(p => !p.is_friend).map(player => (
                          <PlayerCard
                            key={player.id} className="relative"
                            player={player}
                            currentUser={currentUser}
                            contextGame={searchedGame}
                            isOnline={true}
                            onPlayClick={() => {
                              const handlePlayerSelect = player => {
                                if (!userHasAvailability) { alert("Please set your availability before sending requests"); return; }
                                if (!userHasGames) { alert("Please select at least one game before sending requests"); return; }
                                setSelectedPlayer(player);
                                setShowRequestModal(true);
                              };
                              handlePlayerSelect(player);
                            }}
                          />
                        ))}
                        {offlinePlayers.filter(p => !p.is_friend).map(player => (
                          <PlayerCard
                            key={player.id} className="relative"
                            player={player}
                            currentUser={currentUser}
                            contextGame={searchedGame}
                            isOnline={false}
                            onPlayClick={() => {
                              const handlePlayerSelect = player => {
                                if (!userHasAvailability) { alert("Please set your availability before sending requests"); return; }
                                if (!userHasGames) { alert("Please select at least one game before sending requests"); return; }
                                setSelectedPlayer(player);
                                setShowRequestModal(true);
                              };
                              handlePlayerSelect(player);
                            }}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Request Modal */}
                    {showRequestModal && selectedPlayer && (
                      <RequestModal
                        player={selectedPlayer}
                        currentUser={currentUser}
                        game={searchedGame}
                        onClose={() => setShowRequestModal(false)}
                        onSuccess={() => {
                          setShowRequestModal(false);
                          // You can add a success toast or message here
                        }}
                      />
                    )}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Gamepad2 className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                    </div>
                    <h3 className="text-lg font-medium text-gray-800 dark:text-gray-200 mb-2">{t("noPlayersFound")}</h3>
                    <p className="text-gray-500 dark:text-gray-400">
                      {t("noPlayersFoundDesc", { game: searchedGame })}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
