import { Gamepad2, Plus } from "lucide-react";

export default function GameList({ games }) {
  return (
    <div className="calm-card h-full bg-gradient-to-br from-purple-50 to-indigo-50 border-purple-200">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Gamepad2 className="w-5 h-5 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-800">Favorite Games</h3>
        </div>
        <button className="p-2 bg-white/80 hover:bg-white rounded-lg transition-colors shadow-sm">
          <Plus className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      <div className="space-y-3">
        {games.map((game, index) => (
          <div key={game} className="group bg-white/80 backdrop-blur-sm border border-purple-100 rounded-xl p-4 hover:shadow-md hover:bg-white transition-all duration-200">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-100 to-purple-200 rounded-lg flex items-center justify-center group-hover:from-purple-200 group-hover:to-purple-300 transition-all">
                <span className="text-lg font-semibold text-purple-700">
                  {game.charAt(0)}
                </span>
              </div>
              <div className="flex-1">
                <span className="font-semibold text-gray-800 group-hover:text-purple-700 transition-colors">
                  {game}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>


    </div>
  );
}
