import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

async function hasValidAuthentication(request: NextRequest) {
  if (!request.cookies.has("auth_token")) return false;

  try {
    const response = await fetch(`${backend}/api/auth/me/`, {
      headers: { cookie: request.headers.get("cookie") ?? "" },
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function proxy(request: NextRequest) {
  const authenticated = await hasValidAuthentication(request);
  const isDashboard = request.nextUrl.pathname.startsWith("/dashboard") || request.nextUrl.pathname === "/reports";
  const isGuestOnly = ["/login", "/register"].includes(request.nextUrl.pathname);

  if (isDashboard && !authenticated) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.cookies.delete("auth_token");
    return response;
  }
  if (isGuestOnly && authenticated) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  const response = NextResponse.next();
  if (request.cookies.has("auth_token") && !authenticated) {
    response.cookies.delete("auth_token");
  }
  return response;
}

export const config = {
  matcher: ["/dashboard/:path*", "/reports", "/login", "/register"],
};
