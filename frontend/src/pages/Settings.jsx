import { Type, Palette, Globe } from "lucide-react";
import { useContext } from "react";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { useTheme } from "@/context/ThemeContext";

export default function Settings() {
  const { language, setLanguage, t } = useContext(LanguageContext);
  const { 
    theme, 
    fontSize, 
    reduceMotion, 
    updateTheme, 
    updateFontSize, 
    updateReduceMotion 
  } = useTheme();

  const handleSettingChange = (key, value) => {
    if (key === "theme") {
      updateTheme(value);
    } else if (key === "font_size") {
      updateFontSize(value);
    } else if (key === "reduce_motion") {
      updateReduceMotion(value);
    }
  };

  const ToggleSwitch = ({ enabled, onChange, label }) => {
    const isRtl = language === "he";
    const knobPos = enabled
      ? (isRtl ? "left-1" : "right-1")
      : (isRtl ? "right-1" : "left-1");

    return (
      <div className="flex items-center shrink-0">
        <button
          type="button"
          onClick={() => onChange(!enabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 ${
            enabled 
              ? "bg-teal-600 dark:bg-teal-600" 
              : "bg-gray-200 dark:bg-gray-600"
          }`}
          aria-pressed={enabled}
          aria-label={label}
        >
          <span
            className={`${knobPos} absolute top-1 inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-all duration-200 ease-in-out`}
          />
        </button>
      </div>
    );
  };

  const getFontSizeClass = (size) => {
    switch (size) {
      case 'small':
        return 'text-sm';
      case 'medium':
        return 'text-base';
      case 'large':
        return 'text-lg';
      default:
        return 'text-base';
    }
  };

  const fontSizes = [
    { label: "S", value: "small" },
    { label: "M", value: "medium" },
    { label: "L", value: "large" }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">{t("comfortAndAccessibility")}</h1>
        <p className="text-gray-600 dark:text-gray-300">{t("comfortAndAccessibilityDesc")}</p>
      </div>

      <div className="space-y-6">
        {/* Language Settings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-6">
            <Globe className="w-6 h-6 text-teal-600" />
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{t("appLanguage")}</h2>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{t("chooseLanguage")}</label>
            <div className="grid grid-cols-2 gap-4">
              <button 
                onClick={() => setLanguage("en")} 
                className={`p-4 rounded-lg border-2 transition-all text-center ${
                  language === "en" 
                    ? "border-teal-500 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200" 
                    : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <p className="font-medium">English</p>
              </button>
              <button 
                onClick={() => setLanguage("he")} 
                className={`p-4 rounded-lg border-2 transition-all text-center ${
                  language === "he" 
                    ? "border-teal-500 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200" 
                    : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <p className="font-medium">עברית</p>
              </button>
            </div>
          </div>
        </div>

        {/* Theme Settings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-6">
            <Palette className="w-6 h-6 text-teal-600 dark:text-teal-400" />
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{t("visualTheme")}</h2>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{t("chooseTheme")}</label>
            <div className="grid grid-cols-2 gap-4">
              <button 
                onClick={() => handleSettingChange("theme", "light")} 
                className={`p-4 rounded-lg border-2 transition-all text-center ${
                  theme === "light" 
                    ? "border-teal-500 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200" 
                    : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <p className="font-medium">{t("lightTheme")}</p>
              </button>
              <button 
                onClick={() => handleSettingChange("theme", "dark")} 
                className={`p-4 rounded-lg border-2 transition-all text-center ${
                  theme === "dark" 
                    ? "border-teal-500 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200" 
                    : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <p className="font-medium">{t("darkTheme")}</p>
              </button>
            </div>
          </div>
        </div>

        {/* Accessibility Settings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-6">
            <Type className="w-6 h-6 text-teal-600 dark:text-teal-400" />
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">{t("accessibility")}</h2>
          </div>
          <div className="space-y-6">
            <div className={`flex items-center justify-between ${language === 'he' ? 'gap-x-4' : 'gap-x-4'}`}>
              <div className="flex-1">
                <h3 className="font-medium text-gray-800 dark:text-gray-100">{t("reduceMotion")}</h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">{t("reduceMotionDesc")}</p>
              </div>
              <ToggleSwitch 
                enabled={reduceMotion} 
                onChange={value => handleSettingChange("reduce_motion", value)} 
                label="Reduce Motion"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{t("fontSize")}</label>
              <div className="grid grid-cols-3 gap-4">
                {fontSizes.map(({ label, value }) => (
                  <button
                    key={value}
                    onClick={() => handleSettingChange("font_size", value)}
                    className={`p-4 rounded-lg border-2 transition-all text-center ${
                      fontSize === value 
                        ? "border-teal-500 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200" 
                        : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    }`}
                  >
                    <p className={`font-medium ${getFontSizeClass(value)}`}>
                      {label}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
