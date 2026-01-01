import { Calendar, Clock, Users, Gamepad2, ChevronLeft, ChevronRight } from "lucide-react";
import { useContext } from "react";
import { Link } from "react-router-dom";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { createPageUrl } from "@/utils";
import { formatToParts } from "useful-time";
import { func } from "prop-types";

export default function UpcomingSessionCard({ session , cancleGameFn, joinGameFn, onNext, onPrev, canNext, canPrev }) {
  const { t, locale } = useContext(LanguageContext);
  const isRTL = locale?.direction === 'rtl';
  

  if (!session) {
    return (
      <div className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm p-8 rounded-2xl text-center border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
          <Calendar className="w-8 h-8 text-gray-400 dark:text-gray-300" />
        </div>
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">{t("noUpcomingSessions")}</h3>
        <p className="text-gray-500 dark:text-gray-300 mt-2">{t("noUpcomingSessionsDesc")}</p>
        <Link to={createPageUrl("FindPlayers")}>
          <button className="mt-4 px-6 py-2 bg-teal-500 dark:bg-teal-600 text-white font-semibold rounded-lg hover:bg-teal-600 dark:hover:bg-teal-500 transition-colors">
            {t("findPlayers")}
          </button>
        </Link>
      </div>
    );
  }

  function getLinkText( session) {
    function nameFromId(userId) {
      if(userId === session.organizer_user_id)
        return session.organizer_user_name;
      if(userId === session.second_player_id)
        return session.second_player_name;
      return userId;
    }

    let data;
    if(typeof session.meeting_link === "string")
    {
      data = session.meeting_link.trim();
      if(data.startsWith("http")) return data;
      if(!['{',"'",'"'].includes(data[0])) return t("unexpectedLinkFormat", {data});
      try {
        data = JSON.parse(data);
      } catch (e) {
        return t("unexpectedLinkFormat", {data});
      }
      if(typeof data === "string")
      {
        session.meeting_link = data;
        return getLinkText( session);
      };
    }
    else if(typeof session.meeting_link === "object" && session.meeting_link !== null)
    {
      data = session.meeting_link;
    }
    else
    {
      return t("unexpectedLinkFormat", {data:session.meeting_link});
    }
    // at this point data can only be an object, which indecates an error
    if(data.notInGuild)
    {
      let ret = []
      for(const userId of data.notInGuild) 
      {
        ret.push(t("userNotInGuild", {name: nameFromId(userId)}));
      }
      ret.push(t("userNotInGuildDesc")+'.');
      return ret.join(". ");
    }
    
    if(data.GuildError)
    {
      return  t("discordBotError");
    }

    if(data.UnknownError)
    {
      return t("unexpectedMeeetingError", {data: data.message});
    }

    return t("unexpectedLinkFormat", {data:session.meeting_link});
  }

  const time = new Date(session.scheduled_date + " " + session.start_time);
  const formattedparts = formatToParts({to:time, style:"long"});
  const gamelinkText = getLinkText(session);
  const gamelink_is_link = gamelinkText === "string" &&
                            gamelinkText.startsWith("http");

  return (
    <div className="bg-gradient-to-br from-teal-500 to-teal-600 dark:from-teal-600 dark:to-teal-700 p-8 rounded-2xl shadow-xl text-white relative">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-teal-100 dark:text-teal-50 mb-2">{t("nextUp")}</p>
          <a href={session.game_site_url} target='_blank' rel="noopener noreferrer"><h2 className="text-3xl font-bold mb-4">{session.game_name}</h2></a>
        </div>
        <div className="flex items-center [&>*:not(:first-child)]:ms-2">
          <button
            onClick={isRTL ? onNext : onPrev}
            disabled={isRTL ? !canNext : !canPrev}
            className={`p-2 rounded-md bg-white/20 hover:bg-white/30 transition-colors ${(isRTL ? !canNext : !canPrev) ? 'opacity-40 cursor-not-allowed' : ''}`}
            aria-label={isRTL ? "next-session" : "previous-session"}
          >
            {isRTL ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
          <button
            onClick={isRTL ? onPrev : onNext}
            disabled={isRTL ? !canPrev : !canNext}
            className={`p-2 rounded-md bg-white/20 hover:bg-white/30 transition-colors ${(isRTL ? !canPrev : !canNext) ? 'opacity-40 cursor-not-allowed' : ''}`}
            aria-label={isRTL ? "previous-session" : "next-session"}
          >
            {isRTL ? <ChevronLeft className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>
        </div>
      </div>

      <div className="flex flex-col space-y-3 text-teal-50 dark:text-teal-100 mb-6">
        <div className={`flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-3`}>
          <Users className="w-5 h-5 text-teal-200 dark:text-teal-100" />
          <span className="font-medium">
            {t("playingWith", { 
              player: session.participants 
                ? [...new Set(session.participants)].join(", ") 
                : "Unknown" 
            })}
          </span>
        </div>
        <div className="flex flex-row gap-2">
          {formattedparts.map(({type, value}, index) => {
            if(type === "date")
              return (<><Calendar className="w-5 h-5 text-teal-200 dark:text-teal-100" />{value}&nbsp;</>)
            if(type === "time")
              return (<><Clock className="w-5 h-5 text-teal-200 dark:text-teal-100" />{value}&nbsp;</>)
            return (<>{value}</>)
          })}
        </div>
        <div className={`flex items-center ${isRTL ? 'space-x-reverse' : ''} space-x-3`}>
          <Gamepad2 className="w-5 h-5" />
          {gamelink_is_link ? (
            <a href={gamelinkText} target="_blank" rel="noopener noreferrer" className="underline font-medium">
              <span className="font-medium">{gamelinkText}</span>
            </a>
          ) : (
            <span className="font-medium">{gamelinkText}</span>
          )}
        </div>
      </div>

      <div className={`flex ${isRTL ? 'space-x-reverse' : ''} space-x-3`}>
        {/* <button className="flex-1 bg-white/90 dark:bg-white/80 text-teal-600 dark:text-teal-700 font-bold py-3 rounded-lg hover:bg-white dark:hover:bg-white/90 transition-all">
          {t("joinGame")}
        </button> */}
        <button className="flex-1 bg-white/90 text-teal-600 font-bold py-3 rounded-lg hover:bg-white transition-all"
          onClick={cancleGameFn}>
          {t("cancleGame")}
        </button>
      </div>
    </div>
  );
}
