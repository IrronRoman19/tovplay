import { Users, Heart, Shield, LogIn } from "lucide-react";
import { Link } from "react-router-dom";
import { createPageUrl } from "@/utils";
import { useContext } from "react";
import { LanguageContext } from "@/components/lib/LanguageContext";

export default function Welcome() {
  const { t } = useContext(LanguageContext);
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-teal-50 dark:from-gray-900 dark:to-gray-800 p-6 relative">
      <div className="absolute top-6 right-6">
        <Link to={createPageUrl("SignIn")}>
          <button className="flex items-center space-x-2 px-4 py-2 bg-white/70 dark:bg-gray-800/70 backdrop-blur-sm rounded-lg text-gray-700 dark:text-gray-200 hover:bg-white dark:hover:bg-gray-700 transition-colors shadow-sm">
            <LogIn className="w-4 h-4" />
            <span className="font-medium text-sm">{t("signIn", "Sign In")}</span>
          </button>
        </Link>
      </div>

      <div className="flex items-center justify-center w-full h-full pt-16">
        <div className="max-w-4xl w-full">
          <div className="text-center mb-12">
            <div className="w-20 h-20 mx-auto mb-6">
              <img
                src="https://qtrypzzcjebvfcihiynt.supabase.co/storage/v1/object/public/base44-prod/public/a2fc6dcfc_logo.png"
                alt={t("tovplayLogoAlt", "TovPlay Logo")}
                className="w-full h-full rounded-xl"
              />
            </div>
            <h1 className="text-4xl font-bold text-gray-800 dark:text-white mb-6">
              {t("welcomeToTovPlay", "Welcome to TovPlay")}
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto leading-relaxed">
              {t("welcomeSubtitle", "A calm, comfortable space designed for gamers to connect at their own pace. We prioritize your comfort and accessibility above all else.")}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-teal-100 dark:bg-teal-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Heart className="w-6 h-6 text-teal-600 dark:text-teal-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                {t("comfortFirst", "Comfort First")}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
                {t("comfortFirstDesc", "Every feature is designed to minimize stress and maximize your comfort while connecting with others.")}
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-teal-100 dark:bg-teal-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Shield className="w-6 h-6 text-teal-600 dark:text-teal-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                {t("yourControl", "Your Control")}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
                {t("yourControlDesc", "Set your own pace, choose your availability, and customize every aspect of your experience.")}
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-teal-100 dark:bg-teal-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-6 h-6 text-teal-600 dark:text-teal-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                {t("gentleConnections", "Gentle Connections")}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
                {t("gentleConnectionsDesc", "Find like-minded players through shared interests, not pressure or competition.")}
              </p>
            </div>
          </div>

          <div className="text-center">
            <Link to={createPageUrl("CreateAccount")}>
              <button className="bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 text-white font-semibold text-lg px-8 py-4 rounded-lg shadow-md hover:shadow-lg transition-all duration-200 transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800">
                {t("getStarted", "Get Started")}
              </button>
            </Link>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">
              {t("takesLessThan2Minutes", "Takes less than 2 minutes to set up your profile")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
