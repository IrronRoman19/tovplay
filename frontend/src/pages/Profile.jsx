import { User, Camera, Edit, Save } from "lucide-react";
import { useState, useEffect, useContext } from "react";
import { useSelector } from "react-redux";
import { useLocation, useNavigate } from "react-router-dom";
import AvailabilityDisplay from "../components/profile/AvailabilityDisplay";
import GameList from "../components/profile/GameList";
import ProfileHeader from "../components/profile/ProfileHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import LocalStorage from "@/utils/localStorage";
import { toast } from "sonner";
import { LanguageContext } from "@/components/lib/LanguageContext";
import apiService from "@/api/apiService";



const popularGames = [
  "Chess",
  "Stardew Valley",
  "Overwatch",
  "Rocket League",
  "League of Legends",
  "Apex Legends",
  "Fortnite",
  "Minecraft",
  "Valorant",
  "Fall Guys",
  "Among Us",
  "Animal Crossing"
];

// Static language code mapping (doesn't change with language)
const languageCodeMap = {
  'he': 'he',
  'en': 'en',
  'ar': 'ar',
  'ru': 'ru',
  'am': 'am',
};

// Reverse mapping for getting code from name
const languageNameToCode = Object.entries(languageMap).reduce((acc, [code, name]) => {
  acc[name] = code;
  return acc;
}, {});

const availableLanguages = Object.values(languageMap);

// Helper function to convert API language format to array of full names
const parseLanguageString = (langString) => {
  if (!langString) return [];
  // Remove curly braces and split by comma
  const codes = langString.replace(/[{}]/g, '').split(',').map(lang => lang.trim());
  return codes;
};

// Helper function to convert array of language names back to API format
const formatLanguagesForApi = (languages) => {
  const codes = languages.map(lang => languageNameToCode[lang]).filter(Boolean);
  return `{${codes.join(',')}}`;
};

// Communication preferences mapping between frontend and API values
// const communicationMap = {
//   'Text chat only': 'Written',
//   'Voice chat': 'Voice',
//   'Minimal chat': 'NoTalking'
// };

// Reverse mapping for API values to frontend display
const communicationApiToFrontend = {
  'Written': 'Text chat only',
  'Voice': 'Voice chat',
  'NoTalking': 'Minimal chat'
};

const communicationOptions = ["video", "voice", "written", "notalking"];
const opennessOptions = ["Open", "Careful", "Only Previous Contacts"];

