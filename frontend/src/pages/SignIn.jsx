import { GoogleLogin } from "@react-oauth/google";
import { Formik, Form, Field } from "formik";
import { jwtDecode } from "jwt-decode";
import { useState, useContext } from "react";
import * as Yup from "yup";
import { LanguageContext } from "@/components/lib/LanguageContext";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import { loginUser, loginSuccess } from "@/stores/authSlice";
import { addTodo } from "@/stores/todoSlice";
import { apiService } from "@/api/apiService";

const SignIn = ({ identify }) => {
  const { t, language } = useContext(LanguageContext);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showResetHint, setShowResetHint] = useState(false);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  {
    const loc = document.location;
    const url = new URL(loc);
    const params = url.searchParams;
    const token = params.get("token") || null;
    const userID = params.get("user_id") || null;
    if (token && userID) {
      console.log(
        dispatch(
          loginSuccess({
            user: userID,
            token: token,
            isLoggedIn: true
          })
        )
      );
      setTimeout(() => {
        navigate("/dashboard");
      }, 0);
    }
  }

  const validationSchema = Yup.object().shape({
    username: Yup.string()
      .required("Username or email is required")
      .test(
        "username-format",
        "Invalid format. For email: use only letters, numbers, dots, and one @. For username: use Hebrew/English letters, numbers, underscores, hyphens, and dots",
      .required(t('usernameOrEmailRequired'))
      .test(
        'username-format',
        t('invalidUsernameFormat'),
        (value) => {
          if (value.includes("@")) {
            return (
              /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value) &&
              !/[^a-zA-Z0-9.@_-]/.test(value)
            );
          }
          return /^[\u0590-\u05FFa-zA-Z0-9_\-.]*$/.test(value);
        }
      )
      .test(
        "valid-username",
        "Username can only contain Hebrew/English letters, numbers, underscores, hyphens, and dots",
        'valid-username',
        t('usernameValidChars'),
        (value) => {
          if (value.includes("@")) return true;
          return /^[\u0590-\u05FFa-zA-Z0-9_\-.]*$/.test(value);
        }
      )
      .test(
        "no-consecutive-special",
        "Username cannot contain consecutive special characters (_.-)",
        'no-consecutive-special',
        t('usernameNoConsecutiveSpecial'),
        (value) => {
          if (value.includes("@")) return true;
          return !/[_.-]{2,}/.test(value);
        }
      ),
    password: Yup.string().required("Password is required")
    password: Yup.string().required(t('passwordRequired'))
  });

  const handleSubmit = async (values, { setSubmitting, setFieldError }) => {
    try {
      setError("");
      setShowResetHint(false);

      const resultAction = await dispatch(
        loginUser({
          username: values.username,
          password: values.password
        })
      );

      if (loginUser.fulfilled.match(resultAction)) {
        const { user, token } = resultAction.payload;
        if (identify && user) {
          identify(user, { username: values.username });
        }

        try {
          const communityData = await apiService.checkCommunityStatus();
          const isInCommunity =
            communityData[`User ${communityData.discord_username} in our community`] ||
            communityData.in_community;

          if (!isInCommunity) {
            const inviteLink =
              import.meta.env.VITE_DISCORD_INVITE_LINK ||
              "https://discord.gg/FSVxjGAW";
            sessionStorage.setItem("showCommunityDialog", "true");
            sessionStorage.setItem("discordInviteLink", inviteLink);
            window.dispatchEvent(new Event("showCommunityDialog"));
          }
        } catch (error) {
          console.error("Error checking community status:", error);
        }

        navigate("/dashboard");
      } else {
        setError(
          resultAction.payload ||
            "Failed to log in. Please check your credentials."
        );
        setShowResetHint(true);
      }
    } catch (err) {
      setError("An error occurred during login. Please try again.");
      setShowResetHint(true);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBackToWelcome = (e) => {
    e.preventDefault();
    navigate("/welcome");
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-teal-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <Formik
        initialValues={{
          username: "",
          password: ""
        }}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        validateOnChange={true}
        validateOnBlur={true}
      >
        {({
          errors,
          touched,
          isSubmitting,
          isValid,
          dirty,
          handleChange,
          setFieldTouched,
          validateField,
          values
        }) => (
          <Form className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md w-full max-w-sm relative transition-colors duration-200">
            <button
              type="button"
              onClick={handleBackToWelcome}
              className="absolute top-3 left-3 p-1 rounded-full text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Back to welcome"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
            </button>

            <div className="justify-items-center">
              <h1 className="text-3xl font-bold mb-2 text-gray-800 dark:text-white">
                {t('welcomeToTovPlay')}
              </h1>
            </div>

            <div className="mx-auto mb-6">
              <img
                src="https://tovplay.org/lovable-uploads/b1e62294-a51b-4e1e-8f0e-4e1472f1a562.png"
                alt="TovPlay Logo"
                className="h-16 mx-auto"
              />
            </div>

            <h2 className="text-2xl font-bold mb-6 text-center text-gray-800 dark:text-white">
              Sign In
            </h2>

            {showResetHint && (
              <div className="mb-4 p-3 rounded border border-amber-300 bg-amber-50 text-amber-800 dark:bg-amber-900/30 dark:border-amber-600 dark:text-amber-200">
                <p className="text-sm mb-1">Trouble signing in?</p>
                <button
                  type="button"
                  onClick={() => navigate("/ForgotPassword")}
                  className="text-sm font-medium text-teal-700 dark:text-teal-300 hover:underline"
                >
                  Reset your password
                </button>
            <h2 className="text-2xl font-bold mb-6 text-center text-gray-800 dark:text-white">{t('signIn')}</h2>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded dark:bg-red-900 dark:border-red-700 dark:text-red-300">
                <p>{error}</p>
              </div>
            )}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded dark:bg-red-900 dark:border-red-700 dark:text-red-300">
             <p>{error}</p>
            </div>)}
            <div className="mb-4">
              <label htmlFor="username" className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('usernameOrEmail')}
              </label>
              <div className="relative">
                <Field
                  name="username"
                  type="text"
                  className={`w-full px-3 py-2 border rounded focus:outline-none focus:ring ${
                    errors.username && touched.username
                      ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
                      : 'focus:border-teal-300 focus:ring-teal-200 border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400'
                  }`}
                  placeholder={t('enterUsernameOrEmail')}
                  dir={language === 'he' ? 'rtl' : 'ltr'}
                  style={{ textAlign: language === 'he' ? 'right' : 'left' }}
                  onChange={(e) => {
                    handleChange(e);
                    setFieldTouched('username', true, false);
                    // Only validate if we already have an error
                    if (errors.username) {
                      validateField('username');
                    }
                  }}
                  onBlur={() => {
                    setFieldTouched('username', true, true);
                    validateField('username');
                  }}
                  onKeyDown={(e) => {
                    // Allow all key presses during input
                    e.stopPropagation();
                  }}
                  value={values.username}
                />
              </div>
              {errors.username && touched.username && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-300">{errors.username}</p>
              )}
            </div>

            <div className="mb-6">
              <label htmlFor="password" className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('password')}
              </label>
              <Field
                name="password"
                type="password"
                className={`w-full px-3 py-2 border rounded focus:outline-none focus:ring ${
                  errors.password && touched.password
                    ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
                    : 'focus:border-teal-300 focus:ring-teal-200 border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400'
                }`}
                placeholder={t('enterPassword')}
                onChange={(e) => {
                  handleChange(e);
                  setFieldTouched('password', true, false);
                  validateField('password');
                }}
                onBlur={() => {
                  setFieldTouched('password', true, true);
                  validateField('password');
                }}
                value={values.password}
              />
              {errors.password && touched.password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-300">{errors.password}</p>
              )}
            </div>
            <button
              type="submit"
              disabled={!isValid || isSubmitting || !dirty}
              className={`w-full py-2 rounded transition-all duration-200 ${
                !isValid || isSubmitting || !dirty
                  ? 'bg-teal-600/50 text-white/70 cursor-not-allowed dark:bg-teal-600/50 dark:text-white/70'
                  : 'bg-teal-600 hover:bg-teal-700 text-white hover:shadow-md dark:bg-teal-600 dark:hover:bg-teal-700 dark:text-white dark:hover:shadow-md'
              }`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white dark:text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {t('signingIn')}
                </span>
              ) : (
                t('signIn')
              )}
            </button>
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300 dark:border-gray-600"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">{t('orContinueWith')}</span>
              </div>
            </div>

            <a
              href={`${import.meta.env.VITE_API_BASE_URL}/api/discord/login`}
              className="w-full inline-flex justify-center items-center gap-2 bg-[#5865F2] text-white py-2 rounded-md hover:bg-[#4752C4] transition-colors mt-4 border border-[#404EED] shadow-sm dark:bg-[#5865F2] dark:hover:bg-[#4752C4]"
            >
              {/* Discord logo */}
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.317 4.369a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.211.375-.444.864-.608 1.249a18.27 18.27 0 00-5.487 0 12.3 12.3 0 00-.617-1.249.077.077 0 00-.079-.037 19.736 19.736 0 00-4.885 1.515.069.069 0 00-.032.027C1.578 8.02.943 11.56 1.184 15.06a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.08.08 0 00.086-.028c.461-.63.873-1.295 1.226-1.993a.076.076 0 00-.041-.105 12.932 12.932 0 01-1.852-.885.077.077 0 01-.007-.129c.125-.094.25-.192.37-.291a.074.074 0 01.078-.01c3.894 1.778 8.108 1.778 11.96 0a.074.074 0 01.079.009c.12.099.244.198.37.292a.077.077 0 01-.006.129c-.59.345-1.214.64-1.853.885a.076.076 0 00-.04.106c.36.697.772 1.362 1.226 1.993a.08.08 0 00.086.028 19.876 19.876 0 005.993-3.03.08.08 0 00.03-.056c.5-7.148-1.2-11.646-4.23-14.664a.061.061 0 00-.031-.028zM8.02 13.684c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.956-2.42 2.157-2.42 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.419-2.157 2.419zm7.974 0c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.956-2.42 2.157-2.42 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.947 2.419-2.157 2.419z"/></svg>
              <span>{t('signInWithDiscord')}</span>
            </a>
            <div className="text-center mt-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('dontHaveAccount')}{' '}
                <a href="/createaccount" className="text-teal-600 dark:text-teal-400 hover:text-teal-700 dark:hover:text-teal-300 font-medium transition-colors">
                  {t('signUp')}
                </a>
              </p>
            </div>
          </Form>
        )}
      </Formik>

      <style jsx global>{`
      
      <style>{`
        /* Add smooth transition for input focus */
        input {
          transition: all 0.2s ease-in-out;
        }

        /* Style for error tooltip */
        .error-tooltip {
          position: absolute;
          background: #FEE2E2;
          color: #B91C1C;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          margin-top: 0.25rem;
          z-index: 10;
          border: 1px solid #FCA5A5;
        }
      `}</style>
    </div>
  );
};

export default SignIn;
