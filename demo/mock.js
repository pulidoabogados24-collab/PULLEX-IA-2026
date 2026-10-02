// =========================================================================================
// PULLEX IA — capa de demostración. Reemplaza fetch() por un servidor simulado en memoria para
// que la app completa funcione sin backend ni clave de IA. Solo se usa en la página de demo.
// =========================================================================================
(function(){
const D=window.__DEMO_DATOS__;
const esperar=ms=>new Promise(r=>setTimeout(r,ms));
const PLANES={prueba:{nombre:'Prueba gratis',limite:10,precio:0},basico:{nombre:'Básico',limite:200,precio:30000},
  pro:{nombre:'Pro',limite:500,precio:45000},premium:{nombre:'Premium',limite:1000,precio:60000}};
// Acceso por plan: misma tabla que app.py (PLAN_FUNCIONES). El perfil de la demo es Premium; el selector
// oculto ?plan=basico|pro|premium (o prueba) en la URL de la demo muestra los bloqueos de cada plan.
const FUNCIONES=['chat','academia','automatizador'];
const PLAN_FUNCIONES={prueba:FUNCIONES,basico:['chat'],pro:['chat','academia'],premium:FUNCIONES};
const PLAN_REQUERIDO={academia:'pro',automatizador:'premium'};
const PREFIJOS_FUNCION=[['/api/modular','academia'],['/api/academia','academia'],['/api/taller','academia'],
  ['/api/documentos','automatizador'],['/api/flujos','automatizador'],['/api/asistente','automatizador']];
const NOMBRE_FUNCION={academia:'Modular Lab y Mi mapa',automatizador:'Documentos, Flujos y Asistente'};
const PLAN_DEMO=(()=>{try{const p=new URLSearchParams(location.search).get('plan');return PLANES[p]?p:'premium'}catch(e){return 'premium'}})();
function funcionDeRuta(r){const f=PREFIJOS_FUNCION.find(([p])=>r===p||r.startsWith(p+'/'));return f?f[1]:null}
const AREAS=['Constitucional / Tutela','Penal','Civil','Familia','Laboral','Administrativo','Comercial / Societario',
  'Marcas / Propiedad Intelectual','Consumidor','Tributario'];
const RUBRICA=[['problema','Identificación del problema',20],['normas','Marco normativo',20],['argumentacion','Argumentación',20],
  ['aplicacion','Aplicación a los hechos',20],['conclusion','Conclusión',10],['claridad','Claridad jurídica',10]];
const S={perfil:null,convs:[],msgs:{},casos:{},intentos:[],sig:1,conoc:{},imgs:{}};
// Apariencia: misma lista blanca que app.py (las imágenes quedan solo en la memoria de esta página).
const AP_OPC={modo:['claro','oscuro','auto'],tema:['pullex','notario','bogota','caribe','toga','jardin'],
  fuente:['editorial','clasica','moderna'],tamano:['normal','grande'],densidad:['comoda','compacta'],radio:['recto','suave','redondo']};
const AP_TOPE={fondo:350*1024,avatar:120*1024,logo:120*1024};
function apBase(){return {modo:'claro',tema:'pullex',acento:null,fuente:'editorial',tamano:'normal',densidad:'comoda',radio:'suave',
  imagenes:{fondo:0,avatar:0,logo:0}}}
function apActualizar(actual,b){
  if(!b||typeof b!=='object'||Array.isArray(b))return 'Apariencia inválida.';
  const n={...actual,imagenes:{...actual.imagenes}};
  for(const k in AP_OPC){if(k in b){if(!AP_OPC[k].includes(b[k]))return 'Valor no permitido en apariencia: '+k+'.';n[k]=b[k]}}
  if('acento' in b){if(b.acento==null||b.acento==='')n.acento=null;
    else if(typeof b.acento==='string'&&/^#[0-9a-f]{6}$/i.test(b.acento))n.acento=b.acento.toLowerCase();
    else return 'El color de acento debe tener el formato #rrggbb.'}
  for(const t in AP_TOPE){if(!(t in b))continue;const v=b[t];
    if(v==null||v===''){delete S.imgs[t];n.imagenes[t]=0;continue}
    const m=typeof v==='string'&&v.match(/^data:(image\/jpeg|image\/png);base64,([A-Za-z0-9+/=]+)$/);
    if(!m)return 'La imagen debe ser JPG o PNG.';
    if(m[2].length*3/4>AP_TOPE[t])return 'La imagen pesa demasiado (máximo '+(AP_TOPE[t]/1024)+' KB).';
    S.imgs[t]={mime:m[1],b64:m[2]};n.imagenes[t]=Date.now()}
  return n}
function perfilBase(nombre,email){const pl=PLANES[PLAN_DEMO];const usadas=PLAN_DEMO==='prueba'?2:12;
  return {email:email||'demo@pullex.co',nombre:nombre||'Valentina Ríos',plan:PLAN_DEMO,
  plan_nombre:pl.nombre,limite:pl.limite,usadas,restantes:pl.limite-usadas,activo:true,es_admin:false,email_verificado:true,
  funciones:PLAN_FUNCIONES[PLAN_DEMO].slice(),
  preferencias:{areas:['Constitucional / Tutela','Penal'],modo:'auto',tema:'claro',web:true,memoria:'',camino:'aprender',apariencia:apBase()}}}
function json(d,st){return new Response(JSON.stringify(d),{status:st||200,headers:{'content-type':'application/json'}})}
function error(st,m){return json({detail:m},st)}
function gastar(){const p=S.perfil;p.usadas++;p.restantes=p.limite-p.usadas;return p.restantes}
function trozos(t,n){const r=[];for(let i=0;i<t.length;i+=n)r.push(t.slice(i,i+n));return r}
function publico(c){return {id:c.id,area:c.area,nivel:c.nivel,titulo:c.d.titulo,enunciado:c.d.enunciado,pregunta:c.d.pregunta,
  n_pistas:(c.d.pistas||[]).length,cambio:c.d.cambio||null,padre_id:c.padre||null,foco:c.foco?c.foco.nombre:null}}
// Evaluación simulada y genérica: cada caso de datos_demo.json trae sus `claves_evaluacion` (palabras clave por
// criterio de la rúbrica, aciertos, omisiones, normas y conceptos). La misma lógica está en servidor_simulado.py.
const sinTildes=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');
function evaluar(resp,caso){
  const r=sinTildes(resp);const k=(caso&&caso.claves_evaluacion)||{};
  const t=ks=>(ks||[]).some(x=>r.includes(sinTildes(x)));
  const grupos=k.rubrica_claves||{};const p={};
  RUBRICA.forEach(([id,,m])=>{
    if(id==='claridad'){p[id]=resp.length>250?9:7;return}
    const g=grupos[id]||[];const base=Math.round(m*0.4);
    p[id]=g.length?base+Math.round((m-1-base)*g.filter(t).length/g.length):base});
  const omit=(k.omisiones||[]).filter(o=>!t(o.si_falta)).map(o=>o.texto);
  const ident=(k.aciertos||[]).filter(a=>t(a.si_hay)).map(a=>a.texto);
  const rub=RUBRICA.map(([id,n,m])=>({id,nombre:n,max:m,puntaje:Math.min(m,p[id])}));
  return {total:rub.reduce((a,b)=>a+b.puntaje,0),puntajes:p,rubrica:rub,
    identificaste:ident.length?ident:[k.acierto_base||'Identificaste el tema general del caso.'],
    omitiste:omit.length?omit:['Nada importante: cubriste los puntos principales.'],
    norma_faltante:(k.normas_clave||[]).filter(n=>!t(n.si_falta)).map(n=>n.norma),
    contraargumento:k.contraargumento||'',como_mejorar:k.como_mejorar||[],
    conceptos_debiles:(k.conceptos_clave||[]).filter(c=>!t(c.si_falta)).map(c=>c.concepto),
    comentario:omit.length>1?(k.comentario_mejorar||'Vas bien encaminado.'):(k.comentario_bien||'Muy buena estructura.')};
}
function progreso(){
  const por={},deb={};S.intentos.forEach(i=>{(por[i.area]=por[i.area]||[]).push(i.total);
    i.debiles.forEach(c=>deb[c]=(deb[c]||0)+1)});
  const areas=Object.entries(por).map(([a,v])=>({area:a,intentos:v.length,promedio:Math.round(v.reduce((x,y)=>x+y,0)/v.length)}))
    .sort((a,b)=>a.promedio-b.promedio);
  const tot=S.intentos.map(i=>i.total);
  return {resueltos:tot.length,promedio:tot.length?Math.round(tot.reduce((x,y)=>x+y,0)/tot.length):null,por_area:areas,
    a_reforzar:Object.entries(deb).sort((a,b)=>b[1]-a[1]).map(x=>x[0]).slice(0,5),ultimos:tot.slice(-8)};
}
// ------------------------------------------------ Academia (misma lógica que academia.py) --
const DIA=86400,INTERVALOS={0:1,1:1,2:3,3:7,4:15,5:30};
const INDICE={};D.mapa.forEach(a=>a.temas.forEach(t=>t.conceptos.forEach(c=>{INDICE[c.id]={...c,area:a.area,tema:t.tema}})));
const norm=s=>sinTildes(s).replace(/[^a-z0-9]+/g,' ').trim();
function emparejar(texto,area){const t=' '+norm(texto)+' ';let mejor=null,largo=0;
  Object.values(INDICE).forEach(c=>{(c.kw.concat(c.area===area?c.kwa:[])).forEach(k=>{
    const pat=k.endsWith('*')?' '+k.slice(0,-1):' '+k+' ';const pun=k.length+(c.area===area?.5:0);
    if(t.includes(pat)&&pun>largo){mejor=c.id;largo=pun}})});return mejor}
const ahora=()=>Date.now()/1000;
function estadoDe(f){if(!f)return 'sin_evaluar';if(f.caja>=4)return 'dominado';if(f.fallos&&f.caja<=1)return 'debil';return 'en_progreso'}
function nivelRec(p){return p==null||p<55?'basico':p<75?'intermedio':p<88?'avanzado':'experto'}
function cuando(ts){const a=ahora();const d=ts>a?Math.floor((ts-a)/DIA)+1:0;return d<=0?'hoy':d===1?'mañana':'en '+d+' días'}
function severidad(f){return f.fallos>=3||(f.fallos>=2&&!f.aciertos)?'alta':f.fallos>=2||!f.aciertos?'media':'baja'}
function actualizar(cid,nombre,area,res){const t=ahora();
  let f=S.conoc[cid];if(!f)f=S.conoc[cid]={id:cid,nombre,area,aciertos:0,fallos:0,caja:0,proximo:t+DIA,primer_visto:t,ultimo_fallo:null,resuelto:null};
  if(res==='fallo'){f.fallos++;f.caja=1;f.proximo=t+DIA;f.ultimo_fallo=t;f.resuelto=null}
  else if(res==='acierto'){f.aciertos++;f.caja=Math.min(5,f.caja+1);f.proximo=t+INTERVALOS[f.caja]*DIA;
    if(f.caja>=4&&f.fallos&&!f.resuelto)f.resuelto=t}}
function registrar(area,conceptos,debiles,total,foco){
  const res=x=>{const id=emparejar(x,area);return id?[id,INDICE[id].nombre,INDICE[id].area]:null};
  const deb={},ev={};(debiles||[]).forEach(x=>{const r=res(x);if(r)deb[r[0]]=r});(conceptos||[]).forEach(x=>{const r=res(x);if(r)ev[r[0]]=r});
  if(foco&&INDICE[foco.id]&&!ev[foco.id])ev[foco.id]=[foco.id,INDICE[foco.id].nombre,INDICE[foco.id].area];
  const cambios=[];Object.values(deb).forEach(([id,n,a])=>{actualizar(id,n,a,'fallo');cambios.push({id,nombre:n,resultado:'fallo'})});
  Object.values(ev).forEach(([id,n,a])=>{if(deb[id])return;const r=total>=60?'acierto':'visto';actualizar(id,n,a,r);cambios.push({id,nombre:n,resultado:r})});
  return cambios}
function pub(f){return {id:f.id,nombre:f.nombre,area:f.area,estado:estadoDe(f),aciertos:f.aciertos,fallos:f.fallos,caja:f.caja,
  proximo:f.proximo,proximo_texto:cuando(f.proximo),tema:(INDICE[f.id]||{}).tema}}
function promedios(){const p={};S.intentos.forEach(i=>{(p[i.area]=p[i.area]||[]).push(i.total)});
  const r={};Object.entries(p).forEach(([a,v])=>r[a]=[v.reduce((x,y)=>x+y,0)/v.length,v.length]);return r}
function mapa(){const pr=promedios();const cuenta={dominado:0,en_progreso:0,debil:0,sin_evaluar:0};
  const areas=D.mapa.map(a=>{const res={dominado:0,en_progreso:0,debil:0,sin_evaluar:0};
    const temas=a.temas.map(t=>({tema:t.tema,conceptos:t.conceptos.map(c=>{const f=S.conoc[c.id];const e=estadoDe(f);res[e]++;
      return {id:c.id,nombre:c.nombre,desc:c.desc,estado:e,aciertos:f?f.aciertos:0,fallos:f?f.fallos:0,proximo_texto:f?cuando(f.proximo):null}})}));
    Object.keys(cuenta).forEach(k=>cuenta[k]+=res[k]);const p=pr[a.area];
    return {area:a.area,temas,resumen:res,practicable:true,promedio:p?Math.round(p[0]):null,intentos:p?p[1]:0,nivel_recomendado:nivelRec(p?p[0]:null)}});
  return {areas,resumen:cuenta,aviso:'Indicadores orientativos para tu estudio personal. No son una calificación académica.'}}
function errores(){return {errores:Object.values(S.conoc).filter(f=>f.fallos)
  .sort((x,y)=>(!!x.resuelto-!!y.resuelto)||(y.fallos-x.fallos)||((y.ultimo_fallo||0)-(x.ultimo_fallo||0)))
  .map(f=>({...pub(f),frecuencia:f.fallos,severidad:severidad(f),primer_visto:f.primer_visto,ultimo_fallo:f.ultimo_fallo,resuelto:f.resuelto}))}}
function resumen(){const t=ahora(),fin=t+DIA-((t-5*3600)%DIA);const pr=promedios();
  const filas=Object.values(S.conoc).sort((x,y)=>x.proximo-y.proximo);
  const est={dominado:0,en_progreso:0,debil:0};filas.forEach(f=>est[estadoDe(f)]++);
  est.sin_evaluar=Object.keys(INDICE).filter(id=>!S.conoc[id]).length;
  const hoy=filas.filter(f=>f.proximo<=fin).map(pub);const prox=filas.length?pub(filas[0]):null;
  const deb=filas.filter(f=>estadoDe(f)==='debil').sort((x,y)=>(y.fallos-x.fallos)||((y.ultimo_fallo||0)-(x.ultimo_fallo||0)));
  const td=deb.length?pub(deb[0]):null;const niv=a=>nivelRec(pr[a]?pr[a][0]:null);let rec;
  if(td)rec={area:td.area,concepto_id:td.id,concepto:td.nombre,nivel:niv(td.area),motivo:'Es el concepto que más has confundido.'};
  else if(prox)rec={area:prox.area,concepto_id:prox.id,concepto:prox.nombre,nivel:niv(prox.area),motivo:'Te toca repasarlo '+prox.proximo_texto+'.'};
  else rec={area:'Constitucional',concepto_id:null,concepto:null,nivel:'basico',motivo:'Aún no has practicado esta área.'};
  const intentados=new Set(S.intentos.map(i=>i.caso));
  const pend=Object.values(S.casos).filter(c=>!intentados.has(c.id)).sort((x,y)=>y.id-x.id)[0];
  const ult=S.intentos[S.intentos.length-1];
  return {estados:est,repasos_hoy:hoy.slice(0,6),n_repasos_hoy:hoy.length,proximo_repaso:prox,tema_debil:td,caso_recomendado:rec,
    continuar:pend?{caso_id:pend.id,titulo:pend.d.titulo,area:pend.area}:null,
    ultimo_modular:ult?{titulo:ult.titulo,area:ult.area,puntaje:ult.total,fecha:ult.t}:null}}
// Historial de ejemplo: una estudiante que ya lleva unas semanas practicando (datos ficticios de la demo).
(function sembrar(){const t=ahora();
  [['tutela-procedencia',2,0,3,5],['tutela-subsidiariedad',1,2,1,0],['tutela-inmediatez',3,1,4,12],['derecho-salud',3,0,4,9],
   ['legitima-defensa',0,2,1,0],['conducta',1,0,2,2],['tipicidad',3,0,4,11],['ira-intenso-dolor',0,1,1,1],
   ['primacia-realidad',2,1,3,6],['subordinacion',2,0,2,3],['elementos-contrato',1,0,1,1]].forEach(([id,a,f,caja,dias],i)=>{
    const c=INDICE[id];S.conoc[id]={id,nombre:c.nombre,area:c.area,aciertos:a,fallos:f,caja,proximo:t+dias*DIA-(dias?0:3600),
      primer_visto:t-20*DIA,ultimo_fallo:f?t-(i+1)*DIA:null,resuelto:caja>=4&&f?t-2*DIA:null}});
  [['Constitucional',64],['Penal',52],['Constitucional',78],['Laboral',81],['Penal',61]].forEach(([a,n],i)=>
    S.intentos.push({area:a,total:n,debiles:[],titulo:D.casos[a].caso.titulo,t:t-(5-i)*DIA,caso:-1-i}));
})();
// Dos fuentes de EJEMPLO para ver el bloque «Fuentes consultadas» en la demo (no son consultas reales).
const FUENTES_DEMO=[
  {origen:'web',titulo:'Relatoría de la Corte Constitucional (ejemplo de la demostración)',
   url:'https://www.corteconstitucional.gov.co/relatoria/',oficial:true,citado:true},
  {origen:'corpus',ref:'F1',titulo:'Ejemplo de demostración - guía sobre la acción de tutela',tipo:'doctrina',
   estado_vigencia:'PENDIENTE_VERIFICAR',ubicacion:'',fecha_archivo:'2026-01-15',url:null,citado:false}];
function sse(textos,fuentes){
  const enc=new TextEncoder();
  return new Response(new ReadableStream({async start(c){
    c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'restantes',restantes:S.perfil.restantes})+'\n\n'));
    await esperar(500);
    for(const t of textos){c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'texto',texto:t})+'\n\n'));await esperar(18)}
    c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'fuentes',fuentes:fuentes||[]})+'\n\n'));
    c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'fin'})+'\n\n'));c.close();
  }}),{headers:{'content-type':'text/event-stream'}});
}
// ------------------------------------- Automatizador: catálogo REAL incrustado (documentos.py) --
// Generación, flujos y asistente devuelven textos de EJEMPLO (demo/documentos_demo.json), rotulados.
const AU=D.automatizador||{catalogo:[],flujos:[],areas:[],para:[],demo:{documentos:{},pasos:{},plan:{pasos:[]}}};
const AU_IDX={};AU.catalogo.forEach(t=>{AU_IDX[t.id]=t});
const AU_S={docs:[],sig:1,planes:{}};
const auNorm=s=>sinTildes(s).replace(/[^a-z0-9ñ ]+/g,' ');
const auResumen=t=>({id:t.id,nombre:t.nombre,area:t.area,subarea:t.subarea,para_quien:t.para_quien,descripcion:t.descripcion,borrador_funcionario:t.borrador_funcionario});
function auPublico(t){const c=JSON.parse(JSON.stringify(t));delete c.claves;return c}
function auBuscar(q,area,para){const toks=auNorm(q).split(/\s+/).filter(x=>x.length>1);
  return AU.catalogo.filter(t=>(!area||t.area===area)&&(!para||t.para_quien.includes(para))&&
    (!toks.length||toks.every(k=>auNorm([t.nombre,t.descripcion,t.area,t.subarea,t.claves||''].join(' ')).includes(k))))}
