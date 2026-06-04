import { NextResponse } from "next/server";
import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

export async function POST(req: Request) {
  const { message } = await req.json();

  const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

  const prompt = `You are Nerve, a D2C financial intelligence assistant for a jewellery brand.
You help analyze business data like orders, revenue, margins, and customer trends.
Answer concisely and actionably.

User question: ${message}`;

  const result = await model.generateContent(prompt);
  const response = result.response.text();

  return NextResponse.json({ reply: response });
}