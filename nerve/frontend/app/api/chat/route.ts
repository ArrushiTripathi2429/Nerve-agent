import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { message, session_id, stream = false } = await req.json();

  if (stream) {
    const response = await fetch("http://localhost:8000/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id }),
    });
    return new Response(response.body, {
      headers: { "Content-Type": "text/event-stream" },
    });
  }

  const response = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id }),
  });
  const data = await response.json();
  return NextResponse.json({
    reply: data.reply,
    actions_taken: data.actions_taken || [],
    refresh_dashboard: data.refresh_dashboard || false,
  });
}