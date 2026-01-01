// src/api/entities.js
import { z } from "zod"; // Import zod for schema definition and validation

/**
 * Zod Schemas for Application Entities
 *
 * These schemas define the expected structure and types for data
 * flowing through your application, especially data received from
 * the backend API. Using Zod provides runtime validation and helps
 * ensure data consistency.
 *
 * You can extend these schemas or create new ones for other entities
 * as your application grows.
 */

// ---------------------------------------------------------------------
// Core User Profile Schema
// ---------------------------------------------------------------------
export const UserSchema = z.object({
  id: z.string().uuid(), // Unique identifier for the user (UUID format)
  username: z.string().min(3, "Username must be at least 3 characters long."),
  email: z.string().email("Invalid email address.").optional(), // Changed to optional as email might not always be present or valid initially
  avatarUrl: z.string().url("Invalid avatar URL.").optional(), // Optional avatar image URL
  bio: z.string().max(500, "Bio cannot exceed 500 characters.").optional(), // Optional user biography
  createdAt: z.string().datetime(), // ISO 8601 datetime string for creation time
  updatedAt: z.string().datetime() // ISO 8601 datetime string for last update time
});

/**
 * Infer the TypeScript type from the Zod schema.
 * This is incredibly useful for type-checking in your React components.
 * @typedef {z.infer<typeof UserSchema>} UserType // Renamed to avoid conflict
 */

// Export the UserSchema under the alias User to satisfy the import in Layout.jsx
// Note: In Layout.jsx, 'User' will now refer to the Zod schema object itself.
export { UserSchema as User };

// ---------------------------------------------------------------------
// Game Schema
// ---------------------------------------------------------------------
export const GameSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1, "Game name cannot be empty."),
  description: z.string().optional(),
  imageUrl: z.string().url("Invalid game image URL.").optional(),
  minPlayers: z.number().int().positive("Minimum players must be a positive integer.").optional(),
  maxPlayers: z.number().int().positive("Maximum players must be a positive integer.").optional()
});

/**
 * @typedef {z.infer<typeof GameSchema>} Game
 */

// ---------------------------------------------------------------------
// Player Profile Schema (might be a subset or extended User data for games)
// ---------------------------------------------------------------------
export const PlayerSchema = z.object({
  id: z.string().uuid(), // Player's unique ID
  username: z.string(),   // Player's username
  avatarUrl: z.string().url().optional(), // Player's avatar
  status: z.enum(["online", "offline", "playing", "away"]), // Current status
  gamesOwned: z.array(GameSchema).optional(), // Array of games the player owns/plays
  rating: z.number().int().min(0).optional() // Optional game-specific rating
});

/**
 * @typedef {z.infer<typeof PlayerSchema>} Player
 */

// ---------------------------------------------------------------------
// Game Request Schema (e.g., a challenge to play)
// ---------------------------------------------------------------------
export const GameRequestSchema = z.object({
  id: z.string().uuid(),
  requesterId: z.string().uuid(),
  requesterUsername: z.string(),
  receiverId: z.string().uuid(),
  receiverUsername: z.string(),
  game: GameSchema, // The game being requested
  status: z.enum(["pending", "accepted", "rejected", "cancelled"]),
  requestedAt: z.string().datetime(),
  expiresAt: z.string().datetime().optional()
});

/**
 * @typedef {z.infer<typeof GameRequestSchema>} GameRequestType // Renamed to avoid conflict
 */

// Export the GameRequestSchema under the alias GameRequest to satisfy the import in RequestModal.jsx
export { GameRequestSchema as GameRequest };

// ---------------------------------------------------------------------
// Session Schema (e.g., a scheduled or ongoing game session)
// ---------------------------------------------------------------------
export const SessionSchema = z.object({
  id: z.string().uuid(),
  game: GameSchema,
  hostId: z.string().uuid(),
  hostUsername: z.string(),
  participants: z.array(z.string().uuid()), // Array of participant user IDs
  scheduledTime: z.string().datetime().optional(), // When the session is scheduled
  startTime: z.string().datetime().optional(), // When the session actually started
  endTime: z.string().datetime().optional(),   // When the session ended
  status: z.enum(["scheduled", "active", "completed", "cancelled"]),
  location: z.string().optional() // E.g., a link to a game server or voice chat
});

/**
 * @typedef {z.infer<typeof SessionSchema>} Session
 */

// Export the SessionSchema under the alias ScheduledSession to satisfy the import in Dashboard.jsx
export { SessionSchema as ScheduledSession }; // <--- ADDED LINE

// ---------------------------------------------------------------------
// Example of a utility function that might live here (less common, but possible)
// ---------------------------------------------------------------------

/**
 * Validates a user object against the UserSchema.
 * This can be used to validate data received from API calls.
 * @param {any} userData - The data to validate.
 * @returns {UserType} The validated user object.
 * @throws {z.ZodError} If validation fails.
 */
export const validateUser = userData => {
  return UserSchema.parse(userData);
};

/**
 * Validates a game request object against the GameRequestSchema.
 * @param {any} requestData - The data to validate.
 * @returns {GameRequestType} The validated game request object.
 * @throws {z.ZodError} If validation fails.
 */
export const validateGameRequest = requestData => {
  return GameRequestSchema.parse(requestData);
};

// You can add more validation functions for other schemas as needed.
