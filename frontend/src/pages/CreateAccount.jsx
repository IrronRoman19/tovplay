// Minimal working react-tooltip example for debugging
import 'react-tooltip/dist/react-tooltip.css';
import { Tooltip } from 'react-tooltip';
import React, { useEffect, useState, useContext, useMemo } from 'react';
import { Formik, Form, Field } from 'formik';
// import { GoogleLogin, useGoogleLogin } from '@react-oauth/google';
import * as Yup from 'yup';
import { Check, X, Lock, Mail, User } from 'lucide-react';
import { useDispatch, useSelector } from 'react-redux';
import {
  setUsername,
  checkUserNameAvailability,
  setUserId,
  setIsAvailable,
} from '@/stores/profileSlice';
import axios from '@/lib/axios-config';
// import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useNavigate } from 'react-router-dom';
import { createPageUrl } from '@/utils';
import { toast } from 'sonner';
import { Circles } from 'react-loader-spinner';
import { LanguageContext } from '@/components/lib/LanguageContext';



export default function CreateAccount({
  onSubmit,
  submitText,
  className = '',
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step, setStep] = useState(0);
  const prevStep = () => {
    setStep((s) => Math.max(s - 1, 0));
    return false;
  };
  const nextStep = () => {
    // go to next step
    setStep((s) => Math.min(s + 1, 1));
  };
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(setIsAvailable({ isAvailable: null }));
  }, []);

  //
  const dispatch = useDispatch();
  const [usernameLastChecked, setUsernameLastChecked] = useState('');
  const { isAvailable, isChecking, error: profileError } = useSelector(
    (state) => state.profile
  );
  const { t, language } = useContext(LanguageContext);

  // Helper function to translate backend error messages
  const translateErrorMessage = (errorMsg) => {
    if (!errorMsg) return t('signupFailed');
    
    // Map of backend error messages to translation keys
    const errorMap = {
      'Failed to create user': 'failedToCreateUser',
      'User created successfully!': 'accountCreated',
      'User ID not received in response': 'userIdNotReceived',
    };
    
    // Check if we have a translation for this error
    const translationKey = errorMap[errorMsg];
    return translationKey ? t(translationKey) : errorMsg;
  };

  // Validation Schema - wrapped in useMemo to update when language changes
  const SignupSchema = useMemo(() => Yup.object({
    email: Yup.string()
      .required(t('emailRequired'))
      .test(
        'email-format',
        t('invalidEmailFormat'),
        (value) => {
          if (!value.includes('@')) return false;
          return /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value) && 
                !/[^a-zA-Z0-9.@_-]/.test(value);
        }
      ),
    password: Yup.string(),
    passwordConfirmation: Yup.string()
      .oneOf([Yup.ref('password'), null], t('passwordsMustMatch'))
      .required(t('passwordConfirmationRequired')),
    username: Yup.string()
      .required(t('emailRequired'))
      .min(3, t('usernameMinLength'))
      .max(30, t('usernameMaxLength'))
      .test(
        'valid-chars',
        t('usernameValidChars'),
        (value) => !value || /^[\u0590-\u05FFa-zA-Z0-9_\-.]*$/.test(value)
      )
      .test(
        'no-consecutive-special',
        t('usernameNoConsecutiveSpecial'),
        (value) => !value || !/[_.-]{2,}/.test(value)
      )
      .test(
        'min-length',
        t('usernameMinLength'),
        (value) => !value || value.length >= 3
      )
      .test(
        'max-length',
        t('usernameMaxLength'),
        (value) => !value || value.length <= 30
      ),
    discordUsername: Yup.string()
      .test(
        'discord-format',
        t('discordUsernameInvalid'),
        (value) => {
          // New format: 3-30 alphanumeric + underscore
          const newFormat = /^[a-zA-Z0-9_]{3,30}$/;
          // Legacy format: username#1234
          const legacyFormat = /^[a-zA-Z0-9_.]{2,32}#\d{4}$/;
          return newFormat.test(value) || legacyFormat.test(value);
        }
      )
      .required(t('required')),
  }), [language, t]);

  const handleSubmit = async (values, { setSubmitting, setFieldError }) => {
    console.log('handleSubmit called', { values });
    setIsSubmitting(true);
    try {
      const response = await axios.post('/api/users/signup', {
        Email: values.email,
        Password: values.password,
        Username: values.username,
        DiscordUsername: values.discordUsername,
      });

      const userId = response?.data?.user_id;
      if (userId) {
        localStorage.setItem('userId', userId);
        localStorage.setItem('isAuthenticated', 'true');
        dispatch(setUserId({ userId }));
        
        // Show success popup
        toast.success(t('accountCreated'), {
          description: t('redirectingToSignIn'),
          duration: 3000
        });
        
        // Navigate after a short delay to show the success message
        setTimeout(() => {
          navigate(createPageUrl('SignIn'));
        }, 1500);
      } else {
        throw new Error(t('userIdNotReceived'));
      }
    } catch (error) {
      console.error('Signup error:', error);
      const backendMessage = error.response?.data?.message || error.message;
      const errorMessage = translateErrorMessage(backendMessage);
      
      // Show error popup
      toast.error(t('signupFailed'), {
        description: errorMessage,
        duration: 5000,
        position: 'top-center',
        // action: {
        //   label: 'Try Again',
        //   onClick: () => window.location.reload()
        // }
      });
      
      // Also set field error for form validation
      setFieldError('general', errorMessage);
    } finally {
      setIsLoading(false);
      setIsSubmitting(false);
    }
  };

  const validateEmail = email => {
    if (email === "") {
      return "Email is required";
    }
    const emailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;
    return emailRegex.test(email) ? null : 'Invalid email address';
  };

  const validateUsername = (username) => {
    //
    let error;

    // don't validate if usernameLastCheck is the same
    if (!username || username === usernameLastChecked) return;

    // username changed -> clear interval
    if (t) clearTimeout(t);

    // else, create new timeout
    if (!t || t > 1) {
      t = setTimeout(async () => {
        setUsernameLastChecked(username);
        const result = await dispatch(checkUserNameAvailability(username));
        // const userId = result?.data?.userId;
        // if (userId) {
        //     localStorage.setItem('userId', userId); // Store userId in localStorage
        //     dispatch(setUserId({ userId })); // Store userId in Redux state
        // }
        console.log('result', result);
      }, 1000);
    }
  };

  // google login - commented out as not currently used
  // const login = useGoogleLogin({
  //   onSuccess: (tokenResponse) => {
  //     /* handle success */
  //     console.log('Google login successful:', tokenResponse);
  //   },
  //   onError: () => {
  //     /* handle error */
  //   },
  // });

  const validatePassword = (value) => {
    //
    const validators = [
      {
        valfunc: (value) => value.length >= 8,
        vlamsg: t('passwordMinLength'),
      },
      {
        valfunc: (value) => /[a-z]/.test(value),
        vlamsg: t('passwordLowercase'),
      },
      {
        valfunc: (value) => /[A-Z]/.test(value),
        vlamsg: t('passwordUppercase'),
      },
      {
        valfunc: (value) => /[0-9]/.test(value),
        vlamsg: t('passwordNumber'),
      },
      {
        valfunc: (value) => /[@#$!%*?&]/.test(value),
        vlamsg: t('passwordSpecialChar'),
      },
    ];

    //
    const result = [];
    let isValid = true;

    // iterate each option from validators
    validators.forEach((validator) => {
      if (validator.valfunc(value)) {
        result.push(
          <div className="text-green-400" key={validator.vlamsg}>
            <Check className="inline-block mr-2" />
            <span className="text-white">{validator.vlamsg}</span>
          </div>
        );
      } else {
        result.push(
          <div className="text-red-400" key={validator.vlamsg}>
            <X className="inline-block mr-2" />
            <span className="text-white">{validator.vlamsg}</span>
          </div>
        );
        isValid = false;
      }
    });

    // Formik expects `null` when the field is valid (no error).
    return isValid ? null : result;
  };

  const validatePasswordConfirmation = (conf, values) => {
    let error;
    if (!conf) {
      error = t('passwordConfirmationRequired');
    } else if (conf !== values.password) {
      error = t('passwordsDoNotMatch');
    }

    return error;
  };


  const validateForm = (values) => {
    const errors = {};

    errors.email = t('emailNotValid');

    if (values.password.length < 8) {
      errors.password = t('passwordMustBeAtLeast8');
    }

    if (values.passwordConfirmation !== values.password) {
      errors.passwordConfirmation = t('passwordsMustMatch');
    }

    return errors;
  };

  const checkAreFirstThreeValid = (errors, touched) => {
    let isValid = true;

    // check email, password, passwordConfirmation
    if (errors.email || !touched.email) {
      return false;
    }

    if (errors.password) {
      let innerResult = true;
      errors.password.forEach((err) => {

        if (err.props.className.includes('text-red-400')) {
          innerResult = false;
        }
      });

      if (!innerResult) {
        return false;
      }
    }

    if (errors.passwordConfirmation || !touched.passwordConfirmation) {
      return false;
    }

    return isValid;
  }

  const checkAreLastTwoValid = (errors, touched) => {
    // Check if there are any validation errors for username or discordUsername
    if (errors.username || errors.discordUsername) {
      return false;
    }
    
    // Check if the fields have been touched
    if (!touched.username || !touched.discordUsername) {
      return false;
    }
    
    // If we're checking availability, wait for that to complete
    if (isChecking) {
      return false;
    }
    
    // If we have an availability check result, use it
    // Otherwise (null means not checked yet), only check basic validation
    if (isAvailable !== null) {
      return isAvailable;
    }
    
    // If no availability check yet, just check basic validation
    return true;
  };

  return (
    <>

      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-md p-8">
            <div className="w-16 h-16 border-4 border-teal-200 border-t-teal-700 rounded-full animate-spin mx-auto"></div>
            <p className="mt-4 text-center text-gray-600 dark:text-gray-300">{t('loading')}</p>
          </div>
        </div>
      )}

      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-teal-50 dark:from-gray-900 dark:to-gray-800 p-4">
        <div className="max-w-md w-full">
          {/* <!-- Logo --> */}
          <div className="mx-auto mb-6">
            <img
              src="https://tovplay.org/lovable-uploads/b1e62294-a51b-4e1e-8f0e-4e1472f1a562.png"
              alt={t('tovPlayLogo')}
              className="h-16 mx-auto"
            />
          </div>

          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-2">{t('createAccount')}</h1>
            <p className="text-gray-600 dark:text-gray-300">{t('joinCommunity')}</p>
          </div>

          <Formik
            initialValues={{
              email: '',
              password: '',
              passwordConfirmation: '',
              username: '',
              discordUsername: ''
            }}
            validationSchema={SignupSchema}
            validateOnChange={true}
            validateOnBlur={true}
            validateOnMount={false}
            onSubmit={handleSubmit}
          >
            {({
              errors,
              touched,
              isValid,
              handleChange,
              setFieldTouched,
              validateField,
              values,
              submitForm,
              //isSubmitting,
            }) => {
              // Move this above the return statement
              const areFirstThreeValid = checkAreFirstThreeValid(
                errors,
                touched
              );

              //
              const areLastTwoValid = checkAreLastTwoValid(errors, touched);

              return (
                <Form>
                  {/* Step 1 */}
                  <div className={`${step === 0 ? "block" : "hidden"}`}>
                    {/* <!-- Google Sign-up Button --> */}
                    {/* <button
                      type="button"
                      onClick={() => login()}
                      className="w-full flex items-center justify-center bg-white border border-gray-300 text-gray-700 py-3 px-4 rounded-xl shadow-sm hover:bg-gray-50 transition mb-6"
                    >
                      <img
                        src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Google_%22G%22_logo.svg/480px-Google_%22G%22_logo.svg.png"
                        alt="Google logo"
                        className="w-5 h-5 mr-2"
                      />
                      Sign in with Google
                    </button> */}

                    {/* <!-- Divider --> */}
                    {/*<div className="flex items-center my-6">
                      <div className="flex-grow border-t border-gray-300"></div>
                      <span className="mx-4 text-gray-500">OR</span>
                      <div className="flex-grow border-t border-gray-300"></div>
                    </div>*/}

                    {/* <!-- Email Input --> */}
                    <div className="space-y-6">
                      <div className="mb-4">
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          {t('emailAddress')}
                        </label>
                        <Field
                          name="email"
                          type="email"
                          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
                            errors.email && touched.email
                              ? 'border-red-500 focus:ring-red-200 dark:border-red-500'
                              : 'focus:border-teal-500 focus:ring-teal-200 border-gray-300 dark:border-gray-600'
                          }`}
                          onChange={(e) => {
                            handleChange(e);
                            setFieldTouched('email', true, false);
                            validateField('email');
                          }}
                          onBlur={(e) => {
                            setFieldTouched('email', true, true);
                            validateField('email');
                          }}
                          value={values.email}
                        />
                        <div className="text-xs text-red-500 mt-2">
                          {errors.email && touched.email ? (
                            <div className="flex items-center">
                              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                              {errors.email}
                            </div>
                          ) : (
                            <div>&nbsp;</div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Lock className="w-4 h-4 inline mr-2" />
                        {t('password')}
                      </label>
                      <div>
                        <Field
                          name="password"
                          type="password"
                          placeholder={t('createPasswordPlaceholder')}
                          autoComplete="off"
                          validate={validatePassword}
                          value={values.password}
                          className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                          maxLength={20}
                          data-tooltip-id={'password-error-tip'}
                          // data-tooltip-html={errors.password}
                          data-html={true}
                        />
                        <Tooltip id="password-error-tip" place="right">
                          {errors.password}
                        </Tooltip>
                        <div>&nbsp;</div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <Lock className="w-4 h-4 inline mr-2" />
                        {t('confirmPassword')}
                      </label>
                      <Field
                        name="passwordConfirmation"
                        type="password"
                        placeholder={t('confirmPasswordPlaceholder')}
                        autoComplete="off" // validate={validatePasswordConfirmation}
                        onChange={(e) => {
                          handleChange(e);
                          setFieldTouched('passwordConfirmation', true, false);
                          validateField('passwordConfirmation');
                        }}
                        onBlur={(e) => {
                          setFieldTouched('passwordConfirmation', true, true);
                          validateField('passwordConfirmation');
                        }}
                        value={values.passwordConfirmation}
                        className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        maxLength={20}
                      />
                      <div className="text-xs text-red-600 mt-2">
                        {errors.passwordConfirmation &&
                        touched.passwordConfirmation ? (
                          <div>{errors.passwordConfirmation}</div>
                        ) : (
                          <div>&nbsp;</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className={`${step === 1 ? "block" : "hidden"}`}>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <User className="w-4 h-4 inline mr-2" />
                        {t('username')}
                      </label>
                      <div className="relative">
                        <Field
                          name="username"
                          type="text"
                          className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white ${
                            errors.username && touched.username
                              ? 'border-red-500 focus:ring-red-200 dark:border-red-500'
                              : 'focus:border-teal-500 focus:ring-teal-200 border-gray-300 dark:border-gray-600'
                          }`}
                          dir="auto"
                          style={{ textAlign: 'start' }}
                          onChange={(e) => {
                            // Only validate on change if we already have an error
                            const shouldValidate = errors.username && touched.username;
                            handleChange(e);
                            setFieldTouched('username', true, false);
                            if (shouldValidate) {
                              validateField('username');
                            }
                          }}
                          onBlur={(e) => {
                            handleBlur(e);
                            setFieldTouched('username', true, true);
                            validateField('username');
                          }}
                          onKeyDown={(e) => {
                            // Allow all key presses during input
                            // Validation will happen on blur
                            e.stopPropagation();
                          }}
                          value={values.username}
                        />
                      </div>
                      <div className="text-xs text-red-500 mt-2">
                        {errors.username && touched.username ? (
                          <div className="flex items-center">
                            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                            {errors.username}
                          </div>
                        ) : values.username && values.username.length < 3 ? (
                          <p className="text-xs text-red-600 mt-2 flex items-center">
                            <X className="w-3 h-3 mr-1" />
                            {t('usernameMinLength')}
                          </p>
                        ) : isAvailable === true ? (
                          <p className="text-xs text-green-600 mt-2 flex items-center">
                            <Check className="w-3 h-3 mr-1" />
                            {t('usernameAvailable')}
                          </p>
                        ) : isAvailable === false ? (
                          <p className="text-xs text-red-600 mt-2 flex items-center">
                            <X className="w-3 h-3 mr-1" />
                            {t('usernameNotAvailable')}
                          </p>
                        ) : isChecking ? (
                          <p className="text-xs text-gray-500 mt-2">
                            {t('checkingUsername')}
                          </p>
                        ) : (
                          <div className="text-xs text-gray-500 mt-1">
                            {t('usernameRequirements')}
                          </div>
                        )}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        <User className="w-4 h-4 inline mr-2" />
                        {t('discordUsername')}
                      </label>
                      <Field
                        name="discordUsername"
                        autoComplete="off"
                        spellCheck="false"
                        type="text"
                        maxLength={20}
                        className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        placeholder={t('enterDiscordUsername')}
                        onChange={(e) => {
                          handleChange(e);
                          setFieldTouched('discordUsername', true, false);
                          validateField('discordUsername');
                        }}
                        onBlur={(e) => {
                          setFieldTouched('discordUsername', true, true);
                          validateField('discordUsername');
                        }}
                        // onBlur={() => setFieldTouched('discordUsername', true)}
                        value={values.discordUsername}
                      />
                      <div className="text-xs text-red-600 mt-2">
                        {errors.discordUsername && touched.discordUsername ? (
                          <div>{errors.discordUsername}</div>
                        ) : (
                          <div>&nbsp;</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Step 1: Back and Next Buttons */}
                  <div className={`${step === 0 ? 'space-y-3' : 'hidden'}`}>
                    <button
                      type="button"
                      onClick={() => {
                        // Mark core fields as touched so Formik validates them before moving
                        setFieldTouched('email', true);
                        setFieldTouched('password', true);
                        setFieldTouched('passwordConfirmation', true);
                        nextStep();
                      }}
                      disabled={!areFirstThreeValid || !Object.keys(touched).length > 0}
                      className={`w-full bg-teal-600 hover:bg-teal-700 text-white py-2 rounded transition-colors ${
                        !areFirstThreeValid || !Object.keys(touched).length > 0
                          ? 'opacity-50 cursor-not-allowed'
                          : ''
                      }`}
                    >
                      {t('continue')}
                    </button>

                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{t('alreadyHaveAccount')} <a className="text-teal-500 dark:text-teal-400" href="/signin" >{t('signIn')}</a></p>
                  </div>

                  {/* Step 2: Back and Submit Buttons */}
                  <div className={`${step === 1 ? 'space-y-3' : 'hidden'}`}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        prevStep();
                      }}
                      className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 rounded transition-colors flex items-center justify-center gap-2"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                      </svg>
                      {t('back')}
                    </button>
                    <button
                      type="submit"
                      disabled={!areLastTwoValid || isSubmitting}
                      className={`w-full py-2 px-4 rounded-md text-white font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
                        isSubmitting || !areLastTwoValid
                          ? 'bg-teal-400 dark:bg-teal-800 cursor-not-allowed'
                          : 'bg-teal-600 hover:bg-teal-700 dark:bg-teal-700 dark:hover:bg-teal-600 focus:ring-teal-500 dark:focus:ring-offset-gray-800'
                      }`}
                    >
                      {isSubmitting ? t('creatingAccount') : t('createAccount')}
                    </button>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">{t('alreadyHaveAccount')} <a className="text-teal-500 dark:text-teal-400" href="/signin" >{t('signIn')}</a></p>
                  </div>
                </Form>
              );
            }}
          </Formik>
          {/* Toast container is now in App.jsx */}
        </div>
          {isSubmitting &&
                  <div className="fixed lt-0 top-0 w-full h-full bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <Circles
                      height="80"
                      width="80"
                      color="#00a2ff"
                      ariaLabel="circles-loading"
                      wrapperStyle={{}}
                      wrapperClass=""
                      visible={true}
                      />
                    </div>
                  }
      </div>
    </>
  );
}