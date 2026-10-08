import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const PUBLIC_PATHS = ["/auth/login", "/auth/register", "/help", "/api", "/_next", "/favicon.ico"];

function isPublic(pathname: string) {
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

function redirectTo(req: NextRequest, path: string) {
  const url = new URL(path, req.url);
  // Next normalizes loopback URLs to localhost; retain the hostname used by the browser.
  const host = req.headers.get("host");
  if (host) url.host = host;
  return NextResponse.redirect(url);
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (isPublic(pathname)) {
    const hasAuth = req.cookies.get("tx_auth")?.value === "1";
    const hasGuest = req.cookies.get("tx_guest")?.value === "1";
    if (pathname.startsWith("/auth/login") || pathname.startsWith("/auth/register")) {
      if (hasGuest || hasAuth) {
        return redirectTo(req, "/dashboard");
      }
    }
    return NextResponse.next();
  }

  const hasAuth = req.cookies.get("tx_auth")?.value === "1";
  const hasGuest = req.cookies.get("tx_guest")?.value === "1";

  if (!hasAuth && !hasGuest) {
    const search = new URLSearchParams({ redirect: req.nextUrl.pathname + req.nextUrl.search });
    return redirectTo(req, `/auth/login?${search}`);
  }

  if (hasGuest) {
    const guestBlocked = ["/admin", "/settings", "/jobs", "/upload", "/report"];
    if (guestBlocked.some((path) => pathname.startsWith(path))) {
      return redirectTo(req, "/dashboard");
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
