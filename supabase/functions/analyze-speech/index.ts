// supabase/functions/analyze-speech/index.ts
// Deploy: supabase functions deploy analyze-speech

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: cors });

  // Verify user JWT
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: authHeader } },
  });
  const { data: { user }, error } = await sb.auth.getUser();
  if (error || !user) return new Response(JSON.stringify({ error: "Invalid token" }), { status: 401, headers: cors });

  const { target_phrase, spoken_text, module, accuracy, speech_rate } = await req.json();

  const openAiKey = Deno.env.get("OPENAI_API_KEY");
  let ai_feedback: string;

  if (openAiKey) {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Authorization": `Bearer ${openAiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [{
          role: "user",
          content: `You are a professional speech therapist working on ${module}.
Target: "${target_phrase}"
Patient said: "${spoken_text}"
Accuracy: ${accuracy}%, Speech rate: ${speech_rate} wpm
Write 2-3 sentences of warm, specific, actionable coaching feedback.`,
        }],
        max_tokens: 150,
      }),
    });
    const data = await res.json();
    ai_feedback = data.choices[0].message.content.trim();
  } else {
    // Smart fallback — no OpenAI key needed for demo
    const high = [
      `Excellent work with ${accuracy}% accuracy! Your articulation of the target sounds was very clear. Keep that natural pace — you're building strong motor memory.`,
      `Great job! That ${accuracy}% score shows real progress. The target sounds came through clearly. One more session like this and it becomes automatic.`,
    ];
    const mid = [
      `Good effort — ${accuracy}% is solid progress! Focus on the underlined words in the analysis above and try slowing down by 10%. Clarity before speed.`,
      `Nice attempt at ${accuracy}%! Try breaking the phrase into two halves and mastering each separately before combining. You're on the right track.`,
    ];
    const low = [
      `Keep at it! Speech therapy is a journey. Break this phrase into 2-word chunks and practice each slowly. Your brain is building new pathways with every attempt.`,
      `Don't give up — even short practice sessions matter. Try whispering the phrase first — it often helps the mouth find the right positions before full volume.`,
    ];
    const pool = accuracy >= 80 ? high : accuracy >= 60 ? mid : low;
    ai_feedback = pool[Math.floor(Math.random() * pool.length)];
  }

  return new Response(JSON.stringify({ ai_feedback }), {
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
