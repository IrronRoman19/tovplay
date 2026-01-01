import { Calendar, Check, MousePointer, ArrowRight } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiService } from "@/api/apiService";
import { createPageUrl } from "@/utils";

const timeSlots = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, "0")}:00`);
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function OnboardingSchedule() {
  const navigate = useNavigate();
  const [availability, setAvailability] = useState({});
  const [isDragging, setIsDragging] = useState(false);
  const [dragMode, setDragMode] = useState(null); // 'select' or 'deselect'

  // State for the checkbox preference and save confirmation
  const [prefersCustomRequests, setPrefersCustomRequests] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Prevent interaction if calendar is disabled
  const handleMouseDown = (day, time) => {
    if (prefersCustomRequests) {
      return;
    } // Prevent action if disabled
    setIsDragging(true);
    const key = `${day}-${time}`;
    const newMode = !availability[key] ? "select" : "deselect";
    setDragMode(newMode);
    setAvailability(prev => ({ ...prev, [key]: newMode === "select" }));
  };

  // Prevent interaction if calendar is disabled
  const handleMouseEnter = (day, time) => {
    if (isDragging && !prefersCustomRequests) {
      const key = `${day}-${time}`;
      setAvailability(prev => ({ ...prev, [key]: dragMode === "select" }));
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

  // Save data to backend, show confirmation, then navigate
  const handleContinue = async () => {
    try {
      const userId = localStorage.getItem("userId"); // Get from auth context in a real app

      // Transform availability into the format expected by the backend
      const slots = Object.entries(availability)
        .filter(([_, isAvailable]) => isAvailable)
        .map(([key]) => {
          // Convert from "Day-HH:mm" to proper object format
          const [day, time] = key.split("-");
          const startHour = time.split(":")[0].padStart(2, "0");
          const endHour = String(parseInt(startHour) + 1).padStart(2, "0"); // Add 1 hour duration

          return {
            day_of_week: day,
            start_time: `${startHour}:00`,
            end_time: `${endHour}:00`
          };
        });

      // Save to backend
      await apiService.post(`/availability/${userId}`, {
        slots,
        is_recurring: true,
        customPreference: prefersCustomRequests
      });

      // Also save to localStorage as fallback
      const dataToSave = {
        availability,
        customPreference: prefersCustomRequests,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem("tovplay-schedule", JSON.stringify(dataToSave));

      // Show confirmation message
      setShowConfirmation(true);

      // Navigate after a short delay to allow user to see confirmation
      setTimeout(() => {
        navigate(createPageUrl("OnboardingComplete"));
      }, 1500);

    } catch (error) {
      console.error("Error saving schedule:", error);
      // Fallback to just saving to localStorage if backend fails
      const dataToSave = {
        availability,
        customPreference: prefersCustomRequests,
        lastUpdated: new Date().toISOString()
      };
      localStorage.setItem("tovplay-schedule", JSON.stringify(dataToSave));

      // Still show success since we saved to localStorage
      setShowConfirmation(true);
      setTimeout(() => {
        navigate(createPageUrl("OnboardingComplete"));
      }, 1500);
    }
  };

  const handleSkip = () => {
    navigate(createPageUrl("OnboardingComplete"));
  };

  // Handler for the checkbox
  const handleCheckboxChange = e => {
    setPrefersCustomRequests(e.target.checked);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Calendar className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Set Your Availability</h1>
          <p className="text-gray-600 mb-2">Step 4 of 5</p>
          <p className="text-sm text-gray-500">Let others know when you're free to play (optional)</p>
        </div>

        <div className="progress-bar mb-8">
          <div className="progress-fill" style={{ width: "80%" }}></div>
        </div>

        {/* Add conditional classes to disable the calendar visually */}
        <div
          className={`calm-card transition-opacity duration-300 ${prefersCustomRequests ? "opacity-50 pointer-events-none" : ""}`}
          onMouseLeave={handleMouseUp}
        >
          <div className="overflow-x-auto select-none">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="p-2 font-medium text-gray-700 border-b"></th>
                  {days.map(day => (
                    <th key={day} className="text-center p-2 font-medium text-gray-700 border-b min-w-16 text-sm">
                      {day.slice(0,3)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {timeSlots.map(time => {
                  if (parseInt(time.split(":")[0]) % 1 !== 0) {
                    return null;
                  }
                  return (
                    <tr key={time}>
                      <td className="p-1 pr-2 text-xs text-gray-600 border-b text-right">{time}</td>
                      {days.map(day => {
                        const isAvailable = availability[`${day}-${time}`] || false;
                        return (
                          <td
                            key={`${day}-${time}`}
                            className="p-1 text-center border-b"
                            onMouseDown={() => handleMouseDown(day, time)}
                            onMouseEnter={() => handleMouseEnter(day, time)}
                          >
                            <div className={`w-full h-6 rounded-md transition-all duration-100 cursor-pointer ${isAvailable ? "bg-teal-400" : "bg-gray-100 hover:bg-gray-200"}`}></div>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="mt-4 text-center text-sm text-gray-600 flex items-center justify-center">
            <MousePointer className="w-4 h-4 mr-2" />
            Click and drag to select multiple time slots.
          </div>
        </div>

        {/* Checkbox for custom game requests */}
        <div className="flex items-center justify-center mt-6">
          <label htmlFor="custom-requests" className="flex items-center space-x-2 text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              id="custom-requests"
              checked={prefersCustomRequests}
              onChange={handleCheckboxChange}
              className="h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
            />
            <span>I prefer custom game requests instead of a fixed schedule</span>
          </label>
        </div>

        <div className="mt-6 space-y-4 max-w-md mx-auto">
          {/* Confirmation Message */}
          {showConfirmation && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-md text-center flex items-center justify-center" role="alert">
              <Check className="w-5 h-5 mr-2" />
              <span className="font-medium">Availability Saved!</span>
            </div>
          )}

          <button
            onClick={handleContinue}
            className="calm-button w-full flex items-center justify-center space-x-2"
            disabled={showConfirmation} // Disable button after clicking
          >
            <span>Continue</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={handleSkip}
            className="w-full py-3 text-gray-600 hover:text-gray-700 transition-colors"
          >
            I'll do this later
          </button>
        </div>

        <div className="text-center mt-6">
          <Link
            to={createPageUrl("SelectGames")}
            className="text-sm text-teal-600 hover:text-teal-700 underline"
          >
            Go Back
          </Link>
        </div>
      </div>
    </div>
  );
}
