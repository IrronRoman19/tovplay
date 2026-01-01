
import { CheckCircle, ArrowRight } from "lucide-react";
import { useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createPageUrl } from "@/utils";

export default function OnboardingComplete() {
  const navigate = useNavigate();

  useEffect(() => {
    // Auto-redirect after 3 seconds
    const timer = setTimeout(() => {
      navigate(createPageUrl("SignIn"));
    }, 3000);

    return () => clearTimeout(timer);
  }, [navigate]);

  const handleContinue = () => {
    navigate(createPageUrl("SignIn"));
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Welcome to TovPlay!</h1>
          <p className="text-gray-600">Step 5 of 5 - Complete</p>
        </div>

        <div className="progress-bar mb-8">
          <div className="progress-fill" style={{ width: "100%" }}></div>
        </div>

        <div className="calm-card text-center">
          <div className="space-y-4">
            <p className="text-gray-600 leading-relaxed">
              Your profile is all set up! You can now start connecting with other players
              at your own pace and comfort level.
            </p>

            <div className="bg-teal-50 p-4 rounded-lg">
              <p className="text-sm text-teal-700">
                💡 <strong>Next Step:</strong> {/*Explore the "Find Players" page to connect with others.**/}
                You will be redirected to your login shortly. Go to your email to verify your account.
              </p>
            </div>

            <button
              onClick={handleContinue}
              className="calm-button w-full flex items-center justify-center space-x-2"
            >
              <span>Go to Login</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="text-center mt-6 flex justify-between items-center">
          <Link
            to={createPageUrl("OnboardingSchedule")}
            className="text-sm text-teal-600 hover:text-teal-700 underline"
          >
            Go Back
          </Link>
          <p className="text-xs text-gray-500">
            Redirecting automatically in 3 seconds...
          </p>
        </div>
      </div>
    </div>
  );
}