export default function Profile() {
  const { t } = useContext(LanguageContext);
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const viewedUsername = queryParams.get("username");
  const authState = useSelector(state => state.auth);
  const [currentUser, setCurrentUser] = useState(null);

  const loggedInUsername = authState?.user?.username || authState?.username || currentUser?.username;
  const userId = LocalStorage.authUserId.get();

  // Dynamic language map using translations
  const getLanguageMap = () => ({
    'he': t('languages.hebrew'),
    'en': t('languages.english'),
    'ar': t('languages.arabic'),
    'ru': t('languages.russian'),
    'am': t('languages.amharic'),
  });

  // Dynamic communication options using translations
  const getCommunicationOptions = () => [
    t('profile.communication.voice'),
    t('profile.communication.text'),
    t('profile.communication.minimal')
  ];

  // Dynamic communication map using translations
  const getCommunicationMap = () => ({
    [t('profile.communication.text')]: 'Written',
    [t('profile.communication.voice')]: 'Voice',
    [t('profile.communication.minimal')]: 'NoTalking'
  });

  // Dynamic reverse communication map using translations
  const getCommunicationApiToFrontend = () => ({
    'Written': t('profile.communication.text'),
    'Voice': t('profile.communication.voice'),
    'NoTalking': t('profile.communication.minimal')
  });

  // Helper function to parse language string from API and convert to translated names
  const parseLanguageString = (langString) => {
    if (!langString) return [];
    const codes = langString.replace(/[{}]/g, '').split(',').map(lang => lang.trim());
    const languageMap = getLanguageMap();
    return codes.map(code => languageMap[code]).filter(Boolean);
  };

  // Helper function to convert translated language names back to codes
  const getLanguageCode = (translatedName) => {
    const languageMap = getLanguageMap();
    const entry = Object.entries(languageMap).find(([code, name]) => name === translatedName);
    return entry ? entry[0] : translatedName;
  };

  // Get available languages for display
  const availableLanguages = Object.values(getLanguageMap());
  const communicationOptions = getCommunicationOptions();
  const communicationApiToFrontend = getCommunicationApiToFrontend();
  const communicationMap = getCommunicationMap();

  // Fetch user data in parallel
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        setIsLoading(true);

        // 1. If viewing another user's profile, skip fetching current user data for the profile state
        if (viewedUsername && viewedUsername !== loggedInUsername) {
          // We still need currentUser for the "isFriend" check later, but we shouldn't update profileData with it
          // So we'll fetch it but not set it to profileData yet
        }

        // 1. First, fetch the basic user info to get the username
        const userData = await apiService.getCurrentUser();

        if (!userData) {
          setIsLoading(false);
          return;
        }

        setCurrentUser(userData);

        // 2. Prepare both API calls
        const profilePromise = apiService.get('/user_profiles/');
        const gamesPromise = userId ? apiService.get('/user_game_preferences/') : Promise.resolve({ data: [] });

        // 3. Make both API calls in parallel
        const [profileResponse, gamesResponse] = await Promise.all([
          profilePromise,
          gamesPromise
        ]);

        const profileData = profileResponse?.data;
        const gamesData = Array.isArray(gamesResponse?.data) ? gamesResponse.data : [];

        // Update currentUser with games data
        setCurrentUser(prev => ({ ...prev, games: gamesData }));

        // 4. Process and update state ONLY if we are viewing our own profile
        if (profileData && (!viewedUsername || viewedUsername === loggedInUsername)) {
          const mappedProfile = {
            ...profileData,
            description: profileData.bio || '',
            communication: profileData.communication_preferences || 'written',
            languages: Array.isArray(profileData.language)
              ? profileData.language
              : parseLanguageString(profileData.language) || ['en'],
            avatar_url: profileData.avatar_url || '',
            profilePhoto: profileData.avatar_url || '',
            games: gamesData // Add games data directly from the parallel fetch
          };

          // Update both profile and form data states
          setProfileData(prev => ({
            ...prev,
            ...mappedProfile,
            username: userData.username || prev.username
          }));

          setFormData(prev => ({
            ...prev,
            ...mappedProfile,
            username: userData.username || prev.username
          }));
        }

      } catch (error) {
        console.error('Error fetching data:', error);
        if (error.response?.status !== 404) { // Don't show error for 404 (profile not created yet)
          toast.error(t('failedToLoadProfileData') || 'Failed to load profile data');
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, [userId]);

  console.log('LocalStorage authUserId:', userId);
  console.log('LocalStorage userProfile:', typeof window !== 'undefined' ? localStorage.getItem('userProfile') : 'Not available');

  const isMyProfile = !viewedUsername || viewedUsername === loggedInUsername;

  const [isEditing, setIsEditing] = useState(location.search.includes('edit=true'));
  const [isLoading, setIsLoading] = useState(true);
  const [profileData, setProfileData] = useState({
    username: loggedInUsername || '',
    description: '',
    avatar_url: '',
    language: 'en',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    communication: 'Written Messages',
    openness: 'Open',
    games: [],
    languages: ['en']
  });

  const [formData, setFormData] = useState({ ...profileData });
  const [errors, setErrors] = useState({});
  const [allGames, setAllGames] = useState([]);
  const navigate = useNavigate();

  // Function to load user profile data and game preferences in parallel
  const loadProfile = async () => {
    try {
      console.log('Starting profile load...');

      // If viewing another user's profile
      if (viewedUsername && viewedUsername !== loggedInUsername) {
        console.log('DEBUG: Viewing public profile. viewedUsername:', viewedUsername, 'loggedInUsername:', loggedInUsername);
        try {
          const publicProfile = await apiService.getPublicUserProfile(viewedUsername);
          console.log('DEBUG: Public profile API response:', publicProfile);
          console.log('DEBUG: Blocking reason:', publicProfile.blocking_reason);

          if (publicProfile) {
            console.log("DEBUG: Public profile object:", publicProfile);

            // We will let ProfileHeader handle the relationship check to avoid duplication
            // and ensure it's always up to date with the UI component.

            // Fetch all games for icons
            try {
              const gamesResponse = await apiService.get('/games/');
              if (gamesResponse.data) {
                setAllGames(gamesResponse.data);
              }
            } catch (err) {
              console.error('Error fetching all games:', err);
            }

            const mappedProfile = {
              id: publicProfile.id || publicProfile.user_id || publicProfile._id, // Try multiple ID fields
              username: publicProfile.username,
              description: publicProfile.bio || '',
              profilePhoto: publicProfile.avatar_url || '', // ProfileHeader uses profilePhoto
              games: publicProfile.games || [],
              friends: [],
              languages: publicProfile.language ? parseLanguageString(publicProfile.language) : [],
              communication: communicationApiToFrontend[publicProfile.communication_preferences] || 'Written Messages',
              discord_username: publicProfile.discord_username,
              isFriend: false, // Let ProfileHeader determine this
              friendStatus: 'None', // Let ProfileHeader determine this
              blocking_reason: null,
              incomingRequestId: null
            }; console.log('DEBUG: Mapped profile data:', mappedProfile);
            setProfileData(mappedProfile);
          } else {
            console.error('DEBUG: Public profile data is empty');
          }
        } catch (error) {
          console.error('DEBUG: Error fetching public profile:', error);
          toast.error(t('failedToLoadUserProfile') || 'Failed to load user profile');
        }
        return;
      }

      // If viewing own profile
      console.log('User ID:', userId);

      if (!userId) {
        console.error('No user ID found');
        // Only redirect if trying to view own profile
        if (!viewedUsername) {
          toast.error(t('pleaseLogInToViewProfile') || 'Please log in to view your profile');
          navigate('/login');
        }
        return;
      }

      // Initialize with default values
      const defaultProfile = {
        username: loggedInUsername || 'loading user name...',
        description: '',
        bio: '',
        avatar_url: '',
        language: 'English',
        languages: ['English'],
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        communication: 'Written Messages',
        communication_preferences: 'Written',
        openness: 'Open',
        games: [],
        friends: [],
        sessions: 0
      };

      // Set default values first for immediate UI rendering
      setProfileData(prev => ({ ...defaultProfile, ...prev }));
      setFormData(prev => ({ ...defaultProfile, ...prev }));

      try {
        // Prepare both API calls
        const profilePromise = apiService.get('/user_profiles/');
        const gamesPromise = apiService.get('/user_game_preferences/');

        // Make both API calls in parallel
        const [profileResponse, gamesResponse] = await Promise.all([
          profilePromise,
          gamesPromise
        ]);

        console.log('Profile API response:', profileResponse);
        console.log('Games API response:', gamesResponse);

        // Process the responses
        if (profileResponse?.data) {
          const profileData = profileResponse.data;
          const gamesData = Array.isArray(gamesResponse?.data) ? gamesResponse.data : [];

          // Map the API response to our form fields
          const mergedData = {
            ...defaultProfile,
            ...profileData,
            description: profileData.bio || '',
            communication: communicationApiToFrontend[profileData.communication_preferences] || 'Written Messages',
            languages: Array.isArray(profileData.language)
              ? profileData.language
              : parseLanguageString(profileData.language) || ['en'],
            avatar_url: profileData.avatar_url || '',
            games: gamesData,
            // Keep other existing data if needed
            username: profileData.username || defaultProfile.username,
            timezone: profileData.timezone || defaultProfile.timezone
          };

          console.log('Merged profile data:', mergedData);

          // Update both profile and form data states
          setProfileData(mergedData);
          setFormData(mergedData);

          // Update localStorage with fresh data
          if (typeof window !== 'undefined') {
            localStorage.setItem('userProfile', JSON.stringify(mergedData));
          }
        }
      } catch (error) {
        console.error('Error loading data:', error);
        if (error.response?.status === 404) {
          // If 404, initialize with default values
          setProfileData(defaultProfile);
          setFormData(defaultProfile);
        } else {
          toast.error(t('failedToLoadProfileData') || 'Failed to load profile data');
        }
      }
    } catch (error) {
      console.error('Error in loadProfile:', error);
      toast.error(t('failedToLoadProfileData') || 'Failed to load profile data');
    } finally {
      setIsLoading(false);
    }
  };

  // Initial profile load
  useEffect(() => {
    loadProfile();
  }, [navigate, userId, loggedInUsername, isMyProfile, viewedUsername]);

  useEffect(() => {
    setFormData(profileData);
  }, [profileData]);

  useEffect(() => {
    if (isMyProfile && location.search.includes("edit=true")) {
      setIsEditing(true);
    }
  }, [location.search, isMyProfile]);

  const handleEditClick = () => setIsEditing(true);

  const handleCancelEdit = () => {
    setIsEditing(false);
    setFormData(profileData);
    setErrors({});
  };

  const handleSave = async (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!formData.username?.trim()) {
      newErrors.username = "Username is required";
    }

    if (formData.description?.length > 200) {
      newErrors.description = "Description must be 200 characters or less";
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    const userId = LocalStorage.authUserId.get();
    if (!userId) {
      toast.error(t('pleaseLogInToSaveProfile') || 'Please log in to save your profile');
      setIsLoading(false);
      return;
    }

    try {
      console.log('Saving profile for user ID:', userId);
      console.log('Form data:', formData);

      // Prepare profile data according to the API specification
      const profileData = {
        bio: formData.description || formData.bio || '',
        language: formData.languages ? formData.languages.map(lang => getLanguageCode(lang)) : ['en'],
        games: Array.isArray(formData.games) ? formData.games : [],
        communication_preferences: communicationMap[formData.communication] || 'Written',
        username: formData.username,
        avatar_url: formData.avatar_url || ''
      };

      console.log('Prepared profile data for API:', profileData);

      // Make the PUT request to update the profile
      console.log('Updating profile...');
      const response = await apiService.put('/user_profiles/', profileData);
      console.log('Profile update response:', response);

      if (response && response.data) {
        // Show success message with sonner toast
        toast.success(t('profileUpdated') || 'Profile Updated', {
          description: t('profileUpdateSuccess') || 'Your profile changes have been saved successfully!'
        });

        // Exit edit mode
        setIsEditing(false);

        // Remove edit parameter from URL
        const searchParams = new URLSearchParams(window.location.search);
        if (searchParams.has('edit')) {
          searchParams.delete('edit');
          const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
          window.history.replaceState({}, '', newUrl);
        }

        // Reload the profile data to ensure we have the latest from the server
        await loadProfile();
      }
    } catch (error) {
      console.error('Error updating profile:', error);
      const errorMessage = error.response?.data?.message ||
        error.message ||
        t('failedToUpdateProfile') || 'Failed to update profile. Please try again.';
      toast.error(errorMessage);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleGameToggle = game => {
    setFormData(prev => {
      // Ensure games is an array
      const currentGames = Array.isArray(prev.games) ? [...prev.games] : [];
      const gameIndex = currentGames.indexOf(game);

      // Toggle the game in the array
      if (gameIndex === -1) {
        currentGames.push(game); // Add the game if not present
      } else {
        currentGames.splice(gameIndex, 1); // Remove the game if present
      }

      return {
        ...prev,
        games: currentGames
      };
    });
  };

  const handleCommunicationToggle = (option) => {
    setFormData(prev => ({
      ...prev,
      communication: option
    }));
  };

  const handleOpennessToggle = (option) => {
    setFormData(prev => ({
      ...prev,
      openness: option
    }));
  };

  const handleLanguageToggle = language => {
    setFormData(prev => ({
      ...prev,
      languages: prev.languages.includes(language)
        ? prev.languages.filter(l => l !== language)
        : [...prev.languages, language]
    }));
  };

  const handleAvatarChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setIsLoading(true);
      // Here you would typically upload the file to your server
      // and get back the URL, then update the profile with the new URL
      const formData = new FormData();
      formData.append('avatar', file);

      const response = await apiService.uploadAvatar(formData);
      const avatarUrl = response.data.url;

      // Update both form and profile data
      setFormData(prev => ({ ...prev, avatar_url: avatarUrl }));
      setProfileData(prev => ({ ...prev, avatar_url: avatarUrl }));

      toast.success(t('profilePictureUpdated') || 'Profile picture updated successfully');
    } catch (error) {
      console.error('Error uploading avatar:', error);
      toast.error(t('failedToUpdateProfilePicture') || 'Failed to update profile picture');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePhotoUpload = e => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = e => {
        setFormData(prev => ({ ...prev, profilePhoto: e.target.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mx-auto"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mx-auto"></div>
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded mt-4"></div>
        </div>
      </div>
    );
  }

  // Only show not found if we're not in edit mode and have no data
  if (!isEditing && (!profileData || Object.keys(profileData).length === 0)) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Profile not found</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          {isMyProfile
            ? "You don't have a profile yet. Click 'Edit' to create one."
            : `Could not find a player with the username "${viewedUsername || loggedInUsername}"`
          }
        </p>
        {isMyProfile && (
          <button
            onClick={() => setIsEditing(true)}
            className="mt-4 bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-lg"
          >
            Create Profile
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 p-4">
      <div className="max-w-4xl mx-auto">
        {isEditing ? (
          <form onSubmit={handleSave}>
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-100 dark:border-gray-700 p-4">
              <div className="flex flex-col lg:flex-row items-center lg:items-start lg:space-x-6 mb-6">
                <div className="flex-shrink-0 mb-4 lg:mb-0 flex flex-col items-center">
                  <div className="relative mb-2">
                    <div className="w-20 h-20 bg-gradient-to-br from-teal-100 to-teal-200 rounded-2xl flex items-center justify-center overflow-hidden shadow-lg">
                      {profileData.avatar_url ? (
                        <img
                          src={profileData.avatar_url}
                          alt="Profile"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            // Fallback to default avatar if image fails to load
                            e.target.src = '/default-avatar.png';
                            e.target.onerror = null; // Prevent infinite loop if default image also fails
                          }}
                        />
                      ) : (
                        <div className="w-20 h-20 rounded-2xl bg-gray-200 flex items-center justify-center">
                          <User className="w-10 h-10 text-gray-400" />
                        </div>
                      )}
                    </div>
                    {/* {isEditing && (
                      <label className="absolute bottom-0 right-0 bg-teal-500 text-white rounded-full p-2 cursor-pointer hover:bg-teal-600 transition-colors">
                        <Camera className="w-5 h-5" />
                        <input 
                          type="file" 
                          className="hidden" 
                          accept="image/*"
                          onChange={handleAvatarChange}
                        />
                      </label>
                    )} */}
                  </div>
                </div>
                <div className="flex-grow text-center lg:text-left">
                  {/* {isEditing ? (
                    <Input
                      value={formData.username}
                      onChange={e =>
                        setFormData(prev => ({
                          ...prev,
                          username: e.target.value
                        }))
                      }
                      className="text-2xl font-bold text-gray-800 mb-2 h-auto text-center lg:text-left"
                    />
                  ) : (
                    <h1 className="text-2xl font-bold text-gray-800 mb-2 text-center lg:text-left">
                      {formData.username}
                    </h1>
                  )}
                  {errors.username && isEditing && (
                    <p className="text-red-500 text-xs mt-1">
                      {errors.username}
                    </p>
                  )} */}

                  <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2 text-center lg:text-left">
                    {formData.username}
                  </h1>

                  {isEditing ? (
                    <Textarea
                      value={formData.description}
                      onChange={e =>
                        setFormData(prev => ({
                          ...prev,
                          description: e.target.value
                        }))
                      }
                      placeholder={t("profile.description.placeholder")}
                      className="text-sm h-16 text-gray-600 dark:text-gray-300 dark:bg-gray-900 dark:border-gray-700 dark:placeholder-gray-400 text-center lg:text-left"
                      maxLength={200}
                    />
                  ) : (
                    <p className="text-sm text-gray-600 dark:text-gray-300 text-center lg:text-left mb-3">
                      {formData.description || t("profile.description.placeholder")}
                    </p>
                  )}
                  {errors.description && isEditing && (
                    <p className="text-red-500 text-xs mt-1">
                      {errors.description}
                    </p>
                  )}
                  <div className="flex justify-center lg:justify-start space-x-6 mb-2">
                    {/* <div className="text-center">
                      <p className="text-lg font-bold text-teal-600">
                        {profileData?.friends?.length || 0}
                      </p>
                      <p className="text-xs text-gray-500">Friends</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-teal-600">
                        {profileData?.games?.length || 0}
                      </p>
                      <p className="text-xs text-gray-500">Games</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-teal-600">
                        {profileData?.sessions || 0}
                      </p>
                      <p className="text-xs text-gray-500">Sessions</p>
                    </div> */}
                  </div>
                </div>
              </div>
            </div>
            <div className="h-px bg-gray-200 dark:bg-gray-700 mb-4"></div>
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 mb-2">
                  {t("profile.fields.languages")}
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {availableLanguages.map(language => (
                    <button
                      key={language}
                      type="button"
                      disabled={!isEditing}
                      onClick={() => handleLanguageToggle(language)}
                      className={`p-2 rounded-lg border text-center text-xs font-medium transition-all disabled:cursor-default ${(formData.languages || []).includes(language)
                        ? "border-teal-500 dark:border-teal-700 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200"
                        : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500"
                        }`}
                    >
                      {language}
                    </button>
                  ))}
                </div>
              </div>
              <div className="h-px bg-gray-200 dark:bg-gray-700 mb-4"></div>
              <div className="space-y-6">
                {/* Communication Preferences */}
                <div>
                  <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    {t("profile.fields.communication")}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {communicationOptions.map(option => (
                      <button
                        key={option}
                        type="button"
                        disabled={!isEditing}
                        onClick={() => handleCommunicationToggle(option)}
                        className={`p-2 rounded-lg border text-center text-xs font-medium transition-all disabled:cursor-default ${formData.communication === option
                          ? "border-teal-500 dark:border-teal-700 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200"
                          : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500"
                          }`}
                      >
                        {t(`profile.communicationOptions.${option}`)}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Openness to New Users */}
                {/* <div>
                  <h3 className="text-base font-semibold text-gray-800 mb-2">
                    Openness to New Users
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {opennessOptions.map(option => (
                      <button
                        key={option}
                        type="button"
                        disabled={!isEditing}
                        onClick={() => handleOpennessToggle(option)}
                        className={`p-2 rounded-lg border text-center text-xs font-medium transition-all disabled:cursor-default ${
                          formData.openness === option
                            ? "border-teal-500 bg-teal-50 text-teal-700"
                            : "border-gray-200 bg-white hover:border-gray-300"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div> */}

                {/* Favorite Games */}
                <div>
                  <h3 className="text-base font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    {t("favoriteGames")}
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {popularGames.map(game => {
                      // Ensure games is always an array before calling includes
                      const gamesArray = Array.isArray(formData.games) ? formData.games : [];
                      const isSelected = gamesArray.includes(game);

                      return (
                        <button
                          key={game}
                          type="button"
                          disabled={!isEditing}
                          onClick={() => handleGameToggle(game)}
                          className={`p-2 rounded-lg border text-center text-xs font-medium transition-all disabled:cursor-default ${isSelected
                            ? "border-teal-500 dark:border-teal-700 bg-teal-50 dark:bg-teal-900/50 text-teal-700 dark:text-teal-200"
                            : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500"
                            }`}
                        >
                          {game}
                        </button>
                      );
                    })}
                  </div>
                </div>
                {/* Action buttons container */}
                <div className="flex justify-between items-center pt-4 border-t border-gray-200 dark:border-gray-700">
                  {/* Edit button (left side) */}
                  {!isEditing && (
                    <button
                      type="button"
                      onClick={handleEditClick}
                      className="bg-teal-600 hover:bg-teal-700 text-white flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                      <Edit className="w-4 h-4" />
                      <span>{t("editProfile")}</span>
                    </button>
                  )}

                  {/* Save/Cancel buttons (right side) */}
                  {isEditing && (
                    <div className="flex gap-3 ml-auto">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={handleCancelEdit}
                        className="px-4 py-2 text-sm min-w-[80px]"
                      >
                        {t("cancel")}
                      </Button>
                      <Button
                        type="submit"
                        className="bg-teal-600 hover:bg-teal-700 text-white flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors min-w-[80px]"
                      >
                        <Save className="w-3 h-3" />
                        <span>{t("save")}</span>
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </form>
        ) : (
          <div>
            <ProfileHeader player={profileData} isMyProfile={false} currentUser={currentUser} />
            <div className="grid md:grid-cols-3 gap-6 mt-8">
              <div className="md:col-span-1">
                <GameList games={profileData.games} allGames={allGames} />
              </div>
              <div className="md:col-span-2">
                <div className="md:col-span-2">
                  {/* <AvailabilityDisplay
                  availability={profileData.availability}
                  prefersCustom={profileData.prefers_custom_availability}
                /> */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700">
                    <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">{t("profileDetails")}</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <span className="text-sm text-gray-500 dark:text-gray-400 block">{t("about")}</span>
                        <p className="text-gray-700 dark:text-gray-300 text-sm mt-1 whitespace-pre-wrap">
                          {profileData.description || t("noDescriptionProvided")}
                        </p>
                      </div>
                      <div className="space-y-4">
                        <div>
                          <span className="text-sm text-gray-500 dark:text-gray-400 block">{t("profile.fields.languages")}</span>
                          <div className="flex flex-wrap gap-2 mt-1">
                            {profileData.languages && profileData.languages.length > 0 ? (
                              profileData.languages.map((lang, idx) => (
                                <span key={idx} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300">{lang}</span>
                              ))
                            ) : (
                              <span className="text-gray-400 italic">{t("noLanguagesListed")}</span>
                            )}
                          </div>
                        </div>
                        <div>
                          <span className="text-sm text-gray-500 dark:text-gray-400 block">{t("profile.fields.communication")}</span>
                          <span className="text-gray-700 dark:text-gray-300">{t(`profile.communicationOptions.${profileData.communication}`)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
