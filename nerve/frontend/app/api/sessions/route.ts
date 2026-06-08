export const runtime = "edge";

const BACKEND = process.env.BACKEND_URL || "https://nerve-backend-64653683018.us-central1.run.app";

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/api/chat/sessions`, { cache: "no-store" });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    return Response.json({ error: err.message }, { status: 502 });
  }
}
