export const runtime = "edge";

const BACKEND = process.env.BACKEND_URL || "https://nerve-backend-64653683018.us-central1.run.app";

export async function POST(req: Request) {
  const { message, session_id, stream = false } = await req.json();

  if (stream) {
    // Use a TransformStream to proxy the SSE from backend
    const backendRes = await fetch(`${BACKEND}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id }),
    });

    if (!backendRes.ok || !backendRes.body) {
      return new Response(
        `data: ${JSON.stringify({ type: "error", content: "Backend unavailable" })}\n\ndata: [DONE]\n\n`,
        { headers: { "Content-Type": "text/event-stream" } }
      );
    }

    // Pipe the backend SSE stream directly to the client
    return new Response(backendRes.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    });
  }

  const response = await fetch(`${BACKEND}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id }),
  });
  const data = await response.json();
  return Response.json({
    reply: data.reply,
    actions_taken: data.actions_taken || [],
    refresh_dashboard: data.refresh_dashboard || false,
  });
}
