import { NextRequest, NextResponse } from "next/server";
import { BACKEND_API_BASE_URL } from "@/lib/config";

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
    const fetchOptions: any = {
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

    backendResponse = await fetch(targetUrl, {
      ...fetchOptions,
    });
  } catch (error) {
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

  const responseText = await backendResponse.text();
  const contentType =
    backendResponse.headers.get("content-type") ?? "application/json; charset=utf-8";

  return new NextResponse(responseText, {
    status: backendResponse.status,
    headers: {
      "content-type": contentType,
    },
  });
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

