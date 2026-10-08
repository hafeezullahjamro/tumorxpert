import { createContext, useContext } from "react";

export const GuestModeContext = createContext(false);

export function useGuestMode(): boolean {
  return useContext(GuestModeContext);
}

export function hasCookie(name: string): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split(";").some((cookie) => cookie.trim() === `${name}=1`);
}

export function isGuestClient(): boolean {
  return hasCookie("tx_guest");
}

export function isAuthClient(): boolean {
  return hasCookie("tx_auth");
}

export function clearAuthCookies(): void {
  if (typeof document === "undefined") return;
  const expires = "Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = `tx_auth=; expires=${expires}; path=/`;
  document.cookie = `tx_guest=; expires=${expires}; path=/`;
}

export function enterGuestMode(): void {
  clearAuthCookies();
  document.cookie = "tx_guest=1; path=/; SameSite=Lax; Max-Age=7200";
}

export function getLoginRedirect(): string {
  const redirectTo = new URLSearchParams(window.location.search).get("redirect");
  // Login redirects must stay within this application.
  if (!redirectTo?.startsWith("/") || redirectTo.startsWith("//") || redirectTo.includes("\\")) {
    return "/dashboard";
  }
  return redirectTo;
}