function auValidar(def,v){const e={},l={};v=v&&typeof v==='object'?v:{};
  def.campos.forEach(c=>{const x=String(v[c.id]==null?'':v[c.id]).trim();
    if(!x){if(c.requerido)e[c.id]='Este dato es obligatorio.';return}
    if(x.length>c.max)e[c.id]='Máximo '+c.max+' caracteres.';
    else if(c.tipo==='select'&&!(c.opciones||[]).includes(x))e[c.id]='Elige una de las opciones.';
    else if(c.tipo==='fecha'&&!/^\d{4}-\d{2}-\d{2}$/.test(x))e[c.id]='Escribe una fecha válida (AAAA-MM-DD).';
    else l[c.id]=x});return [l,e]}
function auSeparar(texto){const i=texto.indexOf('<<<VERIFICAR>>>');const cuerpo=(i<0?texto:texto.slice(0,i)).trim();
  const items=[];(i<0?'':texto.slice(i+15)).split('\n').forEach(x=>{const s=x.replace(/^\s*(?:[-*•]|\d+[.)])\s*/,'').trim();if(s&&!items.includes(s))items.push(s)});
  (cuerpo.match(/\[\s*COMPLETAR\s*:\s*[^\]\n]{1,160}\]/gi)||[]).forEach(x=>{const s='Completar: '+x.replace(/^\[\s*COMPLETAR\s*:\s*/i,'').replace(/\]$/,'').trim();if(!items.includes(s))items.push(s)});
  return [cuerpo,items.slice(0,40)]}
