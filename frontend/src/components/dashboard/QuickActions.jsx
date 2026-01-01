import { Calendar, Users, Settings, Star } from "lucide-react";
import PropTypes from "prop-types";
import { useContext } from "react";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { createPageUrl } from "@/utils";

export default function QuickActions({ track, page, identify }) {
  const { t } = useContext(LanguageContext);
  const username = useSelector(state => state.profile.username);
  const email = useSelector(state => state.profile.email);

  const actions = [
    {
      nameKey: "setYourSchedule",
      path: "Schedule",
      icon: Calendar,
      onClick: () => page && page()
    },
    {
      nameKey: "findPlayers",
      path: "FindPlayers",
      icon: Users,
      onClick: () => track && track("find_players_clicked")
    },
    {
      nameKey: "comfortSettings",
      path: "Settings",
      icon: Settings,
      onClick: () => identify && identify(username, { email })
    }
  ];

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <Star className="w-6 h-6 text-teal-600 dark:text-teal-400" />
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{t("quickActions")}</h2>
      </div>
      <div className="space-y-3">
        {actions.map(action => (
          <Link
            key={action.nameKey}
            to={createPageUrl(action.path)}
            onClick={() => action.onClick()}
            className="block p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <div className="flex items-center gap-4">
              <div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg">
                <action.icon className="w-5 h-5 text-teal-600 dark:text-teal-400 flex-shrink-0" />
              </div>
              <div>
                <h3 className="font-medium text-gray-800 dark:text-gray-200">{t(action.nameKey)}</h3>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

QuickActions.propTypes = {
  track: PropTypes.func,
  page: PropTypes.func,
  identify: PropTypes.func
};
