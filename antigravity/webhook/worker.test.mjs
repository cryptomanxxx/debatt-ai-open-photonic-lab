import {test} from "node:test";
import assert from "node:assert/strict";
import {createHmac,createHash} from "node:crypto";
import {handle} from "./worker.mjs";
const now=1700000000000, ts=String(now/1000), secret=Buffer.alloc(32,7);
const hash=createHash("sha256").update("synthetic").digest("hex");
let calls=0;
const env={WEBHOOK_SIGNING_SECRET:"whsec_"+secret.toString("base64"),CONFIRM_FREE_PROJECT:"true",GITHUB_TOKEN:"fake",AG_ROUTES:JSON.stringify({[hash]:{experiment:"AG-PHOTONIC-003",run:"123"}}),DELIVERIES:{idFromName:x=>x,get:()=>({fetch:async()=>{calls++;return new Response(null,{status:204});}})}};
function req(type="interaction.completed",id="synthetic",timestamp=ts,invalid=false){
 const body=JSON.stringify({type,data:{id}});
 const sig=createHmac("sha256",secret).update("event."+timestamp+"."+body).digest("base64");
 return new Request("https://example.test/gemini",{method:"POST",body,headers:{"webhook-id":"event","webhook-timestamp":timestamp,"webhook-signature":"v1,"+(invalid?"AAAA":sig)}});
}
test("valid mapped completion only",async()=>{assert.equal((await handle(req(),env,now)).status,204);assert.equal(calls,1);});
test("invalid, stale, unmapped and other events do not dispatch",async()=>{const before=calls;assert.equal((await handle(req(undefined,undefined,ts,true),env,now)).status,401);assert.equal((await handle(req(undefined,undefined,String(Number(ts)-301)),env,now)).status,401);assert.equal((await handle(req(undefined,"unknown"),env,now)).status,204);assert.equal((await handle(req("interaction.failed"),env,now)).status,204);assert.equal(calls,before);});
test("billing confirmation required",async()=>{assert.equal((await handle(req(),{...env,CONFIRM_FREE_PROJECT:"false"},now)).status,503);});
