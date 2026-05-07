import { NextRequest, NextResponse } from "next/server";
import { BACKEND_API_BASE_URL } from "@/lib/config";

const AUTH_COOKIE_NAME = "akp_token";

function isAuthTokenResponse(path: string[]) {
  const joinedPath = path.join("/");
  return joinedPath === "auth/login" || joinedPath === "auth/register";
}

function buildTargetUrl(path: string[], request: NextRequest) {
  const normalizedBase = BACKEND_API_BASE_URL.replace(/\/$/, "");
  const joinedPath = path.join("/");
  const url = new URL(`${normalizedBase}/${joinedPath}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const targetUrl = buildTargetUrl(path, request);

  // IMPORTANT: Don't use `request.text()` for multipart uploads.
  // That forces a full buffered UTF-8 decode and can corrupt multipart boundaries.
  // We pass the raw request body through to the backend instead.
  const requestBody =
    request.method === "GET" || request.method === "HEAD" ? undefined : request.body;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");

  let backendResponse: Response;
  try {
    const fetchOptions: RequestInit & { duplex?: "half" } = {
      method: request.method,
      headers,
      body: requestBody,
      cache: "no-store",
    };

    // When using a streamed body in Node's fetch/undici, `duplex` is required.
    // Only set it when we actually have a body.
    if (requestBody) {
      fetchOptions.duplex = "half";
    }

    console.log(`[PROXY] Forwarding ${request.method} to ${targetUrl}`);
    backendResponse = await fetch(targetUrl, {
      ...fetchOptions,
    });
    console.log(`[PROXY] Backend response: ${backendResponse.status}`);
  } catch (error) {
    console.error(`[PROXY] Error fetching ${targetUrl}:`, error);
    return NextResponse.json(
      {
        detail:
          error instanceof Error
            ? `Backend unreachable: ${error.message}`
            : "Backend unreachable.",
      },
      { status: 502 }
    );
  }

  const contentType =
    backendResponse.headers.get("content-type") ?? "application/json; charset=utf-8";

  const isText = contentType.includes("json") || 
                 contentType.includes("text") || 
                 contentType.includes("html") || 
                 contentType.includes("xml");
  const isBinary = !isText;

  let responseBody: any;
  if (isBinary) {
    const arrayBuffer = await backendResponse.arrayBuffer();
    responseBody = new Uint8Array(arrayBuffer);
  } else {
    responseBody = await backendResponse.text();
  }

  const response = new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "content-type": contentType,
    },
  });

  if (backendResponse.ok && isAuthTokenResponse(path)) {
    try {
      const responseText = typeof responseBody === "string" ? responseBody : new TextDecoder().decode(responseBody);
      const payload = JSON.parse(responseText) as { access_token?: string };
      if (payload.access_token) {
        response.cookies.set({
          name: AUTH_COOKIE_NAME,
          value: payload.access_token,
          path: "/",
          sameSite: "strict",
          maxAge: 60 * 60 * 24,
          httpOnly: false,
        });
      }
    } catch {
      // Ignore cookie setup when the upstream auth response isn't valid JSON.
    }
  }

  return response;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxy(request, context);
}
