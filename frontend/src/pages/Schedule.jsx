import { Calendar, Clock, Check, MousePointer, Info } from "lucide-react";
import { toast } from "sonner";
import { useState, useEffect, useCallback, useContext } from "react";
import { apiService } from "@/api/apiService";
import { User } from "@/api/entities";
import { LanguageContext } from "@/components/lib/LanguageContext";

const timeSlots = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, "0")}:00`);

export default function Schedule() {
  const { t, language } = useContext(LanguageContext);
  
  // English day names for internal use
  const englishDays = language === 'he' 
    ? ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    : ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  
  // Translated day names for display
  const days = englishDays.map(day => t(day));
  
  // Function to get the English day name from a translated day name
  const getEnglishDay = (translatedDay) => {
    const index = days.findIndex(day => day === translatedDay);
    return index >= 0 ? englishDays[index] : englishDays[0];
  };

  const [availability, setAvailability] = useState({});
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState(null); // 'select' or 'deselect'
  const [saved, setSaved] = useState(false);
  const [prefersCustom, setPrefersCustom] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [saveForFutureWeeks, setSaveForFutureWeeks] = useState(false);
  const [hasSelectedSlots, setHasSelectedSlots] = useState(false);
  const [showEmptyScheduleWarning, setShowEmptyScheduleWarning] = useState(false);

  // Helper function to normalize day names to lowercase for internal use
  const normalizeDayName = (day) => {
    if (!day) return '';
    // Convert to lowercase and remove any whitespace
    return day.trim().toLowerCase();
  };

  // Load availability from localStorage and user preferences
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        // Try to fetch from backend first
        try {
          const response = await apiService.get(`/availability/`);

          if (response.data) {
            const backendData = response.data;
            const formattedAvailability = {};

            // Check if we got the data in the slots format (from OnboardingSchedule)
            if (Array.isArray(backendData)) {
              // Format: [{day_of_week: 'Monday', start_time: '09:00', end_time: '10:00', is_recurring: true}, ...]
              backendData.forEach(slot => {
                const startHour = parseInt(slot.start_time.split(":")[0]);
                const endHour = parseInt(slot.end_time.split(":")[0]);
                const dayName = normalizeDayName(slot.day_of_week);

                for (let hour = startHour; hour < endHour; hour++) {
                  const timeKey = `${dayName}-${hour.toString().padStart(2, "0")}:00`;
                  formattedAvailability[timeKey] = true;
                }
              });
            } else if (backendData.slots && Array.isArray(backendData.slots)) {
              // Format: {slots: ["Monday-09:00", "Tuesday-14:00", ...]}
              backendData.slots.forEach(slot => {
                const [day, time] = slot.split('-');
                const dayName = normalizeDayName(day);
                formattedAvailability[`${dayName}-${time}`] = true;
              });

              // Set custom preference if available
              if (typeof backendData.customPreference === "boolean") {
                setPrefersCustom(backendData.customPreference);
              }
            }

            setAvailability(formattedAvailability);
          }
        } catch (error) {
          console.error("Error fetching from backend:", error);
          // Fallback to localStorage if backend fetch fails
          const savedData = localStorage.getItem("tovplay-schedule");
          if (savedData) {
            try {
              const parsedData = JSON.parse(savedData);
              if (parsedData.availability) {
                setAvailability(parsedData.availability);
              } else if (Array.isArray(parsedData)) {
                // Handle legacy format if needed
                const formattedAvailability = {};
                parsedData.forEach(slot => {
                  formattedAvailability[slot] = true;
                });
                setAvailability(formattedAvailability);
              }

              if (typeof parsedData.customPreference === "boolean") {
                setPrefersCustom(parsedData.customPreference);
              }
            } catch (e) {
              console.error("Error parsing saved schedule:", e);
            }
          }
        }
      } catch (error) {
        console.error("Error loading schedule data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Update hasSelectedSlots whenever availability changes
  useEffect(() => {
    const hasSelections = Object.values(availability).some(Boolean);
    setHasSelectedSlots(hasSelections);
    
    // Save to localStorage with English day names
    const saveData = {};
    Object.entries(availability).forEach(([key, value]) => {
      const [day, time] = key.split('-');
      const englishDay = getEnglishDay(day);
      saveData[`${englishDay}-${time}`] = value;
    });
    
    localStorage.setItem("tovplay-schedule", JSON.stringify(saveData));
  }, [availability]);

  const handleMouseDown = (dayIndex, time) => {
    setIsDragging(true);
    // Use the English day name for the key (lowercase for consistency)
    const englishDay = englishDays[dayIndex].toLowerCase();
    const key = `${englishDay}-${time}`;
    const newMode = !availability[key] ? "select" : "deselect";
    setDragMode(newMode);
    setAvailability(prev => ({
      ...prev,
      [key]: newMode === "select"
    }));
  };

  const handleMouseEnter = (dayIndex, time) => {
    if (isDragging) {
      // Use the English day name for the key (lowercase for consistency)
      const englishDay = englishDays[dayIndex].toLowerCase();
      const key = `${englishDay}-${time}`;
      setAvailability(prev => ({
        ...prev,
        [key]: dragMode === "select"
      }));
    }
  };

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setDragMode(null);
  }, []);

  useEffect(() => {
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseUp]);

  // Transform availability object into the required slots array format
  const transformAvailabilityToSlots = availability => {
    return Object.entries(availability)
      .filter(([_, isAvailable]) => isAvailable)
      .map(([slot]) => {
        // Split the slot into day and time
        const [day, time] = slot.split('-');
        
        // Always use the English day name from the englishDays array
        const dayIndex = days.findIndex(d => d === day);
        const englishDay = dayIndex >= 0 ? englishDays[dayIndex] : day;
        
        // Format: "Monday-09:00"
        return `${englishDay.charAt(0).toUpperCase() + englishDay.slice(1)}-${time}`;
      });
  };

  const handleSave = async () => {
    try {
      setIsLoading(true);
      const slots = transformAvailabilityToSlots(availability);

      // Save preference to localStorage
      localStorage.setItem("tovplay-save-for-future-weeks", JSON.stringify(saveForFutureWeeks));

      try {
        // Save to the backend API
        await apiService.post(`/availability/`, {
          slots: slots || [], // Ensure we always send an array, even if empty
          is_recurring: saveForFutureWeeks // Use is_recurring as per backend API
        });

        setSaved(true);
        toast.success(t("scheduleSavedSuccessfully"));
        setTimeout(() => setSaved(false), 3000);
      } catch (apiError) {
        console.warn("Failed to save to API, falling back to localStorage:", apiError);
        // Fallback to localStorage if API is not available
        localStorage.setItem("tovplay-schedule", JSON.stringify(availability));
        toast.success(t("scheduleSavedToLocal"));
      }
    } catch (error) {
      console.error("Error saving schedule:", error);
      toast.error(t("saveScheduleError"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearSchedule = () => {
    setAvailability({});
    setHasSelectedSlots(false);
    localStorage.removeItem("tovplay-schedule");
    toast.info(t("scheduleCleared"));
  };

  const handlePreferenceChange = async e => {
    const isChecked = e.target.checked;
    setPrefersCustom(isChecked);
    try {
      await User.updateMyUserData({ prefers_custom_availability: isChecked });
    } catch (error) {
      console.error("Failed to update preference:", error);
    }
  };

  if (isLoading) {
    return <div className="max-w-7xl mx-auto p-6 text-center">{t("loading")}...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">{t("yourGamingSchedule")}</h1>
        <p className="text-muted-foreground max-w-3xl">
          {t("setWeeklyAvailability")}
        </p>
      </div>

      {/* <div className="calm-card mb-6">
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            id="custom-avail"
            checked={prefersCustom}
            onChange={handlePreferenceChange}
            className="h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
          />
          <label htmlFor="custom-avail" className="font-medium text-gray-800">
            I prefer custom game requests instead of a fixed schedule
          </label>
        </div>
        {prefersCustom && (
          <div className="mt-4 p-4 bg-teal-50 border-l-4 border-teal-500 text-teal-800 rounded-r-lg flex items-center space-x-3">
            <Info className="w-5 h-5"/>
            <p className="text-sm">Your schedule is hidden. Others will know you are open to spontaneous game invitations.</p>
          </div>
        )}
      </div> */}

      <div className={`calm-card transition-opacity ${prefersCustom ? "opacity-40 pointer-events-none" : "opacity-100"}`}>
        <div className={`flex items-center mb-6 ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}>
          <Calendar className="w-6 h-6 text-primary" />
          <h2 className="text-xl font-semibold text-foreground">{t("weeklyAvailability")}</h2>
        </div>

        <div className="overflow-x-auto select-none" onMouseLeave={handleMouseUp}>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="text-left p-3 font-medium text-muted-foreground border-b border-border">{t("time")}</th>
                {days.map((day, index) => (
                  <th key={index} className="text-center p-3 font-medium text-muted-foreground border-b border-border min-w-28">
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {timeSlots.map(time => (
                <tr key={time} className="hover:bg-accent/50">
                  <td className="p-2 text-sm text-muted-foreground border-b border-border font-medium">
                    <div className={`flex items-center ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}>
                      <Clock className="w-4 h-4" />
                      <span>{time}</span>
                    </div>
                  </td>
                  {days.map((day, dayIndex) => {
                    const englishDay = englishDays[dayIndex];
                    const isAvailable = availability[`${englishDay}-${time}`] || false;
                    return (
                      <td
                        key={`${day}-${time}`}
                        className="p-1 text-center border-b border-border"
                        onMouseDown={() => handleMouseDown(dayIndex, time)}
                        onMouseEnter={() => handleMouseEnter(dayIndex, time)}
                      >
                        <div
                          className={`w-full h-8 rounded-md transition-all duration-100 cursor-pointer flex items-center justify-center ${
                            isAvailable
                              ? "bg-teal-500 text-white dark:bg-teal-600"
                              : "bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600"
                          }`}
                        >
                          {isAvailable && <Check className="w-4 h-4" />}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={`calm-card mb-6 mt-5 ${prefersCustom ? "opacity-40 pointer-events-none" : "opacity-100"}`}>
          <div className={`flex items-center ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}>
            <input
              type="checkbox"
              id="save-for-future"
              checked={saveForFutureWeeks}
              onChange={e => setSaveForFutureWeeks(e.target.checked)}
              className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
            />
            <label htmlFor="save-for-future" className="font-medium text-foreground">
              {t("saveForFutureWeeks")}
            </label>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between">
          <div className={`flex items-center text-sm text-muted-foreground ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}>
            <MousePointer className="w-4 h-4" />
            <span>{t("clickAndDragInstruction")}</span>
          </div>

          <div className={`flex items-center ${language === 'he' ? 'space-x-reverse' : ''} space-x-3`}>
            <button
              onClick={handleClearSchedule}
              className="px-4 py-2 text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg transition-colors hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              {t("clearAll")}
            </button>
            <div className="relative">
              <button
                onClick={() => {
                  if (!hasSelectedSlots) {
                    setShowEmptyScheduleWarning(true);
                  } else {
                    handleSave();
                  }
                }}
                className={`flex items-center px-4 py-2 rounded-md transition-colors ${language === 'he' ? 'space-x-reverse' : ''} space-x-2 ${
                  saved 
                  ? "bg-teal-100 border border-teal-200 text-teal-700 dark:bg-teal-900/30 dark:border-teal-800 dark:text-teal-300"
                  : "bg-teal-600 text-white hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-800"
                } ${!hasSelectedSlots ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={prefersCustom}
              >
                <span>{saved ? t("changesSaved") : t("saveSchedule")}</span>
                {saved && <Check className="w-4 h-4" />}
              </button>
              {!hasSelectedSlots && (
                <div className="absolute -top-10 left-1/2 transform -translate-x-1/2 bg-warning/10 text-warning-foreground text-xs px-2 py-1 rounded whitespace-nowrap">
                  {t("unableToSaveEmptySchedule")}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Empty Schedule Warning Popup */}
      {showEmptyScheduleWarning && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-background border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            <div className="flex flex-col items-center text-center">
              <Info className="w-12 h-12 text-warning mb-4" />
              <h3 className="text-xl font-semibold text-foreground mb-2">{t("noTimeSlotsSelected")}</h3>
              <p className="text-muted-foreground mb-6">
                {t("selectTimeSlotsOrEnableCustom")}
              </p>
              <button
                onClick={() => setShowEmptyScheduleWarning(false)}
                className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-800 transition-colors"
              >
                {t("gotIt")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
