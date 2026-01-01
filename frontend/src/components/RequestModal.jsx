import { X, Clock, Gamepad2, Send, Check, AlertCircle } from "lucide-react";
import { useState, useEffect, useContext, useCallback, useMemo } from "react";
import Portal from "./Portal";
import { apiService } from "@/api/apiService";
import { LanguageContext } from "@/components/lib/LanguageContext";

// Day name translations
const dayTranslations = {
  en: {
    Sunday: 'Sunday',
    Monday: 'Monday',
    Tuesday: 'Tuesday',
    Wednesday: 'Wednesday',
    Thursday: 'Thursday',
    Friday: 'Friday',
    Saturday: 'Saturday'
  },
  he: {
    Sunday: 'יום ראשון',
    Monday: 'יום שני',
    Tuesday: 'יום שלישי',
    Wednesday: 'יום רביעי',
    Thursday: 'יום חמישי',
    Friday: 'יום שישי',
    Saturday: 'יום שבת'
  }
};

// A safer, more robust implementation of the matching logic
const findMatchingSlots = (user1Avail, user2Avail) => {
  try {
    if (!user1Avail || !user2Avail) {
      return [];
    }

    const user1Slots = Object.keys(user1Avail || {}).filter(key => user1Avail[key]);
    const user2Slots = Object.keys(user2Avail || {}).filter(key => user2Avail[key]);

    return user1Slots.filter(slot => user2Slots.includes(slot));
  } catch (error) {
    console.error("Error finding matching slots:", error);
    return [];
  }
};

