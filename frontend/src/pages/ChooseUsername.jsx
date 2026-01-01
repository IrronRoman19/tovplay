
import { Formik, Form, Field } from "formik";
import { User, ArrowRight, Check, X } from "lucide-react";
import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import * as Yup from "yup";
import { checkUserNameAvailability } from "@/stores/profileSlice";
import { createPageUrl } from "@/utils";

export default function ChooseUsername() {
  const navigate = useNavigate();
  const [usernameLastChecked, setUsernameLastChecked] = useState("");
  // const profile = useSelector((state) => state.profile);
  const dispatch = useDispatch();
  const { isAvailable, isChecking, error } = useSelector(state => state.profile);
  let t = null;

  const handleSubmit = async values => {
    navigate(createPageUrl("SelectGames"));
  };

  const validateUsername = username => {

    // don't validate if usernameLastCheck is the same
    if (username === usernameLastChecked) {
      return;
    }

    // username changed -> clear interval
    if (t) {
      clearTimeout(t);
    }

    // if username is less than 3 characters -> return
    if (username && username.length <= 3) {
      return;
    }

    // else, create new timeout
    if (!t || t > 1) {
      t = setTimeout(() => {
        setUsernameLastChecked(username);
        dispatch(checkUserNameAvailability(username));
        // console.log("Checking availability for:", username);
      }, 1000);
    }
  };

  const usernameSchema = Yup.object().shape({
    username: Yup.string()
      .min(3, "Username must be at least 3 characters")
      .max(20, "Username must not exceed 20 characters")
      .required("Required")
  });

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <User className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Choose Your Username</h1>
          <p className="text-gray-600">Step 2 of 5</p>
        </div>

        <div className="progress-bar mb-8">
          <div className="progress-fill" style={{ width: "40%" }}></div>
        </div>

        <Formik
          initialValues={{
            username: ""
          }}
          validationSchema={usernameSchema}
          onSubmit={handleSubmit}>

          <Form className="calm-card">
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <div className="relative">


                  <Field
                    name="username"
                    type="text"
                    validate={validateUsername}
                    className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
                    placeholder="Choose a username"
                  />

                </div>
                {(isAvailable && !isChecking) && (
                  <p className="text-xs text-green-600 mt-2 flex items-center">
                    <Check className="w-3 h-3 mr-1" />
                    This username is available
                  </p>
                )}
                {(isAvailable == false && !isChecking) && (
                  <p className="text-xs text-red-600 mt-2 flex items-center">
                    <X className="w-3 h-3 mr-1" />
                    This username is not available
                  </p>
                )}
                {isChecking && (
                  <p className="text-xs text-gray-500 mt-2">
                    Checking username availability...
                  </p>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  This is how other players will know you. Choose something that feels right for you.
                </p>
              </div>

              <button
                type="submit"
                className="calm-button w-full flex items-center justify-center space-x-2"
                disabled={!isAvailable}
              >
                <span>Save & Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </Form>

        </Formik>


        <div className="text-center mt-6">
          <Link to={createPageUrl("CreateAccount")} className="text-sm text-teal-600 hover:text-teal-700 underline">
            Go Back
          </Link>
        </div>

      </div>
    </div>
  );
}
