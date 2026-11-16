// Observation only: a Google signature is not authorization to dispatch.
const JWKS = "https://generativelanguage.googleapis.com/.well-known/jwks.json";
const enc = new TextEncoder();
const reply = status => new Response(null,{status});
function decode(s) {
  if (!/^[A-Za-z0-9_-]+$/.test(s)) throw Error("encoding");
  return Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/")),c=>c.charCodeAt(0));
}
function json(s) { return JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(decode(s))); }
export async function observe(request, now=Date.now(), fetchKeys=fetch) {
  const token=request.headers.get("webhook-signature") || "";
  if (token.length>8192) return reply(401);
  const parts=token.split(".");
  if(parts.length!==3) return reply(401);
  let header, claims, signature;
  try {
    header=json(parts[0]); claims=json(parts[1]); signature=decode(parts[2]);
    if(header.alg!=="RS256" || typeof header.kid!=="string" || !header.kid || header.kid.length>256 || header.crit!==undefined || !claims || typeof claims!=="object" || Array.isArray(claims)) return reply(401);
  } catch { return reply(401); }
  let keys;
  try {
    const r=await fetchKeys(JWKS,{redirect:"error",signal:AbortSignal.timeout(4000)});
    if(!r.ok) return reply(503);
    const raw=await r.text();
    if(raw.length>131072) return reply(503);
    keys=JSON.parse(raw).keys;
    if(!Array.isArray(keys)) return reply(503);
  } catch { return reply(503); }
  try {
    const matches=keys.filter(k=>k.kid===header.kid && k.kty==="RSA" && (!k.alg || k.alg==="RS256") && (!k.use || k.use==="sig"));
    if(matches.length!==1) return reply(401);
    const key=await crypto.subtle.importKey("jwk",matches[0],{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
    if(!await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,signature,enc.encode(parts[0]+"."+parts[1]))) return reply(401);
    const t=now/1000;
    if(claims.exp!==undefined && (!Number.isFinite(claims.exp)||claims.exp<=t)) return reply(401);
    if(claims.nbf!==undefined && (!Number.isFinite(claims.nbf)||claims.nbf>t)) return reply(401);
    // Do not read or trust HTTP body. No audience/issuer values, IDs or token logged.
    console.log(JSON.stringify({event:"dynamic_google_signature_observed",has_audience:typeof claims.aud==="string"||Array.isArray(claims.aud),has_expiry:Number.isFinite(claims.exp),has_issuer:typeof claims.iss==="string"}));
    return reply(204);
  } catch { return reply(401); }
}
