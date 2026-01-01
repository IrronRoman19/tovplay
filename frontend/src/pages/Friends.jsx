import { Heart, Users, UserPlus, MessageCircle } from "lucide-react";
import { useState, useEffect, useContext } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { apiService } from "@/api/apiService";
import { createPageUrl } from "@/utils";
import { LanguageContext } from "@/components/lib/LanguageContext";

export default function Friends() {
  const { t } = useContext(LanguageContext);
  const [friends, setFriends] = useState([]);
  const [friendRequests, setFriendRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [friendsData, requestsData] = await Promise.all([
          apiService.getFriends(),
          apiService.getFriendRequests()
        ]);

        setFriends(friendsData || []);
        setFriendRequests(requestsData || []);
      } catch (error) {
        console.error("Error fetching friends data:", error);
        toast.error(t("failedToLoadFriendsData") || "Failed to load friends data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAcceptRequest = async (requestId) => {
    try {
      await apiService.respondToFriendRequest(requestId, true);
      setFriendRequests(prev => prev.filter(r => r.id !== requestId));
      toast.success(t("friendRequestAccepted") || "Friend request accepted!");
      // Refresh friends list
      const updatedFriends = await apiService.getFriends();
      setFriends(updatedFriends || []);
    } catch (error) {
      console.error("Error accepting request:", error);
      toast.error(t("failedToAcceptRequest") || "Failed to accept request");
    }
  };

  const handleDeclineRequest = async (requestId) => {
    try {
      await apiService.respondToFriendRequest(requestId, false);
      setFriendRequests(prev => prev.filter(r => r.id !== requestId));
      toast.success(t("friendRequestDeclined") || "Friend request declined");
    } catch (error) {
      console.error("Error declining request:", error);
      toast.error(t("failedToDeclineRequest") || "Failed to decline request");
    }
  };

  const isOnline = lastSeen => {
    if (!lastSeen) {
      return false;
    }
    return new Date(lastSeen) > new Date(Date.now() - 6 * 60 * 1000);
  };

  if (loading) {
    return <div className="flex justify-center items-center h-screen"><div className="text-xl text-gray-600">Loading...</div></div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Friends</h1>
        <p className="text-gray-600">Manage your gaming connections and friend requests.</p>
      </div>

      {/* Friend Requests */}
      {friendRequests.length > 0 && (
        <div className="calm-card mb-8">
          <div className="flex items-center space-x-3 mb-6">
            <UserPlus className="w-6 h-6 text-teal-600" />
            <h2 className="text-xl font-semibold text-gray-800">Friend Requests</h2>
          </div>
          <div className="space-y-4">
            {friendRequests.map(request => (
              <div key={request.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-teal-50 to-teal-100 rounded-full flex items-center justify-center">
                    <Users className="w-6 h-6 text-teal-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-800">{request.sender_username}</h3>
                    <p className="text-sm text-gray-600">Wants to be your friend</p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleDeclineRequest(request.id)}
                    className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Decline
                  </button>
                  <button
                    onClick={() => handleAcceptRequest(request.id)}
                    className="px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors"
                  >
                    Accept
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Friends List */}
      <div className="calm-card">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Heart className="w-6 h-6 text-teal-600" />
            <h2 className="text-xl font-semibold text-gray-800">Your Friends ({friends.length})</h2>
          </div>
          <Link to={createPageUrl("FindPlayers")}>
            <button className="flex items-center space-x-2 px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors">
              <UserPlus className="w-4 h-4" />
              <span>Find More Friends</span>
            </button>
          </Link>
        </div>

        {friends.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4">
            {friends.map(friend => (
              <div key={friend.username} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-teal-50 to-teal-100 rounded-full flex items-center justify-center relative">
                      {friend.user_profile_pic ? (
                        <img
                          src={friend.user_profile_pic}
                          alt={friend.username}
                          className="w-full h-full rounded-full object-cover"
                        />
                      ) : (
                        <Users className="w-5 h-5 text-teal-600" />
                      )}
                      {isOnline(friend.last_seen) && (
                        <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
                      )}
                    </div>
                    <div>
                      <Link to={createPageUrl(`UserProfile?username=${friend.username}`)}>
                        <h3 className="font-semibold text-gray-800 hover:text-teal-600 transition-colors">
                          {friend.username}
                        </h3>
                      </Link>
                      <p className="text-xs text-gray-500">
                        {isOnline(friend.last_seen) ? "Online now" : "Offline"}
                      </p>
                    </div>
                  </div>
                  <Link to={`/chat/${friend.username}`}>
                    <button className="p-2 text-gray-400 hover:text-teal-600 transition-colors">
                      <MessageCircle className="w-4 h-4" />
                    </button>
                  </Link>
                </div>
                <div className="flex flex-wrap gap-1">
                  {friend.games?.slice(0, 3).map((game, index) => (
                    <span key={index} className="px-2 py-1 bg-white text-xs text-gray-600 rounded">
                      {game}
                    </span>
                  ))}
                  {friend.games?.length > 3 && (
                    <span className="px-2 py-1 bg-white text-xs text-gray-500 rounded">
                      +{friend.games.length - 3}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Heart className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-800 mb-2">No friends yet</h3>
            <p className="text-gray-500 mb-4">Start connecting with other players to build your friend list.</p>
            <Link to={createPageUrl("FindPlayers")}>
              <button className="px-6 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 transition-colors">
                Find Players
              </button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
