const now = new Date();
const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
const tenMinutesAgo = new Date(now.getTime() - 10 * 60 * 1000);

const mockPlayers = [
  {
    id: "125e7f86-5810-416f-be49-45da321c4bf3",
    username: "GamerAlex",
    games: ["Chess", "Fortnite", "Minecraft", "League of Legends"],
    languages: ["English", "Spanish"],
    availability: {
      "Monday-18:00": true, "Monday-19:00": true, "Wednesday-18:00": true, "Wednesday-19:00": true,
      "Friday-20:00": true, "Friday-21:00": true, "Saturday-14:00": true, "Saturday-15:00": true
    },
    timezone: "EST",
    friends: ["CasualPlayer"],
    last_seen: now.toISOString(),
    prefers_custom_availability: true,
    description: "Competitive player looking for ranked matches",
    profilePhoto: "",
    preferred_communication: "voice_chat",
    openness_to_new_users: "open"
  },
  {
    id: "casual123",
    username: "CasualPlayer",
    games: ["Minecraft", "Stardew Valley", "Overwatch", "League of Legends"],
    languages: ["English", "French"],
    availability: {
      "Tuesday-19:00": true, "Tuesday-20:00": true, "Thursday-19:00": true, "Thursday-20:00": true,
      "Sunday-15:00": true, "Sunday-16:00": true
    },
    timezone: "PST",
    friends: ["ProGamer1"],
    last_seen: fiveMinutesAgo.toISOString(),
    prefers_custom_availability: false,
    description: "Just here to have fun and make new friends",
    profilePhoto: "",
    preferred_communication: "written_messages",
    openness_to_new_users: "open"
  },
  {
    id: "strategy456",
    username: "StrategyMaster",
    games: ["Chess", "Stardew Valley", "Among Us", "Minecraft"],
    languages: ["English", "German"],
    availability: {
      "Monday-20:00": true, "Wednesday-20:00": true, "Friday-20:00": true,
      "Saturday-10:00": true, "Saturday-11:00": true, "Sunday-10:00": true, "Sunday-11:00": true
    },
    timezone: "CET",
    friends: [],
    last_seen: tenMinutesAgo.toISOString(),
    prefers_custom_availability: true,
    description: "Turn-based strategy enthusiast",
    profilePhoto: "",
    preferred_communication: "voice_chat",
    openness_to_new_users: "open"
  }
];

// Mock function to handle the new endpoint
export const findPlayers = async (userId, gameName) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  
  // Filter out the current user
  const filteredPlayers = mockPlayers.filter(player => player.id !== userId);
  
  if (!gameName) {
    return filteredPlayers;
  }
  
  // Filter players who have the selected game in their games array
  return filteredPlayers.filter(player => 
    player.games.some(g => g.toLowerCase() === gameName.toLowerCase())
  );
};

// Keep the old function for backward compatibility
export const searchPlayers = async game => {
  return findPlayers("", game);
};
