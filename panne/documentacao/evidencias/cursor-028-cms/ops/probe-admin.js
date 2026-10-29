const fs=require("fs");const path=require("path");
const jwt=require("c:/Projetos/leaction-platform/services/gateway-api/node_modules/jsonwebtoken");
const env=fs.readFileSync("c:/Projetos/leaction-platform/.env","utf8");
const secret=env.split(/\r?\n/).find(l=>l.startsWith("JWT_SECRET=")).slice(11).trim().replace(/^"|"$/g,"");
const token=jwt.sign({sub:"probe",email:"admin@actionhub.com.br"},secret,{expiresIn:"10m"});
fetch("http://127.0.0.1:4001/api/admin/cms?config_key=panne-demo",{headers:{Authorization:"Bearer "+token}})
  .then(async r=>{console.log("admin_cms_status",r.status); const t=await r.text(); console.log(t.slice(0,200));})
  .catch(e=>{console.error("admin_cms_err",e.message); process.exit(1);});
