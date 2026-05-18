"use client";

import { useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import { usePathname } from "next/navigation";

export function SessionExpiredModal() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener("aria:unauthorized", handler);
    return () => window.removeEventListener("aria:unauthorized", handler);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className="bg-white rounded-2xl p-6 shadow-xl max-w-sm w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-moore-black mb-2">Session Expired</h3>
        <p className="text-sm text-moore-mid-gray mb-5">
          Your session has timed out. Sign in again to continue where you left off.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => setOpen(false)}
            className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-moore-dark-gray hover:bg-gray-50 transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={() =>
              signIn(undefined, { callbackUrl: pathname ?? "/dashboard" })
            }
            className="rounded-xl bg-moore-red px-4 py-2 text-sm font-semibold text-white hover:bg-moore-red-dark transition-colors"
          >
            Sign In Again
          </button>
        </div>
      </div>
    </div>
  );
}
