export const runtime = "edge";

const BACKEND = process.env.BACKEND_URL || "https://nerve-backend-64653683018.us-central1.run.app";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ session_id: string }> }
) {
  const { session_id } = await params;
  try {
    const res = await fetch(`${BACKEND}/api/chat/sessions/${session_id}`, {
      cache: "no-store",
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    return Response.json({ error: err.message }, { status: 502 });
  }
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ session_id: string }> }
) {
  const { session_id } = await params;
  try {
    const res = await fetch(`${BACKEND}/api/chat/sessions/${session_id}`, {
      method: "DELETE",
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    return Response.json({ error: err.message }, { status: 502 });
  }
}
