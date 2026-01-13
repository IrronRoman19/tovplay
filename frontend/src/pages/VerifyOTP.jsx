import { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import axios from '@/lib/axios-config';
import { createPageUrl } from "@/utils";

const VerifyOTP = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState("verifying"); // verifying, success, error

    useEffect(() => {
        const verifyEmail = async () => {
            const email = searchParams.get("email");
            const otp = searchParams.get("otp") || searchParams.get("otp_code");

            if (!email || !otp) {
                console.error("Missing email or otp in URL");
                setStatus("error");
                return;
            }

            try {
                const response = await axios.get(`/api/auth/verify-otp?email=${email}&otp_code=${otp}`);

                if (response.status === 200 || response.status === 201) {
                    setStatus("success");
                    setTimeout(() => {
                        navigate(createPageUrl('SignIn'));
                    }, 3000); // reduced to 3s for better UX
                } else {
                    setStatus("error");
                }

            } catch (error) {
                console.error("Error verifying email:", error);
                setStatus("error");
            }
        };

        verifyEmail();
    }, [searchParams, navigate]);

    if (status === "verifying") {
        return <div>Verifying your email...</div>;
    }

    if (status === "error") {
        return <div>Error verifying email. Please request a new verification link.</div>;
    }

    return (
        <div>Your mail {searchParams.get("email")} has been verified. Redirecting to login Page ...</div>
    );
}

export default VerifyOTP;