function auTitulo(t,c){for(const k of ['contraparte','demandado','entidad','autoridad','deudor','empleador','sociedad','arrendatario','comprador','parte2','destinatario','solicitante'])
  if(c[k])return (t.nombre+' — '+String(c[k]).slice(0,60)).slice(0,120);return t.nombre}
function auAdvertencias(t){const a=(t.advertencias||[]).slice();if(t.borrador_funcionario)a.unshift(AU.aviso_funcionario);a.push(AU.aviso_general);return a}
function auTextoDoc(t){const d=AU.demo;if(d.documentos[t.id])return d.documentos[t.id];
  let x=d.generico.replace('{nombre}',t.nombre).replace('{secciones}',t.estructura.map((s,i)=>(i+1)+'. '+s).join('\n'));
  if(t.borrador_funcionario)x='**'+AU.borrador+'**\n\n'+x;return x}
function auGuardar(o){const ahora=Date.now()/1000;const d={id:AU_S.sig++,creado:ahora,actualizado:ahora,fuentes:[],...o};AU_S.docs.unshift(d);return d}
function auPub(d){const t=AU_IDX[d.tipo];return {...d,tipo_nombre:t?t.nombre:null,borrador_funcionario:!!(t&&t.borrador_funcionario)}}
function auPasosSSE(nombre,pasos,textoDe,guardar){
  const enc=new TextEncoder();const ev=o=>enc.encode('data: '+JSON.stringify(o)+'\n\n');
  return new Response(new ReadableStream({async start(c){
    c.enqueue(ev({tipo:'inicio',titulo:nombre,total:pasos.length,pasos:pasos.map(p=>p.titulo)}));const hechos=[];
    for(let n=1;n<=pasos.length;n++){c.enqueue(ev({tipo:'restantes',restantes:gastar()}));
      c.enqueue(ev({tipo:'paso',n,titulo:pasos[n-1].titulo}));await esperar(350);
      const txt=textoDe(n,pasos[n-1]);for(const t of trozos(txt,40)){c.enqueue(ev({tipo:'texto',n,texto:t}));await esperar(12)}
      hechos.push([pasos[n-1].titulo,txt]);c.enqueue(ev({tipo:'paso_fin',n}))}
    const cuerpo='# '+nombre+'\n\n'+hechos.map(([t,x],i)=>'## Paso '+(i+1)+'. '+t+'\n\n'+x).join('\n\n');
    const d=guardar(cuerpo);c.enqueue(ev({tipo:'documento',id:d.id,titulo:d.titulo,verificar:d.verificar}));
    c.enqueue(ev({tipo:'fin',completo:true,pasos_completados:hechos.length}));c.close()}}),{headers:{'content-type':'text/event-stream'}})}
