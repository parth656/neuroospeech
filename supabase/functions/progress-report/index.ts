// supabase/functions/progress-report/index.ts
// Deploy: supabase functions deploy progress-report

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const authHeader = req.headers.get("Authorization");
  if (!authHeader) return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: cors });

  // Verify user
  const sbUser = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: authHeader } },
  });
  const { data: { user }, error } = await sbUser.auth.getUser();
  if (error || !user) return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: cors });

  // Use service role to read data
  const sbAdmin = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

  const since = new Date();
  since.setDate(since.getDate() - 7);

  const [{ data: sessions }, { data: profile }, { data: streak }] = await Promise.all([
    sbAdmin.from("sessions").select("module, accuracy, created_at").eq("user_id", user.id).gte("created_at", since.toISOString()),
    sbAdmin.from("profiles").select("full_name, total_sessions").eq("id", user.id).single(),
    sbAdmin.from("streaks").select("current_streak, longest_streak").eq("user_id", user.id).single(),
  ]);

  const name = profile?.full_name?.split(" ")[0] || "there";
  const count = sessions?.length ?? 0;

  if (count === 0) {
    return new Response(JSON.stringify({
      report: `Hi ${name}! No sessions this week yet. Even 5 minutes of daily practice builds powerful habits — start your session now! 🎯`,
      stats: { sessions: 0, avg_accuracy: 0, streak: streak?.current_streak ?? 0 }
    }), { headers: { ...cors, "Content-Type": "application/json" } });
  }

  const avgAcc = sessions!.reduce((a, s) => a + s.accuracy, 0) / count;

  // Find best module
  const modMap: Record<string, number[]> = {};
  for (const s of sessions!) {
    if (!modMap[s.module]) modMap[s.module] = [];
    modMap[s.module].push(s.accuracy);
  }
  const bestModule = Object.entries(modMap)
    .sort((a, b) => b[1].reduce((x,y)=>x+y,0)/b[1].length - a[1].reduce((x,y)=>x+y,0)/a[1].length)[0]?.[0] ?? "";

  const openAiKey = Deno.env.get("OPENAI_API_KEY");
  let report: string;

  if (openAiKey) {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Authorization": `Bearer ${openAiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [{
          role: "user",
          content: `Speech therapist writing a weekly report for ${name}. Sessions: ${count}, Avg accuracy: ${avgAcc.toFixed(1)}%, Best module: ${bestModule}, Streak: ${streak?.current_streak ?? 0} days. Write 2 warm, encouraging sentences celebrating progress and suggesting one focus for next week.`
        }],
        max_tokens: 120,
      }),
    });
    const d = await res.json();
    report = d.choices[0].message.content.trim();
  } else {
    report = `Great week, ${name}! You completed ${count} sessions with ${avgAcc.toFixed(1)}% average accuracy — your best work was in ${bestModule.split(" ").slice(1).join(" ") || bestModule}. Next week, aim for one extra session per day to push that streak even higher!`;
  }

  return new Response(JSON.stringify({
    report,
    stats: { sessions: count, avg_accuracy: Math.round(avgAcc * 10) / 10, streak: streak?.current_streak ?? 0, best_module: bestModule },
  }), { headers: { ...cors, "Content-Type": "application/json" } });
});