export default function RequestModal({ player, currentUser, game, onClose, onSuccess }) {
  const { t, locale, language } = useContext(LanguageContext);
  const [matchingSlots, setMatchingSlots] = useState([]);
  const [selectedSlots, setSelectedSlots] = useState([]);
  const [busySlots, setBusySlots] = useState([]);
  const [isLoadingBusySlots, setIsLoadingBusySlots] = useState(true);
  const [message, setMessage] = useState(t('defaultRequestMessage', { game: selectedGame || game || t('thisGame', 'this game') }));
  const [isSending, setIsSending] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState(null);

  // Update message when game changes
  useEffect(() => {
    setMessage(t('defaultRequestMessage', { game: selectedGame || game || t('thisGame', 'this game') }));
  }, [selectedGame, game, t]);

  // Function to fetch busy slots
  const fetchBusySlots = async () => {
    if (!player?.username) return [];

    const activeGame = selectedGame || game;
    if (!activeGame) return [];

    try {
      const response = await apiService.get(`/findplayers/${activeGame}?recipient_username=${player.username}`);
      return response.data || [];
    } catch (error) {
      console.error('Error fetching busy slots:', error);
      return [];
    }
  };

  // Fetch busy slots when the component mounts or when the game changes
  useEffect(() => {
    const loadBusySlots = async () => {
      try {
        setIsLoadingBusySlots(true);
        const slots = await fetchBusySlots();
        setBusySlots(slots);
      } finally {
        setIsLoadingBusySlots(false);
      }
    };

    loadBusySlots();
  }, [player?.username, game, selectedGame]);

  // Format time according to locale
  const formatTime = useCallback((hour, minute = 0) => {
    const date = new Date();
    date.setHours(hour, minute, 0);

    return new Intl.DateTimeFormat(locale.code, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: locale.code === 'en-US' // Use 12-hour format for English, 24-hour for others
    }).format(date);
  }, [locale]);

  // Format day name according to locale
  const formatDay = useCallback((day) => {
    // Use translation if available, otherwise use the original day name
    return dayTranslations[locale.code]?.[day] || day;
  }, [locale]);

  // Format the available slots and mark busy ones
  useEffect(() => {
    if (player?.available_slots) {
      const formattedSlots = player.available_slots.map(slot => {
        const slotId = `${slot.day}-${slot.hour}`;
        // Convert hour to HH:MM format for comparison with backend data
        const hourParts = slot.hour.split(':');
        const hour = parseInt(hourParts[0], 10);
        const minute = hourParts[1] ? parseInt(hourParts[1], 10) : 0;
        const formattedHour = formatTime(hour, minute);

        const isBusy = busySlots.some(busySlot => {
          // Normalize day names (remove any whitespace and convert to lowercase)
          const slotDay = slot.day.trim().toLowerCase();
          const busyDay = (busySlot.day || '').trim().toLowerCase();

          // Normalize times
          let busyHour = busySlot.hour || '';
          if (busyHour && !busyHour.includes(':')) {
            // If hour is just a number, convert to HH:00
            const h = parseInt(busyHour, 10);
            busyHour = `${h.toString().padStart(2, '0')}:00`;
          }

          // Check if days match and times overlap within the same hour
          if (slotDay === busyDay) {
            // If times are the same or within the same hour, consider it busy
            const [busyH, busyM] = busyHour.split(':').map(Number);
            return Math.abs(hour - busyH) < 1 && Math.abs(minute - (busyM || 0)) < 60;
          }
          return false;
        });

        const translatedDay = formatDay(slot.day);
        return {
          id: slotId,
          label: `${translatedDay} ${t('at')} ${formattedHour}`,
          day: translatedDay,
          hour: formattedHour,
          originalDay: slot.day, // Keep original day for backend
          isBusy
        };
      });

      setMatchingSlots(formattedSlots);

      // Log for debugging
      console.log('Formatted slots:', formattedSlots);
      console.log('Busy slots:', busySlots);
    }
  }, [player?.available_slots, busySlots, formatTime, formatDay, t]);

  // Function to fetch and log all game requests
  const fetchAndLogGameRequests = async () => {
    try {
      const response = await apiService.get('/game_requests/');
      console.log('Current game requests:', response.data);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch game requests:', error);
      return null;
    }
  };

  const handleSendRequest = async () => {
    // Validate form
    if (selectedSlots.length === 0 && matchingSlots.length > 0) {
      setError(t("errorSelectTimeSlot"));
      return;
    }

    if (message.trim().length < 2) {
      setError(t("errorEnterMessage"));
      return;
    }

    // First, refresh the busy slots to ensure we have the latest data
    try {
      const freshBusySlots = await fetchBusySlots();
      setBusySlots(freshBusySlots);

      // Check if any selected slots are now busy
      const busySelectedSlots = selectedSlots.filter(slotId => {
        const slot = matchingSlots.find(s => s.id === slotId);
        if (!slot) return false;

        // Check against fresh busy slots
        return freshBusySlots.some(busySlot => {
          const slotDay = slot.day.trim().toLowerCase();
          const busyDay = (busySlot.day || '').trim().toLowerCase();
          if (slotDay !== busyDay) return false;

          // Normalize times for comparison
          const [slotHour, slotMinute = 0] = slot.hour.split(':').map(Number);
          let [busyHour, busyMinute = 0] = (busySlot.hour || '').split(':').map(Number);

          // If busyHour is a number without minutes, treat it as the hour
          if (isNaN(busyHour) && !isNaN(Number(busySlot.hour))) {
            busyHour = Number(busySlot.hour);
            busyMinute = 0;
          }

          // Consider it busy if within the same hour
          return Math.abs(slotHour - busyHour) < 1 && Math.abs((slotMinute || 0) - (busyMinute || 0)) < 60;
        });
      });

      if (busySelectedSlots.length > 0) {
        // Update UI to show these slots as busy
        setMatchingSlots(prevSlots =>
          prevSlots.map(slot => ({
            ...slot,
            isBusy: busySelectedSlots.includes(slot.id) ? true : slot.isBusy
          }))
        );

        // Remove busy slots from selection
        setSelectedSlots(prev => prev.filter(id => !busySelectedSlots.includes(id)));

        // Show error if no slots left
        if (busySelectedSlots.length === selectedSlots.length) {
          setError(t("errorSlotsNoLongerAvailable"));
          return;
        }

        // If we have some valid slots left, continue with those
        if (selectedSlots.length > busySelectedSlots.length) {
          setError(t("errorSomeSlotsUnavailable", { count: selectedSlots.length - busySelectedSlots.length }));
          // Continue with the remaining slots
        }
      }
    } catch (error) {
      console.error('Error refreshing busy slots:', error);
      // Continue with the request even if we couldn't refresh
    }

    // Check if any selected slots are already busy
    const busySelectedSlots = selectedSlots.filter(slotId => {
      const slot = matchingSlots.find(s => s.id === slotId);
      return slot?.isBusy;
    });

    if (busySelectedSlots.length > 0) {
      setError(t("errorSlotsUnavailableRefresh"));
      // Update UI to show these slots as busy
      setMatchingSlots(prevSlots =>
        prevSlots.map(slot => ({
          ...slot,
          isBusy: busySelectedSlots.includes(slot.id) ? true : slot.isBusy
        }))
      );
      return;
    }

    setError(null);
    setIsSending(true);

    try {
      // Format the selected slots into suggested times
      const formatSuggestedTimes = () => {
        if (selectedSlots.length === 0) return [new Date().toISOString()];

        return selectedSlots.map(slotId => {
          const slot = matchingSlots.find(s => s.id === slotId);
          if (!slot) return null;

          // Create a date object for the selected day and time in local timezone
          const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
          const dayIndex = days.findIndex(d => d.toLowerCase() === slot.day.toLowerCase());
          const [hours, minutes] = slot.hour.split(':').map(Number);

          // Create a date in local timezone
          const now = new Date();
          const resultDate = new Date(now);

          // Set to next occurrence of the selected day
          const daysUntilNextDay = (dayIndex + 7 - now.getDay()) % 7;
          resultDate.setDate(now.getDate() + daysUntilNextDay);

          // Set the time in local timezone
          resultDate.setHours(hours, minutes, 0, 0);

          // If the time has already passed today, move to next week
          if (resultDate < now) {
            resultDate.setDate(resultDate.getDate() + 7);
          }

          // Format as ISO string with timezone offset
          const pad = n => n < 10 ? '0' + n : n;
          const tzOffset = -resultDate.getTimezoneOffset();
          const tzSign = tzOffset >= 0 ? '+' : '-';
          const tzHours = Math.abs(Math.floor(tzOffset / 60));
          const tzMinutes = Math.abs(tzOffset % 60);

          // Return in format: YYYY-MM-DDTHH:MM:SS+HH:MM
          return `${resultDate.getFullYear()}-${pad(resultDate.getMonth() + 1)}-${pad(resultDate.getDate())}T${pad(hours)}:${pad(minutes)}:00${tzSign}${pad(tzHours)}:${pad(tzMinutes)}`;
        }).filter(Boolean);
      };

      const suggestedTimes = formatSuggestedTimes();
      const gameName = (selectedGame || game || "General Gaming").toLowerCase();
      const requestMessage = message || `Let's play`;

      // Create a request for each selected time slot
      const requests = suggestedTimes.map(suggestedTime => ({
        recipient_username: player.username,
        game_name: gameName,
        suggested_time: suggestedTime,
        message: requestMessage,
        status: 'pending'
      }));

      // Send all requests in parallel
      const responses = await Promise.all(
        requests.map(request => apiService.post('/game_requests/', request))
      );

      console.log('Sending request with data:', requests);
      console.log('Responses:', responses);

      // Update the busy slots with the newly created requests
      const newBusySlots = responses.map(response => {
        const suggestedTime = new Date(response.data.suggested_time);
        return {
          day: suggestedTime.toLocaleDateString('en-US', { weekday: 'long' }),
          hour: suggestedTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
        };
      });

      // Update the busy slots state with the new busy slots
      setBusySlots(prevBusySlots => [...prevBusySlots, ...newBusySlots]);

      // Update the matching slots to mark the selected slots as busy
      setMatchingSlots(prevSlots =>
        prevSlots.map(slot => ({
          ...slot,
          isBusy: selectedSlots.includes(slot.id) ? true : slot.isBusy
        }))
      );

      // Show success state
      setIsSuccess(true);

      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(responses.map(r => r.data));
      }

      // Close the modal after 2 seconds
      setTimeout(() => {
        onClose();
      }, 2000);

    } catch (error) {
      console.error('Error sending game request:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      
      let errorMessage = t("errorFailedToSendRequest");
      
      if (error.response) {
        if (error.response.status === 401) {
          errorMessage = t("errorPleaseLogin");
        } else if (error.response.status === 403) {
          errorMessage = t("errorNoPermission");
        } else if (error.response.status === 404) {
          errorMessage = t("errorPlayerNotFound");
        } else if (error.response.status === 409) {
          // Conflict - slot already taken
          errorMessage = t("errorSlotsConflict");
          
          // Refresh the busy slots to update the UI
          try {
            const freshBusySlots = await fetchBusySlots();
            setBusySlots(freshBusySlots);

            // Update the UI to show the new busy slots
            setMatchingSlots(prevSlots =>
              prevSlots.map(slot => {
                const isNowBusy = freshBusySlots.some(busySlot =>
                  slot.day.trim().toLowerCase() === (busySlot.day || '').trim().toLowerCase() &&
                  slot.hour.split(':')[0] === (busySlot.hour || '').split(':')[0]
                );
                return {
                  ...slot,
                  isBusy: isNowBusy || slot.isBusy
                };
              })
            );
          } catch (refreshError) {
            console.error('Error refreshing busy slots after conflict:', refreshError);
          }
        } else if (error.response.status >= 500) {
          // Server error - refresh the busy slots
          try {
            const freshBusySlots = await fetchBusySlots();
            setBusySlots(freshBusySlots);
            errorMessage = t("errorServerError");
          } catch (refreshError) {
            console.error('Error refreshing busy slots after server error:', refreshError);
          }
        }
      }

      setError(errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  // Success state
  if (isSuccess) {
    return (
      <Portal>
        <div
          className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center p-4 z-50"
          onClick={onClose}
        >
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-8 w-full max-w-lg text-center">
            <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">{t("requestSentTitle")}</h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              {t("requestSentBody", { username: player.username })}
            </p>
            <button
              onClick={onClose}
              className="mt-4 bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 text-white font-medium py-3 px-6 rounded-lg transition-colors w-full focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
            >
              {t("close")}
            </button>
          </div>
        </div>
      </Portal>
    );
  }

  return (
    <Portal>
      <div
        className="fixed inset-0 bg-black/30 dark:bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        onClick={e => {
          // Close modal if backdrop is clicked
          if (e.target === e.currentTarget) {
            onClose();
          }
        }}
      >
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 w-full max-w-lg relative max-h-[90vh] overflow-y-auto">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            disabled={isSending}
          >
            <X className="w-6 h-6" />
          </button>

          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">{t("requestToPlayTitle")}</h2>
            <p className="text-gray-600 dark:text-gray-300">
              {/* You can add a dedicated translation key for this sentence if needed */}
              <span className="font-semibold text-teal-600 dark:text-teal-400">{player.username}</span>
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="space-y-6">
            {/* Game Field */}
            <div>
              <label className={`flex items-center text-sm font-medium text-gray-700 dark:text-gray-200 mb-2 ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}>
                <Gamepad2 className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                <span>{t("gameLabel")}</span>
              </label>
              <div className="w-full p-3 border-2 border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-700/50 text-gray-700 dark:text-gray-200 font-medium">
                {game || "General Gaming"}
              </div>
            </div>

            {/* Time Slot Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                {t("selectTimeSlots")}
                {isLoadingBusySlots && (
                  <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">{t("checkingAvailability")}</span>
                )}
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {matchingSlots.length === 0 && !isLoadingBusySlots ? (
                  <div className="text-center py-4 text-gray-500 dark:text-gray-400">
                    {t("noTimeSlotsFound")}
                  </div>
                ) : (
                  matchingSlots.map((slot) => {
                    const isSlotBusy = slot.isBusy;
                    const isSelected = selectedSlots.includes(slot.id);

                    return (
                      <div
                        key={slot.id}
                        onClick={() => {
                          if (isSlotBusy) return;

                          setSelectedSlots(prev =>
                            prev.includes(slot.id)
                              ? prev.filter(id => id !== slot.id)
                              : [...prev, slot.id]
                          );
                        }}
                        className={`p-4 rounded-lg border cursor-pointer transition-colors ${isSelected
                          ? 'border-teal-500 dark:border-teal-600 bg-teal-50 dark:bg-teal-900/30'
                          : isSlotBusy
                            ? 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50 cursor-not-allowed'
                            : 'border-gray-200 dark:border-gray-600 hover:border-teal-300 dark:hover:border-teal-500'
                          }`}
                      >
                        <div className="flex items-center justify-between">
                        <div className="flex items-center flex-1">
                          <p className={`font-medium ${
                            isSlotBusy ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-gray-100'
                          }`}>
                            {slot.label}
                          </p>
                        </div>
                        <div className="flex items-center gap-x-2">
                            {isSlotBusy && (
                              <span className={`text-xs text-green-600 dark:text-green-400 flex items-center ${language === 'he' ? 'gap-x-1 flex-row-reverse' : 'gap-x-1'}`}>
                                <Check className="w-3.5 h-3.5" />
                                {t("requestSentTag")}
                              </span>
                            )}
                            <div
                              className={`w-5 h-5 rounded border-2 ${isSlotBusy
                                ? 'border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700'
                                : isSelected
                                  ? 'bg-teal-500 dark:bg-teal-600 border-teal-500 dark:border-teal-600 flex items-center justify-center'
                                  : 'border-gray-300 dark:border-gray-600'
                                }`}
                            >
                              {isSelected && !isSlotBusy && (
                                <Check className="w-3.5 h-3.5 text-white" />
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
              {selectedSlots.length > 0 && (
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  {t("timeSlotsSelected", { count: selectedSlots.length, plural: selectedSlots.length !== 1 ? 's' : '' })}
                </p>
              )}
            </div>
            {/* Message Field */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                {t("yourMessage")}{' '}
                <span className="text-gray-400 font-normal">{t("required")}</span>
              </label>
              <div className="relative">
                <textarea
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                  className="w-full p-3 border-2 border-gray-200 dark:border-gray-600 rounded-lg h-32 resize-none focus:border-teal-500 dark:focus:border-teal-500 focus:ring-2 focus:ring-teal-100 dark:focus:ring-teal-900/30 transition-all bg-white dark:bg-gray-700/50 text-gray-900 dark:text-gray-100"
                  placeholder={t("writeFriendlyMessage")}
                  disabled={isSending}
                  maxLength={500}
                />
                <div className="text-xs text-gray-400 dark:text-gray-500 text-right mt-1">
                  {message.length}/500 {t("characters")}
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-8 space-y-3">
            <button
              onClick={handleSendRequest}
              disabled={isSending || (matchingSlots.length > 0 && selectedSlots.length === 0) || !message.trim() || isLoadingBusySlots}
              className={`w-full bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-all flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 ${language === 'he' ? 'space-x-reverse' : ''} space-x-2`}
            >
              {isSending ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>{t("sending")}</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>{t("sendRequest")}</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={onClose}
              disabled={isSending}
              className="w-full text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100 font-medium py-2 px-4 rounded-lg transition-colors text-sm focus:outline-none focus:ring-2 focus:ring-gray-300 dark:focus:ring-gray-600 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
            >
              {t("cancelAction")}
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
};
