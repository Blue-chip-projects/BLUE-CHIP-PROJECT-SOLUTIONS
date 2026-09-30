const clean=(v,max=180)=>String(v??"").trim().slice(0,max);
const emailOK=v=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);

export async function onRequestPost({request,env}){
  try{
    const type=request.headers.get("content-type")||"";
    const body=type.includes("application/json")
      ? await request.json()
      : Object.fromEntries((await request.formData()).entries());

    if(clean(body.website)) return json({ok:true},200);

    const lead={
      id:crypto.randomUUID(),
      createdAt:new Date().toISOString(),
      firstName:clean(body.firstName,80),
      lastName:clean(body.lastName,80),
      email:clean(body.email,180).toLowerCase(),
      company:clean(body.company,160),
      role:clean(body.role,120),
      region:clean(body.region,120),
      organisationType:clean(body.organisationType,80),
      teamSize:clean(body.teamSize,40),
      interest:clean(body.interest,100),
      message:clean(body.message,1500),
      consent:body.consent==="yes"
    };

    if(!lead.firstName||!lead.lastName||!lead.company||!lead.organisationType||!lead.interest||!lead.consent||!emailOK(lead.email)){
      return json({error:"Please complete the required fields and provide a valid work email."},400);
    }
    if(!env.JENASARO_LEADS){
      return json({error:"The signup service is not configured yet. Please try again shortly."},503);
    }

    await env.JENASARO_LEADS.put("lead:"+lead.createdAt+":"+lead.id,JSON.stringify(lead),{
      metadata:{company:lead.company,email:lead.email,interest:lead.interest}
    });
    return json({ok:true},201);
  }catch{
    return json({error:"Unable to submit your interest at the moment."},500);
  }
}
const json=(body,status)=>new Response(JSON.stringify(body),{status,headers:{"content-type":"application/json;charset=UTF-8","cache-control":"no-store"}});