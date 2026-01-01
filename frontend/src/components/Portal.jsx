import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

export default function Portal({ children }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (typeof window === "undefined" || !mounted) {
    return null;
  }

  return createPortal(
    children,
    document.body
  );
}
