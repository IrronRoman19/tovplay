import { User, MessageCircle, UserPlus, Check, Edit, Mic, MessageSquare, VolumeX, Shield, Users, AlertTriangle, Ban, X, Send, Trash2 } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { useState, useEffect, useContext } from "react";
import { toast } from "sonner";
import { apiService } from "@/api/apiService";
import RequestModal from "../RequestModal";
import { LanguageContext } from "@/components/lib/LanguageContext";

export default function ProfileHeader({ player, isMyProfile, onEditClick, currentUser }) {
  const { t } = useContext(LanguageContext);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showFriendsModal, setShowFriendsModal] = useState(false);
  const [friendRequestSent, setFriendRequestSent] = useState(false);
  const [isRemoveFriendDialogOpen, setIsRemoveFriendDialogOpen] = useState(false);

  // Local state for friend status to allow immediate UI updates
  const [friendStatus, setFriendStatus] = useState(player.friendStatus);
  const [blockingReason, setBlockingReason] = useState(player.blocking_reason);
  const [relationshipData, setRelationshipData] = useState(null);
  const [requestMessage, setRequestMessage] = useState("");
  const [isRequestPopoverOpen, setIsRequestPopoverOpen] = useState(false);
  const [playerForModal, setPlayerForModal] = useState(null);

  // Sync local state with prop when it changes
  useEffect(() => {
    setFriendStatus(player.friendStatus);
    setBlockingReason(player.blocking_reason);
  }, [player.friendStatus, player.blocking_reason]);

  // Fetch relationship status
  useEffect(() => {
    console.log("ProfileHeader: Checking relationship...", { playerUsername: player.username, isMyProfile });
    const fetchRelationship = async () => {
      // Use username instead of ID for the check
      if (player.username && !isMyProfile) {
        console.log("ProfileHeader: Fetching relationship for", player.username);
        try {
          const data = await apiService.checkRelationship(player.username);
          console.log("ProfileHeader: Relationship data received:", data);
          setRelationshipData(data);

          // Update friendStatus based on the relationship data
          if (data && data.status) {
            const status = data.status.toLowerCase();
            if (status === 'accepted') {
              setFriendStatus('Accepted');
            } else if (status === 'pending') {
              setFriendStatus('Pending');
            } else if (status === 'blocked') {
              setFriendStatus('Blocked');
              if (data.blocking_reason || data.message) {
                setBlockingReason(data.blocking_reason || data.message);
              }
            } else if (status === 'none') {
              setFriendStatus('None');
            }
          }
        } catch (error) {
          console.error("Failed to fetch relationship status", error);
        }
      }
    };
    fetchRelationship();
  }, [player.username, isMyProfile]);

  const handleAddFriend = async (message = null) => {
    try {
      const response = await apiService.sendFriendRequest(player.username, message);
      setFriendRequestSent(true);
      setFriendStatus('Pending'); // Optimistic update

      // Update relationship data with the new info if available
      if (response) {
        setRelationshipData(prev => ({
          ...prev,
          status: 'Pending',
          message: message, // Store the sent message
          request_id: response.request_id || response.id // Try to capture ID if returned
        }));
      }

      setIsRequestPopoverOpen(false);
      setRequestMessage(""); // Reset message
      toast.success("Friend request sent!");

      // Trigger a re-fetch to ensure we have the correct ID for cancellation
      // This is a safety measure if the immediate response doesn't have the ID
      const updatedData = await apiService.checkRelationship(player.username);
      if (updatedData) {
        setRelationshipData(updatedData);
        if (updatedData.status) {
          const status = updatedData.status.toLowerCase();
          if (status === 'pending') setFriendStatus('Pending');
        }
      }

    } catch (error) {
      console.error("Error sending friend request:", error);
      toast.error("Failed to send friend request.");
    }
  };

  const handleCancelRequest = async () => {
    // Find request ID from relationshipData
    const requestId = relationshipData?.request_id || relationshipData?.id;

    if (!requestId) {
      console.error("No request ID found to cancel");
      toast.error(t("cannotCancelRequestIdMissing") || "Cannot cancel request: ID missing");
      return;
    }

    try {
      await apiService.cancelFriendRequest(requestId);
      setFriendStatus('None');
      setFriendRequestSent(false);
      setRelationshipData(null); // Clear relationship data
      toast.success(t("friendRequestCancelled") || "Friend request cancelled");
    } catch (error) {
      console.error("Error cancelling request:", error);
      toast.error(t("failedToCancelRequest") || "Failed to cancel request");
    }
  };

  const handleBlockUser = async () => {
    const reason = window.prompt(t("blockUserPrompt", { username: player.username }) || `Are you sure you want to block ${player.username}? Please provide a reason (optional):`);
    if (reason === null) {
      return; // User cancelled
    }

    try {
      await apiService.blockUser(player.username, reason);
      setFriendStatus('Blocked'); // Immediate UI update
      setBlockingReason(reason); // Immediate UI update for reason
      toast.success(t("blockedUser", { username: player.username }) || `Blocked ${player.username}`);
    } catch (error) {
      console.error("Error blocking user:", error);
      toast.error(t("failedToBlockUser") || "Failed to block user.");
    }
  };

  const handleUnblockUser = async () => {
    if (!window.confirm(t("unblockUserPrompt", { username: player.username }) || `Are you sure you want to unblock ${player.username}?`)) {
      return;
    }
    try {
      await apiService.unblockUser(player.username);
      setFriendStatus('None'); // Immediate UI update (reset to not friends)
      setBlockingReason(null); // Clear reason
      toast.success(t("unblockedUser", { username: player.username }) || `Unblocked ${player.username}`);
    } catch (error) {
      console.error("Error unblocking user:", error);
      toast.error(t("failedToUnblockUser") || "Failed to unblock user.");
    }
  };

  const handleAcceptRequest = async (requestId) => {
    try {
      await apiService.respondToFriendRequest(requestId, true);
      setFriendStatus('Accepted'); // Immediate UI update
      toast.success(t("friendRequestAccepted") || "Friend request accepted!");
    } catch (error) {
      console.error("Error accepting friend request:", error);
      toast.error(t("failedToAcceptFriendRequest") || "Failed to accept friend request.");
    }
  };

  const getCommunicationIcon = commType => {
    switch (commType) {
      case "voice_messages":
        return <Mic className="w-4 h-4" />;
      case "prefer_no_talking":
        return <VolumeX className="w-4 h-4" />;
      default:
        return <MessageSquare className="w-4 h-4" />;
    }
  };

  const getCommunicationLabel = commType => {
    switch (commType) {
      case "voice_messages":
        return t("voiceMessages") || "Voice Messages";
      case "prefer_no_talking":
        return t("preferNoTalking") || "Prefer No Talking";
      default:
        return t("writtenMessages") || "Written Messages";
    }
  };

  const getOpennessIcon = openness => {
    switch (openness) {
      case "careful":
        return <AlertTriangle className="w-4 h-4" />;
      case "only_previous":
        return <Shield className="w-4 h-4" />;
      default:
        return <Users className="w-4 h-4" />;
    }
  };

  const getOpennessLabel = openness => {
    switch (openness) {
      case "careful":
        return t("carefulWithNewPeople") || "Careful with new people";
      case "only_previous":
        return t("onlyPreviousContacts") || "Only previous contacts";
      default:
        return t("openToNewPeople") || "Open to new people";
    }
  };

  // Helper to check if blocked (case-insensitive)
  const isBlocked = friendStatus?.toLowerCase() === 'blocked';


  return (
    <>
      <div className={`calm-card bg-gradient-to-r from-white to-gray-50 dark:from-gray-800 dark:to-gray-900 border-gray-200 dark:border-gray-700 p-8 ${isBlocked ? 'border-red-200 dark:border-red-800 bg-red-50/30 dark:bg-red-900/20' : ''}`}>
        <div className="flex flex-col lg:flex-row items-center lg:items-start lg:space-x-8">
          {/* Profile Image Section */}
          <div className="flex-shrink-0 mb-6 lg:mb-0 pl-4 pt-4">
            <div className="relative">
              <div className="w-32 h-32 bg-gradient-to-br from-teal-100 to-teal-200 rounded-2xl flex items-center justify-center overflow-hidden shadow-lg">
                {player.profilePhoto || player.avatar_url ? (
                  <img
                    src={player.profilePhoto || player.avatar_url}
                    alt={`${player.username}'s profile`}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = "https://api.dicebear.com/9.x/thumbs/svg?seed=" + player.username;
                    }}
                  />
                ) : (
                  <User className="w-16 h-16 text-teal-600" />
                )}
              </div>
              {/* Online status indicator */}
              <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-green-500 rounded-full border-4 border-white shadow-lg flex items-center justify-center">
                <div className="w-3 h-3 bg-white rounded-full"></div>
              </div>
            </div>
          </div>

          {/* Profile Info Section */}
          <div className="flex-grow text-center lg:text-left lg:py-4">
            <div className="mb-4">
              <div className="flex items-center justify-center lg:justify-start space-x-4 mb-2">
                <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100">{player.username}</h1>
              </div>
              {player.discord_username && (
                <a
                  href={`https://discord.com/users/${player.discord_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 font-medium flex items-center justify-center lg:justify-start space-x-2"
                >
                  <MessageCircle className="w-4 h-4" />
                  <span>{player.discord_username}</span>
                </a>
              )}
            </div>

            {/* Stats Row */}
            <div className="flex justify-center lg:justify-start gap-8 mb-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-teal-600 dark:text-teal-400">{player.friends?.length || 0}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{t("friends") || "Friends"}</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-teal-600 dark:text-teal-400">{player.games?.length || 0}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{t("games") || "Games"}</p>
              </div>
            </div>


          </div>

          {/* Action Buttons Section */}
          <div className="flex-shrink-0 lg:py-4 pr-4 pt-4">
            {isMyProfile ? (
              <button
                onClick={onEditClick}
                className="calm-button flex items-center justify-center space-x-2 px-6 py-3"
              >
                <Edit className="w-5 h-5" />
                <span>{t("editProfile") || "Edit Profile"}</span>
              </button>
            ) : isBlocked ? (
              <div className="flex flex-col items-center space-y-3">
                <div className="text-red-600 dark:text-red-400 font-bold text-lg flex items-center">
                  <Ban className="w-5 h-5 mr-2" />
                  {t("youHaveBlockedThisUser") || "You have blocked this user"}
                </div>
                <div className="group relative">
                  <button
                    onClick={handleUnblockUser}
                    className="flex items-center justify-center space-x-2 px-6 py-2 rounded-lg transition-colors border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 font-medium text-sm"
                  >
                    <span>{t("unblockUser") || "Unblock User"}</span>
                  </button>
                  {blockingReason && (
                    <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                      {t("reason") || "Reason"}: {blockingReason}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col space-y-3">
                <span className="group relative">
                  <button
                    onClick={async () => {
                      if (!currentUser) {
                        toast.error(t("mustBeLoggedIn") || "You must be logged in to send a request.");
                        return;
                      }

                      try {
                        const playerData = await apiService.findOverlappingTimes(player.username);
                        const targetPlayer = Array.isArray(playerData) ? playerData[0] : playerData;

                        if (targetPlayer) {
                          const enhancedPlayer = { ...player, ...targetPlayer };
                          setPlayerForModal(enhancedPlayer);
                          setShowRequestModal(true);
                        } else {
                          toast.error(t("couldNotFetchAvailability") || "Could not fetch availability data.");
                        }
                      } catch (error) {
                        console.error("Error fetching overlapping times:", error);
                        toast.error(t("failedToLoadPlayerAvailability") || "Failed to load player availability.");
                      }
                    }}
                    className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-colors"
                  >
                    <MessageCircle className="w-5 h-5" />
                    <span>{t("requestPlay") || "Request Play"}</span>
                  </button>
                </span>

                {/* Add Friend Button Logic */}
                <div className="group relative">
                  {(friendStatus === 'Accepted' || player.isFriend) ? (
                    <button
                      disabled
                      className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg border font-medium bg-gray-100 dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 cursor-default w-full"
                    >
                      <Users className="w-5 h-5" />
                      <span>{t("friends") || "Friends"}</span>
                    </button>
                  ) : (player.incomingRequestId) ? (
                    <button
                      onClick={() => handleAcceptRequest(player.incomingRequestId)}
                      className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-colors border font-medium bg-teal-100 dark:bg-teal-900/50 border-teal-200 dark:border-teal-700 text-teal-700 dark:text-teal-300 hover:bg-teal-200 dark:hover:bg-teal-900/70 w-full"
                    >
                      <UserPlus className="w-5 h-5" />
                      <span>{t("acceptRequest") || "Accept Request"}</span>
                    </button>
                  ) : (friendStatus === 'Pending' || friendRequestSent) ? (
                    <Popover>
                      <PopoverTrigger asChild>
                        <button
                          className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-colors border font-medium bg-green-100 dark:bg-green-900/50 border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 w-full hover:bg-green-200 dark:hover:bg-green-900/70"
                        >
                          <Check className="w-5 h-5" />
                          <span>{t("requestSent") || "Request Sent"}</span>
                        </button>
                      </PopoverTrigger>
                      <PopoverContent className="w-80">
                        <div className="space-y-4">
                          <h4 className="font-medium text-gray-900 dark:text-gray-100">{t("requestSent") || "Request Sent"}</h4>
                          {relationshipData?.message && (
                            <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded text-sm text-gray-600 dark:text-gray-300 italic">
                              "{relationshipData.message}"
                            </div>
                          )}
                          <button
                            onClick={handleCancelRequest}
                            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700 text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 text-sm font-medium transition-colors"
                          >
                            <X className="w-4 h-4" />
                            <span>{t("cancelRequest") || "Cancel Request"}</span>
                          </button>
                        </div>
                      </PopoverContent>
                    </Popover>
                  ) : (
                    <Popover open={isRequestPopoverOpen} onOpenChange={setIsRequestPopoverOpen}>
                      <PopoverTrigger asChild>
                        <button
                          className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-colors border font-medium bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 w-full"
                        >
                          <UserPlus className="w-5 h-5" />
                          <span>{t("addFriend") || "Add Friend"}</span>
                        </button>
                      </PopoverTrigger>
                      <PopoverContent className="w-80" align="end">
                        <div className="space-y-4">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium leading-none dark:text-gray-100">{t("addFriend") || "Add Friend"}</h4>
                          </div>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {t("sendMessageToUser", { username: player.username }) || `Send a message to ${player.username} with your request (optional).`}
                          </p>
                          <Textarea
                            placeholder={t("friendRequestPlaceholder") || "Hi, let's play some games!"}
                            value={requestMessage}
                            onChange={(e) => setRequestMessage(e.target.value)}
                            className="min-h-[80px]"
                          />
                          <div className="flex flex-col gap-2">
                            <button
                              onClick={() => handleAddFriend(requestMessage)}
                              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-teal-600 dark:bg-teal-700 text-white rounded-md hover:bg-teal-700 dark:hover:bg-teal-600 transition-colors"
                            >
                              <Send className="w-4 h-4" />
                              <span>{t("sendWithMessage") || "Send with Message"}</span>
                            </button>
                            <button
                              onClick={() => handleAddFriend(null)}
                              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
                            >
                              <span>{t("sendWithoutMessage") || "Send without Message"}</span>
                            </button>
                          </div>
                        </div>
                      </PopoverContent>
                    </Popover>
                  )}
                </div>

                <div className="group relative">
                  <button
                    onClick={handleBlockUser}
                    className="flex items-center justify-center space-x-2 px-6 py-3 rounded-lg transition-colors border border-red-200 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 font-medium"
                  >
                    <Ban className="w-5 h-5" />
                    <span>{t("blockUser") || "Block User"}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div >

      {showRequestModal && (
        <RequestModal
          player={playerForModal || player}
          currentUser={currentUser}
          onClose={() => {
            setShowRequestModal(false);
            setPlayerForModal(null);
          }}
        />
      )
      }

      {
        showFriendsModal && (
          <FriendsModal
            isOpen={showFriendsModal}
            onClose={() => setShowFriendsModal(false)}
          />
        )
      }

    </>
  );
}
