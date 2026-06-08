export const runtime = "edge";

const BACKEND = process.env.BACKEND_URL || "https://nerve-backend-64653683018.us-central1.run.app";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${BACKEND}/api/whatif`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
