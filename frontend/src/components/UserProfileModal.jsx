
import { User, Gamepad2, MessageSquare, Mic, VolumeX, Users, AlertTriangle, Shield, X, Globe } from "lucide-react";

const CommIcon = ({ preference }) => {
  switch (preference) {
    case "written_messages": return <MessageSquare className="w-4 h-4 text-gray-600" />;
    case "voice_messages": return <Mic className="w-4 h-4 text-gray-600" />;
    case "prefer_no_talking": return <VolumeX className="w-4 h-4 text-gray-600" />;
    default: return null;
  }
};

const OpennessIcon = ({ openness }) => {
  switch (openness) {
    case "open": return <Users className="w-4 h-4 text-gray-600" />;
    case "careful": return <AlertTriangle className="w-4 h-4 text-gray-600" />;
    case "only_previous": return <Shield className="w-4 h-4 text-gray-600" />;
    default: return null;
  }
};

const preferenceLabels = {
  written_messages: "Written Messages",
  voice_messages: "Voice Messages",
  prefer_no_talking: "No Talking",
  open: "Open to new users",
  careful: "Careful with new users",
  only_previous: "Only previous contacts"
};


export default function UserProfileModal({ player, onClose }) {
  if (!player) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-[99990]"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md relative animate-in fade-in-0 zoom-in-95"
        onClick={e => e.stopPropagation()}
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors">
          <X className="w-6 h-6" />
        </button>

        {/* Header */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-24 h-24 bg-gradient-to-br from-teal-100 to-teal-200 rounded-full flex items-center justify-center mb-4 shadow-lg">
            {player.profilePhoto ? (
              <img src={player.profilePhoto} alt="Profile" className="w-full h-full object-cover rounded-full" />
            ) : (
              <User className="w-12 h-12 text-teal-600" />
            )}
          </div>
          <h2 className="text-2xl font-bold text-gray-800">{player.username}</h2>
          {player.description && (
            <p className="text-sm text-gray-600 mt-2 max-w-xs">
              {player.description}
            </p>
          )}
        </div>

        <div className="space-y-4">
          {/* Languages */}
          {player.languages && player.languages.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
                <Globe className="w-4 h-4 mr-2 text-gray-400" />
                Languages
              </h3>
              <div className="flex flex-wrap gap-2">
                {player.languages.map((language, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium"
                  >
                    {language}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Games */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center">
              <Gamepad2 className="w-4 h-4 mr-2 text-gray-400" />
              Plays
            </h3>
            <div className="flex flex-wrap gap-2">
              {player.games.map((game, index) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-gray-100 text-gray-700 text-xs rounded-full font-medium"
                >
                  {game}
                </span>
              ))}
            </div>
          </div>

          {/* Preferences */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Preferences</h3>
            <div className="space-y-2">
              <div className="flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
                <CommIcon preference={player.preferred_communication} />
                <span className="text-sm text-gray-800">{preferenceLabels[player.preferred_communication]}</span>
              </div>
              <div className="flex items-center space-x-3 p-2 bg-gray-50 rounded-lg">
                <OpennessIcon openness={player.openness_to_new_users} />
                <span className="text-sm text-gray-800">{preferenceLabels[player.openness_to_new_users]}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
