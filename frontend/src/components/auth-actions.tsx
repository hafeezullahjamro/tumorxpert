"use client";

import { useEffect, useState } from "react";
import { clearAuthCookies, hasCookie } from "../lib/auth";

export function AuthActions() {
  const [isAuth, setIsAuth] = useState(false);
  const [isGuest, setIsGuest] = useState(false);

  useEffect(() => {
    setIsAuth(hasCookie("tx_auth"));
    setIsGuest(hasCookie("tx_guest"));
  }, []);

  const handleLogout = () => {
    clearAuthCookies();
    window.location.href = "/auth/login";
  };

  if (!isAuth && !isGuest) {
    return (
      <a
        href="/auth/login"
        className="rounded-full border border-slate-200 bg-white/85 px-3.5 py-1.5 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-white"
      >
        Login
      </a>
    );
  }

  return (
    <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/85 px-2.5 py-1">
      <span className="text-[11px] uppercase tracking-[0.12em] text-slate-500">
        {isGuest ? "Guest" : "Signed In"}
      </span>
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-full px-3 py-1 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
        title={isGuest ? "Exit guest mode" : "Logout"}
      >
        {isGuest ? "Exit Guest" : "Logout"}
      </button>
    </div>
  );
}
