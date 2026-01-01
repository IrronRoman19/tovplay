import {
  Route,
  Routes,
  useLocation
} from "react-router-dom";

import ChessPlayers from "./ChessPlayers";
import ChooseUsername from "./ChooseUsername";
import CreateAccount from "./CreateAccount";
import Dashboard from "./Dashboard";
import FindPlayers from "./FindPlayers";
import Friends from "./Friends";
import Layout from "./Layout.jsx";
import OnboardingComplete from "./OnboardingComplete";
import OnboardingSchedule from "./OnboardingSchedule";
import Profile from "./Profile";
import Schedule from "./Schedule";
import SelectGames from "./SelectGames";
import Settings from "./Settings";
import SignIn from "./SignIn";
import Welcome from "./Welcome";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";

import VerifyOTP from "./VerifyOTP";
import LoggedInRoute from "@/components/LoggedinRoute.jsx";
import PublicRoute from "@/components/PublicRoute.jsx";

const PAGES = {
  Welcome: Welcome,
  SignIn: SignIn,
  CreateAccount: CreateAccount,
  ForgotPassword: ForgotPassword,
  ResetPassword: ResetPassword,
  ChooseUsername: ChooseUsername,
  SelectGames: SelectGames,
  OnboardingComplete: OnboardingComplete,
  Dashboard: Dashboard,
  Schedule: Schedule,
  FindPlayers: FindPlayers,
  Settings: Settings,
  MyProfile: Profile,
  UserProfile: Profile,
  OnboardingSchedule: OnboardingSchedule,
  ChessPlayers: ChessPlayers,
  Friends: Friends,
  VerifyOTP: VerifyOTP
};

function _getCurrentPage(url) {
  if (url.endsWith("/")) {
    url = url.slice(0, -1);
  }

  let urlLastPart = url.split("/").pop();

  if (urlLastPart.includes("?")) {
    urlLastPart = urlLastPart.split("?")[0];
  }

  const pageName = Object.keys(PAGES).find(
    page => page.toLowerCase() === urlLastPart.toLowerCase()
  );

  return pageName || "Welcome";
}

function PagesContent({ track, page, identify }) {
  const location = useLocation();
  const currentPage = _getCurrentPage(location.pathname);

  return (
    <Layout currentPageName={currentPage}>
      <Routes>
        {/* Public routes */}
        <Route
          path="/"
          element={
            <PublicRoute>
              <Welcome track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        <Route
          path="/Welcome"
          element={
            <PublicRoute>
              <Welcome track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        <Route
          path="/SignIn"
          element={
            <PublicRoute>
              <SignIn track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        <Route
          path="/ForgotPassword"
          element={
            <PublicRoute>
              <ForgotPassword track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        <Route
          path="/ResetPassword"
          element={
            <PublicRoute>
              <ResetPassword track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        <Route
          path="/CreateAccount"
          element={
            <PublicRoute>
              <CreateAccount track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />
        <Route
          path="/VerifyOTP"
          element={
            <PublicRoute>
              <VerifyOTP track={track} page={page} identify={identify} />
            </PublicRoute>
          }
        />

        {/* Protected routes */}
        <Route element={<LoggedInRoute />}>
          <Route path="/ChooseUsername" element={<ChooseUsername track={track} page={page} identify={identify} />} />
          <Route path="/SelectGames" element={<SelectGames track={track} page={page} identify={identify} />} />
          <Route path="/OnboardingComplete" element={<OnboardingComplete track={track} page={page} identify={identify} />} />
          <Route path="/Dashboard" element={<Dashboard track={track} page={page} identify={identify} />} />
          <Route path="/Schedule" element={<Schedule track={track} page={page} identify={identify} />} />
          <Route path="/FindPlayers" element={<FindPlayers track={track} page={page} identify={identify} />} />
          <Route path="/Settings" element={<Settings track={track} page={page} identify={identify} />} />
          <Route path="/MyProfile" element={<Profile track={track} page={page} identify={identify} />} />
          <Route path="/profile" element={<Profile track={track} page={page} identify={identify} />} />
          <Route path="/UserProfile" element={<Profile track={track} page={page} identify={identify} />} />
          <Route path="/OnboardingSchedule" element={<OnboardingSchedule track={track} page={page} identify={identify} />} />
          <Route path="/ChessPlayers" element={<ChessPlayers track={track} page={page} identify={identify} />} />
          <Route path="/Friends" element={<Friends track={track} page={page} identify={identify} />} />
        </Route>
      </Routes>
    </Layout>
  );
}

export default function Pages(props) {
  return <PagesContent {...props} />;
}
