import { NextResponse } from "next/server";

const API = process.env.NEXT_PUBLIC_API_URL;

export async function GET() {
  return NextResponse.json({ ok: true, from: "Next.js /api/generer" });
}

export async function POST(req: Request) {
  if (!API) {
    return NextResponse.json({ ok: false, error: "NEXT_PUBLIC_API_URL manquante" }, { status: 500 });
  }

  try {
    const payload = await req.json().catch(() => ({}));
    const body = Object.keys(payload).length ? payload : { loterie: "2", mode: "Gb", blocs: 1 };

    const r = await fetch(`${API}/api/generer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await r.text();

    try {
      return NextResponse.json(JSON.parse(data), { status: r.status });
    } catch {
      return new NextResponse(data, {
        status: r.status,
        headers: { "Content-Type": r.headers.get("Content-Type") || "text/plain" },
      });
    }
  } catch (e: unknown) {
    if (e instanceof Error) {
      return NextResponse.json({ ok: false, error: e.message }, { status: 500 });
    }
    return NextResponse.json({ ok: false, error: "Erreur inconnue" }, { status: 500 });
  }
}

