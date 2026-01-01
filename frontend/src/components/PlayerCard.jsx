import { User, Globe, Gamepad2, MessageCircle, Check, Clock, MessageSquare, Mic, BellOff, MessageCircleQuestion, Languages } from "lucide-react";
import PropTypes from "prop-types";
import { useState, useContext, useMemo } from "react";
import { LanguageContext } from "@/components/lib/LanguageContext";
import RequestModal from "./RequestModal";
import UserProfileModal from "./UserProfileModal";
import apiService from "@/api/apiService";

// Language options with codes, translation keys, and default names
const languageOptions = [
  { code: 'en', key: 'languages.english', defaultName: 'English' },
  { code: 'he', key: 'languages.hebrew', defaultName: 'עברית' },
  { code: 'ar', key: 'languages.arabic', defaultName: 'العربية' },
  { code: 'ru', key: 'languages.russian', defaultName: 'Русский' },
  { code: 'am', key: 'languages.amharic', defaultName: 'አማርኛ' }
];

// Create a map for quick lookup by code
const languageMap = languageOptions.reduce((acc, lang) => {
  acc[lang.code] = lang.key;
  return acc;
}, {});

// Helper function to convert API language format to array of translated language names
const parseLanguageString = (langString, t) => {
  if (!langString) {
    return [];
  }
  
  try {
    // Handle both string format (e.g., "{he,en}") and array format
    const codes = typeof langString === 'string' 
      ? langString.replace(/[{}]/g, '').split(',').map(lang => lang.trim())
      : Array.isArray(langString) 
        ? langString.map(lang => typeof lang === 'string' ? lang.trim() : '')
        : [];

    // Map codes to their translated names
    return codes.map(code => {
      if (!code) return null;
      
      // Find the language option that matches the code
      const langOption = languageOptions.find(lang => lang.code === code.toLowerCase());
      
      // If we found a matching language option, return its translated name
      if (langOption) {
        return t(langOption.key, langOption.defaultName);
      }
      
      // If no matching option found, try to find by key (for backward compatibility)
      const langByKey = languageOptions.find(lang => 
        lang.key.toLowerCase() === `languages.${code.toLowerCase()}`
      );
      
      if (langByKey) {
        return t(langByKey.key, langByKey.defaultName);
      }
      
      // If still no match, return the code as is
      return code;
    }).filter(Boolean); // Remove any null/undefined values
  } catch (error) {
    console.error('Error parsing language string:', error, langString);
    return [];
  }
};

// Helper function to translate communication preferences
const translateCommunicationPref = (pref, t) => {
  if (!pref) return '';
  
  const prefMap = {
    'Written': 'profile.communication.text',
    'Voice': 'profile.communication.voice',
    'NoTalking': 'profile.communication.minimal',
    'Text chat only': 'profile.communication.text',
    'Voice chat': 'profile.communication.voice',
    'Minimal chat': 'profile.communication.minimal'
  };
  
  return t(prefMap[pref] || pref);
};

// Helper function to translate day names
const translateDay = (day, t) => {
  if (!day) return '';
  const dayLower = day.toLowerCase();
  return t(dayLower);
};

