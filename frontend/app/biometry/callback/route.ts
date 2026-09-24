import { NextRequest, NextResponse } from "next/server";

const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
const frontend = process.env.FRONTEND_PUBLIC_URL ?? "http://localhost:3000";

function redirectToContracts(url: URL) {
  const response = NextResponse.redirect(url, 303);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export async function GET(request: NextRequest) {
  const fallback = new URL("/contracts?biometry=error", frontend);
  const callback = new URL("/api/contracts/biometry/callback/", backend);
  callback.search = request.nextUrl.search;

  try {
    const result = await fetch(callback, { cache: "no-store", redirect: "manual" });
    const location = result.headers.get("location");
    if (result.status === 302 && location) {
      const destination = new URL(location, frontend);
      if (destination.origin === fallback.origin && destination.pathname === "/contracts") {
        return redirectToContracts(destination);
      }
    }
  } catch {
    // A failed internal callback must never be presented as a successful signature.
  }

  return redirectToContracts(fallback);
}
