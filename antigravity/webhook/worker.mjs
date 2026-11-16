// Static Gemini webhook pilot. No Google API key or research content here.
const enc = new TextEncoder();
const experiments = new Set(["AG-INFRA-001","AG-PHOTONIC-001","AG-PHOTONIC-002","AG-PHOTONIC-003"]);
const response = status => new Response(null,{status});
export async function handle(request, env, now = Date.now()) {
  if (new URL(request.url).pathname !== "/gemini" || request.method !== "POST") return response(404);
  const id = request.headers.get("webhook-id"), ts = request.headers.get("webhook-timestamp");
  const sig = request.headers.get("webhook-signature") || "";
  if (!id || !/^\d{1,12}$/.test(ts || "") || Math.abs(now/1000-Number(ts)) > 300) return response(401);
  if (!env.WEBHOOK_SIGNING_SECRET?.startsWith("whsec_")) return response(503);
  const body = await request.text();
  if (enc.encode(body).length > 65536) return response(413);
  let event;
  try {
    const key = await crypto.subtle.importKey("raw",Uint8Array.from(atob(env.WEBHOOK_SIGNING_SECRET.slice(6)),c=>c.charCodeAt(0)),{name:"HMAC",hash:"SHA-256"},false,["verify"]);
    let valid = false;
    for (const part of sig.split(/\s+/)) {
      if (!part.startsWith("v1,")) continue;
      try { if (await crypto.subtle.verify("HMAC",key,Uint8Array.from(atob(part.slice(3)),c=>c.charCodeAt(0)),enc.encode(id+"."+ts+"."+body))) valid=true; } catch {}
    }
    if (!valid) return response(401);
    event=JSON.parse(body);
  } catch { return response(400); }
  if (event?.type !== "interaction.completed") return response(204);
  if (typeof event.data?.id !== "string" || !event.data.id || event.data.id.length>1024) return response(400);
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(event.data.id))),b=>b.toString(16).padStart(2,"0")).join("");
  let route;
  try { route=JSON.parse(env.AG_ROUTES || "{}")[hash]; } catch { return response(503); }
  if (!route) return response(204);
  if (!experiments.has(route.experiment) || !/^\d+$/.test(route.run || "") || env.CONFIRM_FREE_PROJECT !== "true" || !env.GITHUB_TOKEN) return response(503);
  // Durable Object serializes duplicate deliveries; no raw interaction ID is persisted.
  return env.DELIVERIES.get(env.DELIVERIES.idFromName(hash)).fetch("https://internal/dispatch",{method:"POST",body:JSON.stringify({hash,route})});
}
export class Delivery {
  constructor(state,env){this.state=state;this.env=env;}
  async fetch(request){
    return this.state.blockConcurrencyWhile(async()=>{
      if(await this.state.storage.get("sent")) return response(204);
      const {hash,route}=await request.json();
      const r=await fetch("https://api.github.com/repos/cryptomanxxx/debatt-ai-open-photonic-lab/actions/workflows/antigravity-manager.yml/dispatches",{method:"POST",headers:{Authorization:"Bearer "+this.env.GITHUB_TOKEN,"Content-Type":"application/json","User-Agent":"debatt-ai-antigravity-webhook","Accept":"application/vnd.github+json"},body:JSON.stringify({ref:"main",inputs:{experiment:route.experiment,mode:"retrieve",prior_run_id:route.run,expected_interaction_hash:hash,confirm_free_project:true,confirm_new_submission:false}})});
      if(!r.ok) return response(503);
      await this.state.storage.put("sent",true);
      return response(204);
    });
  }
}
export default {fetch(request,env){return handle(request,env);}};
