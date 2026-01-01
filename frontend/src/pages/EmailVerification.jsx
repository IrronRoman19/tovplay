import { Formik, Form, Field } from "formik";
import { User, Mail, Lock, ArrowRight, Check, X } from "lucide-react";
import { useState } from "react";
import { useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import * as Yup from "yup";
import { setEmailAndPassword } from "@/stores/profileSlice";
import { checkUserNameAvailability } from "@/stores/profileSlice";
import { createPageUrl } from "@/utils";

// Define validation schema
const SignupSchema = Yup.object({
  email: Yup.string().email("Invalid email address").required("Required"),
  username: Yup.string()
    .min(3, "Username must be at least 3 characters")
    .max(20, "Username must not exceed 20 characters")
    .required("Required"),
  password: Yup.string()
    .min(8, "Password must be at least 8 characters")
    .required("Required"),
  passwordConfirmation: Yup.string()
    .oneOf([Yup.ref("password"), null], "Passwords must match")
    .required("Required")
});

export default function EmailVerification() {
  const [isChecking, setIsChecking] = useState(false);
  const [isAvailable, setIsAvailable] = useState(null);
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // Handle form submission
  const handleSubmit = async (values, { setSubmitting }) => {
    try {
      // Set email and password in Redux store
      dispatch(setEmailAndPassword({ email: values.email, password: values.password }));

      // Navigate to next step
      navigate(createPageUrl("SelectGames"));
    } catch (error) {
      console.error("Error during signup:", error);
    } finally {
      setSubmitting(false);
    }
  };

  // Validate username availability
  const validateUsername = async value => {
    if (!value) {
      return;
    }

    setIsChecking(true);
    try {
      const result = await dispatch(checkUserNameAvailability(value));
      setIsAvailable(result.payload?.available);
    } catch (error) {
      setIsAvailable(false);
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <User className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Create Your Account</h1>
          <p className="text-gray-600">Step 1 of 4</p>
        </div>

        <div className="progress-bar mb-8">
          <div className="progress-fill" style={{ width: "20%" }}></div>
        </div>

        <Formik
          initialValues={{
            email: "",
            username: "",
            password: "",
            passwordConfirmation: ""
          }}
          validationSchema={SignupSchema}
          onSubmit={handleSubmit}>

          {({ errors, touched }) => (
            <Form className="calm-card">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Mail className="w-4 h-4 inline mr-2" />
                    Email Address
                  </label>
                  <Field
                    name="email"
                    placeholder="Enter your email"
                    autoComplete="off"
                    className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
                  />
                  <div className="text-xs text-red-500 mt-2">
                    {errors.email && touched.email ? <div>{errors.email}</div> : <div>&nbsp;</div>}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <User className="w-4 h-4 inline mr-2" />
                    Username
                  </label>
                  <Field
                    name="username"
                    autoComplete="off"
                    type="text"
                    validate={validateUsername}
                    className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
                    placeholder="Choose a username"
                  />
                  <div className="text-xs text-red-500 mt-2">
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
                    {
                      (!isChecking && isAvailable == null) && (
                        <div>&nbsp;</div>
                      )
                    }
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Lock className="w-4 h-4 inline mr-2" />
                    Password
                  </label>
                  <Field
                    name="password"
                    type="password"
                    placeholder="Create a password"
                    autoComplete="off"
                    className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
                  />
                  <div className="text-xs text-red-600 mt-2">
                    {errors.password && touched.password ? <div>{errors.password}</div> : <div>&nbsp;</div>}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Lock className="w-4 h-4 inline mr-2" />
                    Confirm Password
                  </label>
                  <Field
                    name="passwordConfirmation"
                    type="password"
                    placeholder="Confirm your password"
                    autoComplete="off"
                    className="w-full px-3 py-2 border rounded focus:outline-none focus:ring focus:border-blue-300"
                  />
                  <div className="text-xs text-red-600 mt-2">
                    {errors.passwordConfirmation && touched.passwordConfirmation ? <div>{errors.passwordConfirmation}</div> : <div>&nbsp;</div>}
                  </div>
                </div>

                <button type="submit" className="calm-button w-full flex items-center justify-center space-x-2">
                  <span>Continue</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </Form>
          )}
        </Formik>

        <div className="text-center mt-6">
          <Link to={createPageUrl("Welcome")} className="text-sm text-teal-600 hover:text-teal-700 underline">
            Go Back
          </Link>
        </div>
      </div>
    </div>
  );
}
