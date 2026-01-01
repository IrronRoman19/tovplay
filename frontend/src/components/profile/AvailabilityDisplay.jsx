import { Calendar, Info } from "lucide-react";

const timeSlots = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, "0")}:00`);
const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const fullDays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function AvailabilityDisplay({ availability, prefersCustom }) {

  if (prefersCustom) {
    return (
      <div className="calm-card">
        <div className="flex items-center space-x-3 mb-4">
          <Calendar className="w-5 h-5 text-teal-600" />
          <h3 className="text-lg font-semibold text-gray-800">Availability</h3>
        </div>
        <div className="p-4 bg-blue-50 border-l-4 border-blue-500 text-blue-800 rounded-r-lg flex items-start space-x-3 text-center">
          <Info className="w-6 h-6 mt-1 flex-shrink-0"/>
          <div className="text-left">
            <p className="font-medium">Open to Custom Requests</p>
            <p className="text-sm">This player prefers spontaneous game invitations. Send them a message to connect!</p>
          </div>
        </div>
      </div>
    );
  }

  const hasAvailability = availability && Object.keys(availability).length > 0;

  return (
    <div className="calm-card">
      <div className="flex items-center space-x-3 mb-4">
        <Calendar className="w-5 h-5 text-teal-600" />
        <h3 className="text-lg font-semibold text-gray-800">Availability</h3>
      </div>
      {hasAvailability ? (
        <div className="overflow-x-auto">
          <table className="w-full text-center text-sm">
            <thead>
              <tr>
                <th className="p-2 w-16"></th>
                {days.map(day => (
                  <th key={day} className="p-2 font-medium text-gray-600">{day}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {timeSlots.map(time => {
                if (parseInt(time.split(":")[0]) % 4 !== 0) {
                  return null;
                }
                return (
                  <tr key={time}>
                    <td className="p-2 text-xs text-gray-500 text-right">{time}</td>
                    {fullDays.map(day => (
                      <td key={`${day}-${time}`} className="p-1">
                        <div className={`w-full h-4 rounded-sm ${availability[`${day}-${time}`] ? "bg-teal-400" : "bg-gray-100"}`}></div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-gray-600">This player has not set their availability yet.</p>
        </div>
      )}
    </div>
  );
}
