import { Crown, Users, Search, ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import PlayerCard from "../components/PlayerCard";
import { samplePlayers } from "../components/data/samplePlayers";
import { createPageUrl } from "@/utils";

export default function ChessPlayers() {
  const [sortBy, setSortBy] = useState("username");

  // Filter players who play chess
  const chessPlayers = samplePlayers.filter(player =>
    player.games.some(game => game.toLowerCase().includes("chess"))
  );

  // Sort players based on selected criteria
  const sortedPlayers = [...chessPlayers].sort((a, b) => {
    switch (sortBy) {
      case "username":
        return a.username.localeCompare(b.username);
      case "friends":
        return b.friends.length - a.friends.length;
      case "games":
        return b.games.length - a.games.length;
      default:
        return 0;
    }
  });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <div className="flex items-center space-x-4 mb-4">
          <Link to={createPageUrl("FindPlayers")}>
            <button className="flex items-center space-x-2 text-gray-600 hover:text-gray-800 transition-colors">
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Find Players</span>
            </button>
          </Link>
        </div>

        <div className="flex items-center space-x-3 mb-2">
          <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
            <Crown className="w-6 h-6 text-amber-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800">Chess Players</h1>
        </div>
        <p className="text-gray-600">
          Connect with fellow chess enthusiasts on TovPlay. All players listed here enjoy playing chess.
        </p>
      </div>

      <div className="calm-card mb-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-3">
            <Users className="w-5 h-5 text-teal-600" />
            <span className="font-semibold text-gray-800">
              {chessPlayers.length} Chess Player{chessPlayers.length !== 1 ? "s" : ""} Found
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Sort by:</label>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-teal-500"
            >
              <option value="username">Username (A-Z)</option>
              <option value="friends">Most Friends</option>
              <option value="games">Most Games</option>
            </select>
          </div>
        </div>
      </div>

      {chessPlayers.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedPlayers.map(player => (
            <div key={player.username} className="relative">
              <PlayerCard player={player} />
              {/* Chess specialty badge */}
              <div className="absolute -top-2 -right-2 bg-amber-500 text-white rounded-full p-2 shadow-lg">
                <Crown className="w-4 h-4" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="calm-card text-center py-16">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-800 mb-2">No Chess Players Found</h3>
          <p className="text-gray-600 max-w-md mx-auto">
            It looks like there aren't any chess players available right now.
            Check back later or try searching for other games.
          </p>
          <Link to={createPageUrl("FindPlayers")} className="inline-block mt-4">
            <button className="calm-button">
              Explore Other Games
            </button>
          </Link>
        </div>
      )}

      <div className="mt-12 bg-amber-50 p-6 rounded-lg">
        <div className="flex items-center space-x-3 mb-4">
          <Crown className="w-6 h-6 text-amber-600" />
          <h3 className="text-lg font-semibold text-gray-800">About Chess on TovPlay</h3>
        </div>
        <div className="grid md:grid-cols-2 gap-6 text-sm text-gray-700">
          <div>
            <h4 className="font-medium mb-2">Perfect for All Skill Levels</h4>
            <p>Whether you're a beginner learning the basics or a seasoned player,
              our chess community welcomes everyone at their own pace.</p>
          </div>
          <div>
            <h4 className="font-medium mb-2">Comfortable Gaming</h4>
            <p>Play in a pressure-free environment where you can take your time,
              learn from others, and enjoy the strategic beauty of chess.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
