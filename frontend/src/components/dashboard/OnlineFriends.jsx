import { User, Sparkles } from "lucide-react";
import { useContext } from "react";
import { Link } from "react-router-dom";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { createPageUrl } from "@/utils";
// import { LanguageContext } from "@/contexts/LanguageContext";

export default function OnlineFriends({ onlinePlayers }) {
  const { t } = useContext(LanguageContext);

  return (
    <div className="calm-card">
      <div className="flex items-center space-x-3 mb-4">
        <Sparkles className="w-6 h-6 text-teal-600" />
        <h2 className="text-xl font-semibold text-gray-800">{t("onlineNow")}</h2>
      </div>
      {onlinePlayers.length > 0 ? (
        <div className="flex -space-x-3">
          {onlinePlayers.map(player => (
            <Link to={createPageUrl(`UserProfile?username=${player.username}`)} key={player.username}>
              <div className="w-12 h-12 bg-gray-200 rounded-full border-2 border-white flex items-center justify-center hover:ring-4 hover:ring-teal-200 transition-all cursor-pointer" title={player.username}>
                <User className="w-6 h-6 text-gray-500" />
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">{t("noFriendsOnline")}</p>
      )}
    </div>
  );
}
