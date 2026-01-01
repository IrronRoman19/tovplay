import { Gamepad2, Clock, Check, X } from "lucide-react";
import PropTypes from "prop-types";
import { useContext } from "react";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { format } from "useful-time";

import { Link } from "react-router-dom";

export default function GameRequestSentCard({
  request,
  onCancel,
  actionState
}) {
  
  const { t, language } = useContext(LanguageContext);
  const isRTL = language === 'he';
  const time = new Date(request.suggested_time.replace("_", " "));
  //const formattedTime = `${time.toLocaleDateString(undefined, { weekday: "long" })} ${time.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false })}`;
  const formattedTime = format({to:time, style:"compact"});

  const isLoading = actionState?.loading;
  const isError = actionState?.error;
  const loadingType = actionState?.type;

  const rawTitle = t('gameRequestSentCard.youAsked', { username: "___USERNAME___" });
  const titleParts = rawTitle.split("___USERNAME___");

  return (
    <div className="bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm p-4 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm transition-all hover:shadow-md">
      <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mb-2">
        {titleParts[0]}
        <Link
          to={`/profile?username=${request.recipient_username}`}
          className="hover:text-teal-600 dark:hover:text-teal-400 hover:underline transition-colors"
        >
          {request.recipient_username}
        </Link>
        {titleParts[1]}
      </p>

      <div className={`flex items-center text-sm text-gray-600 dark:text-gray-300 mb-3 ${isRTL ? 'space-x-reverse' : ''} space-x-4`}>
        <div className={`flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
          <Gamepad2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
          <span>{request.game}</span>
        </div>
        <div className={`flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
          <Clock className="w-4 h-4 text-teal-600 dark:text-teal-400" />
          <span>{formattedTime.text}</span>
        </div>
      </div>

      {request.message && (
        <div className="text-sm text-gray-500 dark:text-gray-300 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md mb-4 italic">
          &quot;{request.message}&quot;
        </div>
      )}

      <div className={`flex ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
        <button
          onClick={() => onCancel(request.id)}
          className={`flex-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all font-semibold flex items-center justify-center text-sm px-3 py-2 rounded-lg ${isRTL ? 'space-x-reverse' : ''} space-x-2 ${isLoading ? "opacity-70 cursor-not-allowed" : ""}}`}
          disabled={isLoading}
        >
          {isLoading && loadingType === "decline" ? (
            <span className="animate-spin mr-2 w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full"></span>
          ) : isError && loadingType === "decline" ? (
            <X className="w-4 h-4 text-red-500" />
          ) : (
            <X className="w-4 h-4" />
          )}
          <span>{t('gameRequestSentCard.cancelRequest')}</span>
        </button>
        {/* <button
          onClick={() => onAccept(request.id)}
          className={`flex-1 bg-teal-500 text-white hover:bg-teal-600 transition-all font-semibold flex items-center justify-center space-x-2 text-sm px-3 py-2 rounded-lg ${isLoading ? "opacity-70 cursor-not-allowed" : ""}`}
          disabled={isLoading}
        >
          {isLoading && loadingType === "accept" ? (
            <span className="animate-spin mr-2 w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
          ) : isError && loadingType === "accept" ? (
            <X className="w-4 h-4 text-red-500" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          <span>Accept</span>
        </button> */}
      </div>
    </div>
  );
}

GameRequestSentCard.propTypes = {
  request: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    sender_username: PropTypes.string.isRequired,
    game: PropTypes.string.isRequired,
    suggested_time: PropTypes.string.isRequired,
    message: PropTypes.string
  }).isRequired,
  onAccept: PropTypes.func.isRequired,
  onDecline: PropTypes.func.isRequired,
  actionState: PropTypes.shape({
    loading: PropTypes.bool,
    error: PropTypes.bool,
    type: PropTypes.oneOf(["accept", "decline", null])
  })
};
