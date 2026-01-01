
import { Gamepad2, ArrowRight, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "../lib/axios-config";
import { createPageUrl } from "@/utils";


const popularGames = [
  { name: "Minecraft", icon: "🎮" },
  { name: "Among Us", icon: "🚀" },
  { name: "Chess", icon: "♟️" },
  { name: "Animal Crossing", icon: "🏝️" },
  { name: "Stardew Valley", icon: "🌱" },
  { name: "Fall Guys", icon: "🎪" },
  { name: "Rocket League", icon: "🚗" },
  { name: "Overwatch", icon: "🎯" },
  { name: "Fortnite", icon: "🏗️" },
  { name: "Apex Legends", icon: "🎮" },
  { name: "Valorant", icon: "🔫" },
  { name: "League of Legends", icon: "⚔️" }
];

export default function SelectGames() {
  const navigate = useNavigate();
  const [games, setGames] = useState([]);
  const [selectedGames, setSelectedGames] = useState([]);

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const response = await axios.get("/api/games");
        setGames(response.data || popularGames);
      } catch (error) {
        console.error("Error fetching games:", error);
        setGames(popularGames);
      }
    };

    // const fetchSelectedGames = async () => {
    //   try {
    //     const response = await axios.get('/api/user/selected-games');
    //     setSelectedGames(response.data || []);
    //   } catch (error) {
    //     console.error("Error fetching selected games:", error);
    //     setSelectedGames([]);
    //   }
    // }

    fetchGames();
    // fetchSelectedGames();
  }, []);



  const handleGameToggle = game => {
    setSelectedGames(prev =>
      prev.includes(game)
        ? prev.filter(g => g !== game)
        : [...prev, game]
    );
  };

  const handleContinue = async () => {

    try {
      // Save selected games to backend if needed
      const response = await axios.post("/api/user_game_preferences/create_user_games_preference",
        { user_id: localStorage.getItem("userId"), games_names: selectedGames });
      console.log("Saved selected games:", response.data);
      navigate(createPageUrl("OnboardingSchedule"));
    } catch (error) {
      console.error("Error saving selected games:", error);
      // Optionally handle the error (e.g., show a notification)
    }

  };

  const handleSkip = () => {
    navigate(createPageUrl("OnboardingSchedule"));
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <Gamepad2 className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Select Your Games</h1>
          <p className="text-gray-600 mb-2">Step 3 of 5</p>
          <p className="text-sm text-gray-500">Choose the games you enjoy playing (optional)</p>
        </div>

        <div className="progress-bar mb-8">
          <div className="progress-fill" style={{ width: "60%" }}></div>
        </div>

        <div className="calm-card">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
            {games.map(game => (
              <button
                key={game.game_name}
                onClick={() => handleGameToggle(game.game_name)}
                className={`p-4 rounded-lg border-2 transition-all duration-200 text-left relative ${
                  selectedGames.includes(game.game_name)
                    ? "border-teal-500 bg-teal-50 text-teal-700"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{popularGames.find(g => g.name === game.game_name)?.icon}</span>
                  <span className="font-medium text-sm">{game.game_name}</span>
                </div>
                {selectedGames.includes(game.game_name) && (
                  <Check className="w-5 h-5 text-teal-600 absolute top-2 right-2" />
                )}
              </button>
            ))}
          </div>

          <div className="space-y-4">
            <button
              onClick={handleContinue}
              className="calm-button w-full flex items-center justify-center space-x-2"
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
        </div>

        <div className="text-center mt-6">
          <Link
            to={createPageUrl("ChooseUsername")}
            className="text-sm text-teal-600 hover:text-teal-700 underline"
          >
            Go Back
          </Link>
        </div>
      </div>
    </div>
  );
}