export default function PlayerCard({ player, currentUser, contextGame, isOnline }) {
  const { t, language } = useContext(LanguageContext);
  const isRTL = language === 'he';
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [gameRequestSent, setGameRequestSent] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showAllGames, setShowAllGames] = useState(false);

  //
  const showRequestModalWithDiscordVerify = async () => {
    // Implement Discord verification logic here
    const JWTToken = localStorage.getItem('authToken');
    try {

      // check api if user is in_community
      const data = await apiService.checkCommunityStatus();

      // if not in community, open discord auth url
      if (data.is_in_community) {
        debugger;
        setShowRequestModal(true);
        return;
      }
      else {

        const CLIENT_ID = import.meta.env.VITE_DISCORD_CLIENT_ID;
        const REDIRECT_URI = encodeURIComponent(import.meta.env.VITE_DISCORD_REDIRECT_URI);
        const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

        const discord_auth_url = `${VITE_API_BASE_URL}/api/auth/discord/login?is_login_page=false&state=${localStorage.getItem('userId')}`;

        window.open(discord_auth_url, '_blank');

        debugger;
        return;
      }
    }
    catch (error) {
      debugger;
    }
  }  



  // Format available slots for display
  // If no available slots and not online, show "Offline"
  const hasNoAvailability = !player?.available_slots?.length;
  const formattedAvailableSlots = player?.available_slots?.length > 0
    ? player.available_slots
      .slice(0, 3) // Show only first 3 slots
      .map(slot => `${translateDay(slot.day, t)} ${slot.hour}`)
      .join(", ")
    : (isOnline ? t("noAvailableSlots") : t("offline"));

  const handleGameRequestSent = () => {
    setGameRequestSent(true);
    // Don't close the modal here, let the RequestModal handle it after the success state
    console.log("Game request sent successfully");

    // Reset the button text after 3 seconds
    setTimeout(() => {
      setGameRequestSent(false);
    }, 3000);
  };

  const handleCloseModal = () => {
    setShowRequestModal(false);
    // Reset the button text when modal is closed
    setGameRequestSent(false);
  };

  // Helper function to find shared languages
  const getSharedLanguages = () => {
    player.languages = player?.profile?.language || player.languages;
    if (!currentUser?.languages || !player?.languages ) {
      return [];
    }
    return currentUser.languages.filter(lang => player.languages.includes(lang));
  };

  const sharedLanguages = getSharedLanguages();

  return (
    <>
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 transition-all duration-300 hover:shadow-xl border border-gray-100 dark:border-gray-700">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-4">
            <div className="relative">
              <div className="w-12 h-12 bg-gradient-to-br from-teal-50 to-teal-100 dark:from-teal-900/30 dark:to-teal-800/30 rounded-full flex items-center justify-center overflow-hidden">
                {player.user_profile_pic ? (
                  <img
                    src={player.user_profile_pic}
                    alt={player.username}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User className="w-6 h-6 text-teal-600 dark:text-teal-400" />
                )}
              </div>
              {isOnline ? (
                <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
              ) : hasNoAvailability && (
                <div className="absolute bottom-0 right-0 w-3 h-3 bg-gray-400 rounded-full border-2 border-white"></div>
              )}
            </div>
            <div>
              <button 
                onClick={() => setShowProfileModal(true)} 
                className={`flex items-center text-left bg-transparent border-none p-0 m-0 cursor-pointer ${isRTL ? 'space-x-reverse' : ''} space-x-2`}
              >
                <h3 className="font-bold text-lg text-gray-800 dark:text-gray-100 hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                  {player.username}
                </h3>
              </button>
              <div className={`flex items-start text-sm ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
                <Gamepad2 className="w-4 h-4 flex-shrink-0 mt-0.5 text-gray-600" />
                <div className="flex flex-wrap gap-1">
                  {player.games?.length > 0 ? (
                    <>
                      {player.games.slice(0, showAllGames ? player.games.length : 3).map((game, index) => (
                        <span key={index} className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-100 dark:bg-teal-900/50 text-teal-800 dark:text-teal-200">
                          {game}
                        </span>
                      ))}
                      {player.games.length > 3 && (
                        <button
                          onClick={() => setShowAllGames(!showAllGames)}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 hover:bg-teal-100 dark:hover:bg-teal-800/50 transition-colors"
                        >
                          {showAllGames ? t("showLess") : t("moreCount", { count: player.games.length - 3 })}
                        </button>
                      )}
                    </>
                  ) : (
                    <span className="text-gray-400 dark:text-gray-500 text-xs">{t("noGamesSelected")}</span>
                  )}
                </div>
              </div>
              {player.communication_preferences && (
                <div className={`flex items-center text-sm text-gray-500 ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
                  {player.communication_preferences === "Written" || player.communication_preferences === "Written Messages" ? (
                    <MessageSquare className="w-4 h-4 flex-shrink-0" />
                  ) : player.communication_preferences === "Voice" || player.communication_preferences === "Voice Messages" ? (
                    <Mic className="w-4 h-4 flex-shrink-0" />
                  ) : player.communication_preferences === "NoTalking" || player.communication_preferences === "Prefer No Talking" ? (
                    <BellOff className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <MessageCircleQuestion className="w-4 h-4 flex-shrink-0" />
                  )}
                  <span>{t(`profile.communicationMap.${player.communication_preferences.toLowerCase()}`)}</span>
                </div>
              )}
              <div className={`flex items-start text-sm text-gray-500 dark:text-gray-400 ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
                <Clock className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span className="line-clamp-2">{formattedAvailableSlots}</span>
              </div>

              {/* Languages */}
              <div className={`flex items-start text-sm text-gray-500 dark:text-gray-400 ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
                <Languages className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div className="flex flex-wrap gap-1">
                  {(() => {
                    if (!player.languages) {
                      return <span className="text-gray-400 dark:text-gray-500 text-xs">{t("noLanguagesSelected")}</span>;
                    }
                    
                    const translatedLangs = parseLanguageString(player.languages, t);
                    if (translatedLangs.length === 0) {
                      return <span className="text-gray-400 dark:text-gray-500 text-xs">{t("noLanguagesSelected")}</span>;
                    }
                    
                    return translatedLangs.map((lang, index) => (
                      <span 
                        key={index} 
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                      >
                        {lang}
                      </span>
                    ));
                  })()}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-3 mb-5">
          {/* Languages */}
          {sharedLanguages.length > 0 && (
            <div>
              <p className={`text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
                <Globe className="w-4 h-4 text-gray-400" />
                {t("sharedLanguages")}
              </p>
              <div className="flex flex-wrap gap-2">
                {sharedLanguages.map((language, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs rounded-full font-medium"
                  >
                    {language}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className={`flex ${isRTL ? 'space-x-reverse' : ''} space-x-2`}>
          <button
            onClick={() => setShowRequestModal(true)}
            disabled={gameRequestSent}
            className={`flex-1 font-semibold flex items-center justify-center text-sm px-3 py-2.5 rounded-lg transition-all ${isRTL ? 'space-x-reverse' : ''} space-x-2 ${
              gameRequestSent
                ? "bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300"
                : "bg-teal-600 dark:bg-teal-700 text-white hover:bg-teal-700 dark:hover:bg-teal-600"
            }`}
          >
            {gameRequestSent ? <Check className="w-4 h-4" /> : <MessageCircle className="w-4 h-4" />}
            <span>{gameRequestSent ? t("requestSent") : t("requestToPlay")}</span>
          </button>
        </div>
      </div>

      {showRequestModal && (
        <RequestModal
          player={player}
          currentUser={currentUser}
          game={contextGame || (player.games && player.games[0]) || "Game"}
          onClose={handleCloseModal}
          onSuccess={handleGameRequestSent}
        />
      )}

      {showProfileModal && (
        <UserProfileModal
          player={player}
          onClose={() => setShowProfileModal(false)}
        />
      )}
    </>
  );
}

PlayerCard.propTypes = {
  player: PropTypes.shape({
    id: PropTypes.string.isRequired,
    username: PropTypes.string.isRequired,
    user_profile_pic: PropTypes.string,
    games: PropTypes.arrayOf(PropTypes.string),
    communication_preferences: PropTypes.string,
    available_slots: PropTypes.arrayOf(PropTypes.shape({
      day: PropTypes.string,
      hour: PropTypes.string
    })),
    languages: PropTypes.string
  }).isRequired,
  currentUser: PropTypes.shape({
    username: PropTypes.string.isRequired,
    languages: PropTypes.arrayOf(PropTypes.string)
  }),
  contextGame: PropTypes.string,
  isOnline: PropTypes.bool,
  onPlayClick: PropTypes.func.isRequired
};
