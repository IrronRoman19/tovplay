
import { format, addDays, isAfter, startOfWeek, addWeeks } from "date-fns";
import { Calendar, Clock, Info, User, Sparkles } from "lucide-react";
import { useState, useEffect } from "react";
import { GameRequest } from "@/api/entities";

export default function UpcomingSlots({ availability, prefersCustom, currentUser }) {
  const [bookedSessions, setBookedSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const getBookedSessions = async () => {
      if (!currentUser) {
        setIsLoading(false); // No user, nothing to load
        return;
      }
      setIsLoading(true);
      try {
        const sentRequests = await GameRequest.filter({
          sender_username: currentUser.username,
          status: "accepted"
        });
        const receivedRequests = await GameRequest.filter({
          recipient_username: currentUser.username,
          status: "accepted"
        });

        const allAccepted = [...sentRequests, ...receivedRequests];

        // This is a complex mapping because we stored time as 'Day-HH:MM' string
        // In a real app, storing a proper ISO date would be better.
        // For now, we'll calculate the next occurrence of that day of the week.
        const dayMapping = {
          "Sunday": 0,
          "Monday": 1,
          "Tuesday": 2,
          "Wednesday": 3,
          "Thursday": 4,
          "Friday": 5,
          "Saturday": 6
        };

        const sessions = allAccepted.map(req => {
          const [dayOfWeek, time] = req.suggested_time.split("-");
          const today = new Date();
          const currentDayOfWeek = today.getDay(); // 0 for Sunday, 1 for Monday, etc.
          const targetDay = dayMapping[dayOfWeek];

          if (targetDay === undefined) {
            console.warn(`Unknown day of week: ${dayOfWeek} in request ${req.id}`);
            return null; // Skip invalid entries
          }

          let date = new Date(today); // Start with today's date

          // Calculate days to add to get to the target day of the week
          let daysToAdd = targetDay - currentDayOfWeek;
          if (daysToAdd < 0) {
            daysToAdd += 7; // If target day is earlier in the week, go to next week
          }
          date = addDays(date, daysToAdd);

          const [hour, minute] = time.split(":");
          date.setHours(parseInt(hour, 10), parseInt(minute, 10), 0, 0);

          // If the calculated time for today/this week is already in the past, move to next week
          if (isAfter(today, date)) {
            date = addWeeks(date, 1);
          }

          return {
            date: date,
            game: req.game,
            player: req.sender_username === currentUser.username ? req.recipient_username : req.sender_username,
            duration: "1 hour" // Placeholder, if duration is not stored in GameRequest
          };
        }).filter(session => session !== null && isAfter(session.date, new Date())); // Filter out invalid and past sessions

        // Sort sessions by date to display upcoming ones first
        sessions.sort((a, b) => a.date.getTime() - b.date.getTime());

        setBookedSessions(sessions.slice(0, 4)); // Limit to 4 upcoming sessions
      } catch (error) {
        console.error("Error fetching booked sessions:", error);
        setBookedSessions([]); // Clear sessions on error
      }
      setIsLoading(false);
    };

    getBookedSessions();
  }, [currentUser]); // Re-run effect when currentUser changes


  if (isLoading) {
    return (
      <div className="calm-card bg-gradient-to-br from-gray-50 to-slate-50 border-gray-200">
        <div className="flex items-center justify-center py-10">
          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-gray-500">Loading schedule...</span>
        </div>
      </div>
    );
  }

  if (prefersCustom) {
    return (
      <div className="calm-card bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Calendar className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-800">Schedule</h3>
        </div>
        <div className="p-5 bg-white/80 backdrop-blur-sm border border-blue-200 text-blue-800 rounded-xl flex items-start space-x-3 shadow-sm">
          <div className="p-2 bg-blue-100 rounded-full">
            <Info className="w-5 h-5 text-blue-600"/>
          </div>
          <div>
            <p className="font-semibold text-gray-800 mb-1">Open to Custom Requests</p>
            <p className="text-sm text-gray-600 leading-relaxed">This player prefers spontaneous game invitations. Send them a message to connect!</p>
          </div>
        </div>
      </div>
    );
  }

  const bookedDates = bookedSessions.map(s => format(s.date, "yyyy-MM-dd"));

  // Generate calendar view for the next 2 weeks
  const generateCalendarWeeks = () => {
    const today = new Date();
    const startDate = startOfWeek(today, { weekStartsOn: 0 }); // Start week on Sunday for calendar view
    const weeks = [];

    for (let weekIndex = 0; weekIndex < 2; weekIndex++) {
      const weekStart = addWeeks(startDate, weekIndex);
      const days = [];

      for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
        const date = addDays(weekStart, dayIndex);
        const dayName = format(date, "EEE");
        const dayNumber = format(date, "d");
        const dateString = format(date, "yyyy-MM-dd");
        const isToday = dateString === format(today, "yyyy-MM-dd");
        // Check if date is strictly before today's start
        const isPast = date.setHours(0,0,0,0) < today.setHours(0,0,0,0) && !isToday;

        const fullDayName = format(date, "EEEE"); // e.g., 'Monday'
        const hasAvailability = availability && Object.keys(availability).some(key =>
          key.startsWith(fullDayName) && availability[key]
        );

        const hasBooking = bookedDates.includes(dateString);

        days.push({
          date,
          dayName,
          dayNumber,
          isToday,
          isPast,
          hasAvailability,
          hasBooking
        });
      }

      weeks.push(days);
    }

    return weeks;
  };

  const calendarWeeks = generateCalendarWeeks();
  const hasAvailability = availability && Object.keys(availability).length > 0;

  return (
    <div className="calm-card bg-gradient-to-br from-gray-50 to-slate-50 border-gray-200">
      <div className="flex items-center space-x-3 mb-6">
        <div className="p-2 bg-teal-100 rounded-lg">
          <Calendar className="w-5 h-5 text-teal-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-800">Next Sessions</h3>
        <div className="flex-1"></div>
        <Sparkles className="w-4 h-4 text-gray-400" />
      </div>

      {/* Enhanced Calendar View */}
      <div className="mb-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          {/* Header with subtle styling */}
          <div className="grid grid-cols-7 gap-2 mb-4">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
              <div key={day} className="text-center text-xs font-semibold text-gray-500 py-3 bg-gray-50 rounded-lg">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar days with enhanced styling */}
          {calendarWeeks.map((week, weekIndex) => (
            <div key={weekIndex} className="grid grid-cols-7 gap-2 mb-2">
              {week.map((day, dayIndex) => (
                <div
                  key={dayIndex}
                  className={`
                    aspect-square flex items-center justify-center text-sm rounded-xl font-medium relative transition-all duration-200 cursor-pointer
                    ${day.isToday 
                  ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-200 transform scale-105" 
                  : day.isPast 
                    ? "text-gray-300 bg-gray-50" 
                    : day.hasBooking
                      ? "bg-gradient-to-br from-teal-600 to-teal-700 text-white shadow-md shadow-teal-200 hover:shadow-lg hover:scale-105"
                      : day.hasAvailability
                        ? "bg-gradient-to-br from-teal-50 to-teal-100 text-teal-700 border border-teal-200 hover:from-teal-100 hover:to-teal-200 hover:shadow-md hover:scale-105"
                        : "text-gray-600 bg-gray-50 hover:bg-gray-100 border border-transparent hover:border-gray-200"
                }
                  `}
                >
                  {day.dayNumber}
                  {day.hasBooking && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 bg-white rounded-full shadow-sm flex items-center justify-center">
                      <div className="w-1.5 h-1.5 bg-teal-600 rounded-full"></div>
                    </div>
                  )}
                  {day.isToday && (
                    <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-white rounded-full shadow-sm"></div>
                  )}
                </div>
              ))}
            </div>
          ))}

          {/* Enhanced legend */}
          <div className="flex items-center justify-center space-x-6 text-xs text-gray-600 mt-6 pt-4 border-t border-gray-100">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-gradient-to-br from-teal-50 to-teal-100 border border-teal-200 rounded-md"></div>
              <span className="font-medium">Available</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-gradient-to-br from-teal-600 to-teal-700 rounded-md shadow-sm"></div>
              <span className="font-medium">Booked</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-gradient-to-br from-blue-500 to-blue-600 rounded-md shadow-sm"></div>
              <span className="font-medium">Today</span>
            </div>
          </div>
        </div>
      </div>

      {/* Enhanced Booked Sessions List */}
      {bookedSessions.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <h4 className="font-semibold text-gray-700">Upcoming Sessions</h4>
            <div className="flex-1 h-px bg-gradient-to-r from-gray-200 to-transparent"></div>
          </div>
          {bookedSessions.map((session, index) => (
            <div key={index} className="group bg-white border border-gray-100 rounded-xl p-4 hover:shadow-md transition-all duration-200 hover:border-teal-200">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  <div className="p-2 bg-teal-50 rounded-lg group-hover:bg-teal-100 transition-colors flex-shrink-0">
                    <Clock className="w-4 h-4 text-teal-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-gray-800 truncate">
                      {format(session.date, "EEEE, MMM d")} at {format(session.date, "h:mm a")}
                    </p>
                    <div className="flex items-center flex-wrap space-x-3 text-sm text-gray-600 mt-1">
                      <span className="px-2 py-1 bg-gray-100 rounded-md font-medium">{session.game}</span>
                      <div className="flex items-center space-x-1">
                        <User className="w-3 h-3" />
                        <span>{session.player}</span>
                      </div>
                      <span className="text-gray-400">•</span>
                      <span>{session.duration}</span>
                    </div>
                  </div>
                </div>
                <div className="px-3 py-1 bg-teal-50 text-teal-700 rounded-full text-xs font-semibold flex-shrink-0">
                  Confirmed
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : hasAvailability ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
            <Calendar className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-800 font-semibold mb-2">No upcoming sessions</p>
          <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
            Your calendar is free! Others can request to play during your available times.
          </p>
        </div>
      ) : (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-sm">
            <Calendar className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-800 font-semibold mb-2">No schedule set</p>
          <p className="text-sm text-gray-500 max-w-sm mx-auto leading-relaxed">
            Set your availability to start receiving game requests
          </p>
        </div>
      )}
    </div>
  );
}
