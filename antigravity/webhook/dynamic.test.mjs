import {test} from "node:test";
import assert from "node:assert/strict";
import {observe} from "./dynamic.mjs";
test("Google-key signature observation only",async()=>{
 const pair=await crypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
 const jwk=await crypto.subtle.exportKey("jwk",pair.publicKey); jwk.kid="test";
 const b64=x=>Buffer.from(JSON.stringify(x)).toString("base64url");
 const data=b64({alg:"RS256",kid:"test"})+"."+b64({aud:"untrusted-project",exp:2000});
 const sig=Buffer.from(await crypto.subtle.sign("RSASSA-PKCS1-v1_5",pair.privateKey,new TextEncoder().encode(data))).toString("base64url");
 const req=token=>new Request("https://example.com/gemini-dynamic",{method:"POST",headers:{"webhook-signature":token},body:"untrusted body"});
 const keys=async url=>{assert.equal(url,"https://generativelanguage.googleapis.com/.well-known/jwks.json");return Response.json({keys:[jwk]});};
 assert.equal((await observe(req(data+"."+sig),1000000,keys)).status,204);
 assert.equal((await observe(req(data+"."+sig),3000000,keys)).status,401);
 assert.equal((await observe(req(data+".AAAA"),1000000,keys)).status,401);
 assert.equal((await observe(req(""),1000000,keys)).status,401);
 assert.equal((await observe(req(data+"."+sig),1000000,async()=>Response.json({keys:[]}))).status,401);
});