async function automatizador(ruta,m,b,qs){
  if(ruta==='/api/documentos/catalogo'){const a=qs.get('area')||'',p=qs.get('para')||'';const ts=auBuscar((qs.get('q')||'').slice(0,120),a,p);
    return json({total:AU.catalogo.length,n:ts.length,para_quien:AU.para,
      areas:AU.areas.map(x=>({area:x,n:AU.catalogo.filter(t=>t.area===x).length})),tipos:ts.map(qs.get('detalle')?auPublico:auResumen)})}
  const rt=ruta.match(/^\/api\/documentos\/catalogo\/([a-z0-9_]+)$/);
  if(rt){const t=AU_IDX[rt[1]];return t?json(auPublico(t)):error(404,'Tipo de documento no encontrado')}
  if(ruta==='/api/documentos/generar'){const t=AU_IDX[b.tipo];if(!t)return error(404,'Tipo de documento no encontrado');
    const [c,e]=auValidar(t,b.campos);if(Object.keys(e).length)return json({detail:'Revisa los datos marcados del formulario.',errores:e},400);
    await esperar(1100);const [texto,verificar]=auSeparar(auTextoDoc(t));
    const d=auGuardar({tipo:t.id,titulo:auTitulo(t,c),origen:'documento',campos:c,texto,verificar,advertencias:auAdvertencias(t)});
    return json({...auPub(d),restantes:gastar()})}
  if(ruta==='/api/documentos/mis')return json({documentos:AU_S.docs.map(d=>{const p=auPub(d);return {id:p.id,tipo:p.tipo,titulo:p.titulo,origen:p.origen,creado:p.creado,actualizado:p.actualizado,tipo_nombre:p.tipo_nombre}})});
  const rd=ruta.match(/^\/api\/documentos\/(\d+)(\/docx)?$/);
  if(rd){const d=AU_S.docs.find(x=>x.id===+rd[1]);if(!d)return error(404,'Documento no encontrado');
    if(rd[2])return error(501,'La demostración no genera archivos Word.');
    if(m==='PUT'){const t=String(b.texto||'');if(!t.trim())return error(400,'El documento no puede quedar vacío');
      d.texto=t;d.actualizado=Date.now()/1000;AU_S.docs=[d,...AU_S.docs.filter(x=>x!==d)];return json(auPub(d))}
    if(m==='DELETE'){AU_S.docs=AU_S.docs.filter(x=>x!==d);return json({ok:true})}
    return json(auPub(d))}
  if(ruta==='/api/flujos')return json({flujos:AU.flujos,max_pasos:AU.max_pasos||6});
  if(ruta==='/api/flujos/ejecutar'){const f=AU.flujos.find(x=>x.id===b.flujo);if(!f)return error(404,'Flujo no encontrado');
    const [c,e]=auValidar(f,b.campos);if(Object.keys(e).length)return json({detail:'Revisa los datos marcados del formulario.',errores:e},400);
    if(S.perfil.restantes<f.n_pasos)return error(402,'Este trabajo usa '+f.n_pasos+' consultas (una por paso).');
    const textos=AU.demo.pasos[f.id]||[];
    return auPasosSSE(f.nombre,f.pasos,(n,p)=>textos[n-1]||AU.demo.paso_generico.replace('{titulo}',p.titulo),
      cuerpo=>{const [,v]=auSeparar(cuerpo);return auGuardar({tipo:'flujo:'+f.id,titulo:f.nombre,origen:'flujo',campos:c,texto:cuerpo,verificar:v,advertencias:[AU.aviso_general]})})}
  if(ruta==='/api/asistente/tarea'){const t=String(b.tarea||'').trim();
    if(t.length<15)return error(400,'Describe la tarea con un poco más de detalle (mínimo una frase completa).');
    await esperar(900);const id=AU_S.sig++;const plan=JSON.parse(JSON.stringify(AU.demo.plan));AU_S.planes[id]={tarea:t,plan,estado:'planificado'};
    return json({id,...plan,max_pasos:AU.max_pasos||6,restantes:gastar()})}
  if(ruta==='/api/asistente/ejecutar'){const pl=AU_S.planes[b.id];if(!pl)return error(404,'Tarea no encontrada');
    if(pl.estado!=='planificado')return error(409,'Este plan ya se ejecutó. Pide un plan nuevo para otra ejecución.');
    const pasos=Array.isArray(b.pasos)?b.pasos:pl.plan.pasos;
    if(!pasos.length||pasos.length>(AU.max_pasos||6))return error(400,'El plan debe tener entre 1 y 6 pasos.');
    if(pasos.some(p=>!String(p.titulo||'').trim()||!String(p.instruccion||'').trim()))return error(400,'Cada paso necesita un título y una instrucción.');
    pl.estado='ejecutado';
    return auPasosSSE(pl.plan.titulo,pasos,(n,p)=>AU.demo.paso_generico.replace('{titulo}',p.titulo),
      cuerpo=>{const [,v]=auSeparar(cuerpo);return auGuardar({tipo:'asistente',titulo:pl.plan.titulo,origen:'asistente',campos:{tarea:pl.tarea},texto:cuerpo,verificar:v,advertencias:[AU.aviso_general]})})}
  return null;
}
async function manejar(url,o){
  const partes=String(url).replace(/^https?:\/\/[^/]+/,'').split('?');const ruta=partes[0];
  const qs=new URLSearchParams(partes[1]||'');const m=(o&&o.method)||'GET';
  let b={};try{b=o&&o.body?JSON.parse(o.body):{}}catch(e){}
  await esperar(ruta.startsWith('/api/modular/caso')||ruta.startsWith('/api/modular/evaluar')?900:150);
  if(ruta==='/api/login'||ruta==='/api/registro'){
    S.perfil=perfilBase(b.nombre&&b.nombre.trim()||'Valentina Ríos',b.email||'demo@pullex.co');
    return json({token:'demo',perfil:S.perfil});}
  if(!S.perfil)return error(401,'No autenticado');
  const fn=funcionDeRuta(ruta);
  if(fn&&!S.perfil.funciones.includes(fn)){const req=PLAN_REQUERIDO[fn];
    return json({detail:NOMBRE_FUNCION[fn]+' está disponible desde el plan '+PLANES[req].nombre+'. Mejora tu plan para usarlo.',
      codigo:'plan_insuficiente',funcion:fn,plan_requerido:req},403)}
  if(ruta==='/api/estado')return json({perfil:S.perfil,api:true,planes:PLANES,areas:AREAS,corpus:false,
    funciones:S.perfil.funciones,plan_funciones:PLAN_FUNCIONES,plan_requerido:PLAN_REQUERIDO,
    contacto_planes:{correo:'Pulidoabogados24@gmail.com',medio_pago:'Nequi'}});
  if(ruta==='/api/boletin')return json({fecha:new Date().toISOString().slice(0,10),contenido:
    '## Boletín de demostración\n\nEn la app real, aquí aparece cada día un boletín con noticias jurídicas, jurisprudencia reciente y novedades normativas de Colombia, generado con búsqueda web en fuentes oficiales.\n\n_Esta página es una demostración: no muestra noticias reales._'});
  if(ruta==='/api/preferencias'){const p=S.perfil.preferencias;
    if('apariencia' in b){const a=apActualizar(p.apariencia||apBase(),b.apariencia);if(typeof a==='string')return error(400,a);
      p.apariencia=a;if(a.modo==='claro'||a.modo==='oscuro')p.tema=a.modo}
    if(b.tema==='claro'||b.tema==='oscuro'){p.tema=b.tema;p.apariencia={...(p.apariencia||apBase()),modo:b.tema}}
    const resto={...b};delete resto.apariencia;delete resto.tema;Object.assign(p,resto);
    return json({ok:true,preferencias:p})}
  const ri=ruta.match(/^\/api\/apariencia\/imagen\/(fondo|avatar|logo)$/);
  if(ri){const im=S.imgs[ri[1]];if(!im)return error(404,'Imagen no encontrada');
    const bin=atob(im.b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
    return new Response(new Blob([u],{type:im.mime}),{status:200,headers:{'content-type':im.mime}})}
  if(ruta==='/api/conversaciones'&&m==='POST'){const id=S.sig++;S.convs.unshift({id,titulo:'Nueva consulta',t:0});S.msgs[id]=[];return json({id,titulo:'Nueva consulta'})}
  if(ruta==='/api/conversaciones')return json(S.convs.filter(c=>(S.msgs[c.id]||[]).length)
    .sort((x,y)=>y.t-x.t).map(c=>({id:c.id,titulo:c.titulo,actualizada:c.t})));
  const rc=ruta.match(/^\/api\/conversaciones\/(\d+)(\/mensajes|\/titulo)?$/);
  if(rc){const conv=S.convs.find(c=>c.id===+rc[1]);if(!conv)return error(404,'Conversación no encontrada');
    if(rc[2]==='/mensajes')return json(S.msgs[conv.id]||[]);
    if(rc[2]==='/titulo'){const t=String(b.titulo||'').replace(/\s+/g,' ').trim().slice(0,80);
      if(!t)return error(400,'Escribe un título');conv.titulo=t;return json({ok:true,titulo:t})}
    if(m==='DELETE'){S.convs=S.convs.filter(c=>c!==conv);delete S.msgs[conv.id];return json({ok:true})}}
  if(ruta==='/api/chat'){
    const conv=S.convs.find(c=>c.id===+b.conversacion);if(!conv)return error(404,'Conversación no encontrada');
    const msj=String(b.mensaje||'').trim();const hist=S.msgs[conv.id]=S.msgs[conv.id]||[];
    if(!hist.length)conv.titulo=msj.slice(0,60)+(msj.length>60?'…':'');
    // Document Studio: el mensaje empieza con «SOLICITUD DE REDACCIÓN — …»
    const pl=msj.split('\n')[0];
    const txt=pl.startsWith('SOLICITUD DE REDACCIÓN')?(pl.includes('PETICIÓN')?D.chat.escrito_peticion:D.chat.escrito)
      :(D.chat[b.estilo]||D.chat.directo);
    const fu=pl.startsWith('SOLICITUD DE REDACCIÓN')?[]:FUENTES_DEMO;
    hist.push({rol:'user',contenido:msj},{rol:'assistant',contenido:txt,fuentes:fu});conv.t=Date.now();
    gastar();return sse(trozos(txt,24),fu);}
  if(ruta==='/api/modular/opciones')return json({areas:['Constitucional','Penal','Civil','Laboral','Administrativo','Comercial','Familia','Procesal','Probatorio'],
    niveles:[{id:'basico',nombre:'Básico'},{id:'intermedio',nombre:'Intermedio'},{id:'avanzado',nombre:'Avanzado'},{id:'experto',nombre:'Experto'}],
    rubrica:RUBRICA.map(([id,n,mx])=>({id,nombre:n,max:mx}))});
  const rcaso=ruta.match(/^\/api\/modular\/caso\/(\d+)$/);
  if(rcaso){const c=S.casos[+rcaso[1]];return c?json(publico(c)):error(404,'Caso no encontrado')}
  if(ruta==='/api/modular/conceptos'){const c=S.casos[qs.get('caso_id')];if(!c)return error(404,'Caso no encontrado');
    return json({conceptos:(c.d.conceptos||[]).slice(0,4)})}
  if(ruta==='/api/academia/mapa')return json(mapa());
  if(ruta==='/api/academia/errores')return json(errores());
  if(ruta==='/api/academia/resumen')return json(resumen());
  if(ruta==='/api/modular/caso'){
    let c;
    if(b.variacion_de){const p=S.casos[b.variacion_de];if(!p)return error(404,'Caso no encontrado');
      c={id:S.sig++,area:p.area,nivel:p.nivel,d:D.casos[p.area].variacion,padre:p.id,foco:p.foco}}
    else if(b.concepto_id){const f=INDICE[b.concepto_id];if(!f)return error(404,'Concepto no encontrado');
      const banco=D.casos[f.area];
      if(!banco)return error(503,'En esta demostración el banco de casos solo trae Constitucional, Penal y Laboral. En la app real se genera un caso nuevo centrado en «'+f.nombre+'».');
      c={id:S.sig++,area:f.area,nivel:b.nivel||'intermedio',d:banco.caso,padre:null,foco:{id:f.id,nombre:f.nombre}}}
    else{
      const banco=D.casos[b.area];
      if(!banco){const hay=Object.keys(D.casos);
        return error(503,'En esta demostración el banco de casos trae casos de Derecho '+hay.slice(0,-1).join(', ')+' y '+hay[hay.length-1]+
          '. Elige una de esas áreas para verlos; en la app real se genera un caso nuevo de cualquier área.')}
      c={id:S.sig++,area:b.area,nivel:b.nivel||'basico',d:banco.caso,padre:null}}
    S.casos[c.id]=c;return json({...publico(c),restantes:gastar()});}
  if(ruta==='/api/modular/pista'){const c=S.casos[b.caso_id];const n=b.n||0;const ps=c.d.pistas||[];
    if(n>=ps.length)return error(404,'No hay más pistas para este caso');return json({n,pista:ps[n],quedan:ps.length-n-1})}
  if(ruta==='/api/modular/evaluar'){const c=S.casos[b.caso_id];const r=(b.respuesta||'').trim();
    if(r.length<40)return error(400,'Escribe una respuesta más completa antes de evaluarla (mínimo unas líneas).');
    const ev=evaluar(r,c.d);S.intentos.push({area:c.area,total:ev.total,debiles:ev.conceptos_debiles,titulo:c.d.titulo,t:ahora(),caso:c.id});
    const conocimiento=registrar(c.area,c.d.conceptos,ev.conceptos_debiles,ev.total,c.foco);
    return json({...ev,conocimiento,restantes:gastar()});}
  if(ruta==='/api/modular/solucion'){const c=S.casos[qs.get('caso_id')];const s=c.d.solucion;
    return json({...s,conceptos:c.d.conceptos||[]})}
  if(ruta==='/api/modular/progreso')return json(progreso());
  const rau=await automatizador(ruta,m,b,qs);if(rau)return rau;
  if(ruta==='/api/cambiar-clave')return json({ok:true,token:'demo'});
  if(['/api/cerrar-sesiones','/api/reenviar-verificacion','/api/recuperar-clave'].includes(ruta))
    return json({ok:true,mensaje:'En la demostración no se envían correos.'});
  return error(404,'Esta función no está disponible en la demostración.');
}
const original=window.fetch.bind(window);
window.fetch=(url,o)=>{const s=String(url);
  if(/^(https?:\/\/[^/]+)?\/api\//.test(s))return manejar(s,o);
  return original(url,o)};
})();
