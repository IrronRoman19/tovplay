const now = new Date();
const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000);
const tenMinutesAgo = new Date(now.getTime() - 10 * 60 * 1000);
const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

export const samplePlayers = [
  {
    username: "GamerAlex",
    id: "a4dc94f1-a3cb-4ba5-956b-91165d88e0dd",
    games: ["Minecraft", "Stardew Valley", "Chess", "Rocket League"],
    languages: ["English", "Hebrew"],
    availability: {
      "Saturday-14:00": true, "Saturday-15:00": true, "Saturday-16:00": true,
      "Sunday-19:00": true, "Sunday-20:00": true, "Sunday-21:00": true
    },
    timezone: "EST",
    friends: ["CozyGamer"],
    last_seen: now.toISOString(),
    prefers_custom_availability: false,
    description: "Loves playing cozy games and strategy challenges. Looking for relaxed teammates!",
    profilePhoto: "",
    preferred_communication: "written_messages",
    openness_to_new_users: "open"
  },
  {
    username: "CozyGamer",
    id: "a4dc94f1-a3cb-4ba5-956b-91165d88e0dd",
    games: ["Animal Crossing", "Stardew Valley", "Among Us", "Chess"],
    languages: ["English", "Russian"],
    availability: {
      "Monday-20:00": true, "Tuesday-20:00": true, "Wednesday-20:00": true,
      "Sunday-20:00": true,
      "Friday-21:00": true, "Friday-22:00": true
    },
    timezone: "PST",
    friends: ["GamerAlex", "BuilderBee"],
    last_seen: fiveMinutesAgo.toISOString(),
    prefers_custom_availability: false,
    description: "Enjoys casual and social games. Always up for a friendly match.",
    profilePhoto: "",
    preferred_communication: "written_messages",
    openness_to_new_users: "open"
  },
  {
    username: "ChessPlayer99",
    games: ["Chess", "Checkers", "Scrabble"],
    languages: ["English", "Arabic"],
    availability: {
      "Wednesday-14:00": true, "Wednesday-15:00": true, "Thursday-14:00": true, "Thursday-15:00": true
    },
    timezone: "GMT",
    friends: [],
    last_seen: tenMinutesAgo.toISOString(),
    prefers_custom_availability: true,
    description: "Competitive chess player seeking worthy opponents.",
    profilePhoto: "",
    preferred_communication: "prefer_no_talking",
    openness_to_new_users: "careful"
  },
  {
    username: "BuilderBee",
    games: ["Minecraft", "Terraria", "Cities: Skylines"],
    languages: ["Hebrew", "English", "Amharic"],
    availability: {
      "Friday-9:00": true, "Friday-10:00": true, "Saturday-15:00": true,
      "Saturday-10:00": true, "Saturday-11:00": true
    },
    timezone: "EST",
    friends: ["CozyGamer"],
    last_seen: oneDayAgo.toISOString(),
    prefers_custom_availability: false,
    description: "Loves to build amazing creations in sandbox games.",
    profilePhoto: "",
    preferred_communication: "voice_messages",
    openness_to_new_users: "open"
  }
];
