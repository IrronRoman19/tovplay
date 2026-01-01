
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X, UserMinus, Ban, MoreVertical, Loader2, User } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { apiService } from "@/api/apiService";
import { toast } from "sonner";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function FriendsModal({ isOpen, onClose }) {
    const [friends, setFriends] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);

    useEffect(() => {
        if (isOpen) {
            loadFriends();
        }
    }, [isOpen]);

    const loadFriends = async () => {
        try {
            setLoading(true);
            const data = await apiService.getFriends();
            let friendsList = [];

            if (Array.isArray(data)) {
                friendsList = data;
            } else if (typeof data === 'object' && data !== null) {
                // Handle dictionary format where keys are usernames
                friendsList = Object.entries(data).map(([username, info]) => ({
                    username: username, // Ensure username is present
                    ...info
                }));
            }

            setFriends(friendsList);
        } catch (error) {
            console.error("Failed to load friends:", error);
            toast.error("Failed to load friends list");
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveFriend = async (friendUsername) => {
        if (!window.confirm(`Are you sure you want to remove ${friendUsername} from your friends?`)) {
            return;
        }

        try {
            setActionLoading(friendUsername);

            // We need the relationship ID to cancel/remove.
            // Since getFriends might not return it, we fetch it first.
            // This is a bit inefficient but safe.
            const relationship = await apiService.checkRelationship(friendUsername);
            const requestId = relationship?.request_id || relationship?.id;

            if (requestId) {
                await apiService.cancelFriendRequest(requestId);
                setFriends(prev => prev.filter(f => f.username !== friendUsername));
                toast.success(`Removed ${friendUsername} from friends`);
            } else {
                toast.error("Could not find friend relationship to remove");
            }
        } catch (error) {
            console.error("Error removing friend:", error);
            toast.error("Failed to remove friend");
        } finally {
            setActionLoading(null);
        }
    };

    const handleBlockUser = async (friendUsername) => {
        const reason = window.prompt(`Are you sure you want to block ${friendUsername}? Reason (optional):`);
        if (reason === null) return;

        try {
            setActionLoading(friendUsername);
            await apiService.blockUser(friendUsername, reason);
            setFriends(prev => prev.filter(f => f.username !== friendUsername));
            toast.success(`Blocked ${friendUsername}`);
        } catch (error) {
            console.error("Error blocking user:", error);
            toast.error("Failed to block user");
        } finally {
            setActionLoading(null);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="sm:max-w-md bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
                <DialogHeader>
                    <div className="flex items-center justify-between">
                        <DialogTitle className="text-xl font-bold text-gray-900 dark:text-white">My Friends</DialogTitle>
                    </div>
                </DialogHeader>

                <div className="max-h-[60vh] overflow-y-auto mt-4 pr-1">
                    {loading ? (
                        <div className="flex justify-center py-8">
                            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                        </div>
                    ) : friends.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                            <p>You haven't added any friends yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {friends.map((friend) => (
                                <div
                                    key={friend.username}
                                    className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                >
                                    <div className="flex items-center space-x-3 flex-grow">
                                        <div className="w-10 h-10 rounded-full bg-teal-100 dark:bg-teal-900/30 flex items-center justify-center overflow-hidden border border-teal-200 dark:border-teal-800">
                                            <img
                                                src={friend.avatar_url || friend.profilePhoto || `https://api.dicebear.com/9.x/thumbs/svg?seed=${friend.username}`}
                                                alt={friend.username}
                                                className="w-full h-full object-cover"
                                                onError={(e) => {
                                                    e.target.onerror = null;
                                                    e.target.src = `https://api.dicebear.com/9.x/thumbs/svg?seed=${friend.username}`;
                                                }}
                                            />
                                        </div>
                                        <Link
                                            to={`/profile?username=${friend.username}`}
                                            onClick={onClose}
                                            className="font-medium text-gray-900 dark:text-gray-100 hover:text-teal-600 dark:hover:text-teal-400 transition-colors hover:underline"
                                        >
                                            {friend.username}
                                        </Link>
                                    </div>

                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                                                {actionLoading === friend.username ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <MoreVertical className="w-4 h-4" />
                                                )}
                                                <span className="sr-only">Actions</span>
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem
                                                className="text-red-600 dark:text-red-400 focus:text-red-700 dark:focus:text-red-300 focus:bg-red-50 dark:focus:bg-red-900/20 cursor-pointer"
                                                onSelect={() => handleRemoveFriend(friend.username)}
                                            >
                                                <UserMinus className="w-4 h-4 mr-2" />
                                                <span>Remove Friend</span>
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                className="text-red-600 dark:text-red-400 focus:text-red-700 dark:focus:text-red-300 focus:bg-red-50 dark:focus:bg-red-900/20 cursor-pointer"
                                                onSelect={() => handleBlockUser(friend.username)}
                                            >
                                                <Ban className="w-4 h-4 mr-2" />
                                                <span>Block User</span>
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
