// =========================================================================================
// PULLEX IA — capa de demostración. Reemplaza fetch() por un servidor simulado en memoria para
// que la app completa funcione sin backend ni clave de IA. Solo se usa en la página de demo.
// =========================================================================================
(function(){
const D=window.__DEMO_DATOS__;
const esperar=ms=>new Promise(r=>setTimeout(r,ms));
const PLANES={prueba:{nombre:'Prueba gratis',limite:10,precio:0},basico:{nombre:'Básico',limite:200,precio:30000},
  pro:{nombre:'Pro',limite:500,precio:45000},premium:{nombre:'Premium',limite:1000,precio:60000}};
const AREAS=['Constitucional / Tutela','Penal','Civil','Familia','Laboral','Administrativo','Comercial / Societario',
  'Marcas / Propiedad Intelectual','Consumidor','Tributario'];
const RUBRICA=[['problema','Identificación del problema',20],['normas','Marco normativo',20],['argumentacion','Argumentación',20],
  ['aplicacion','Aplicación a los hechos',20],['conclusion','Conclusión',10],['claridad','Claridad jurídica',10]];
const S={perfil:null,convs:[],msgs:{},casos:{},intentos:[],sig:1,conoc:{}};
function perfilBase(nombre,email){return {email:email||'demo@pullex.co',nombre:nombre||'Valentina Ríos',plan:'pro',
  plan_nombre:'Pro',limite:500,usadas:12,restantes:488,activo:true,es_admin:false,email_verificado:true,
  preferencias:{areas:['Constitucional / Tutela','Penal'],modo:'auto',tema:'oscuro',web:true,memoria:'',camino:'aprender'}}}
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
async function manejar(url,o){
  const partes=String(url).replace(/^https?:\/\/[^/]+/,'').split('?');const ruta=partes[0];
  const qs=new URLSearchParams(partes[1]||'');const m=(o&&o.method)||'GET';
  let b={};try{b=o&&o.body?JSON.parse(o.body):{}}catch(e){}
  await esperar(ruta.startsWith('/api/modular/caso')||ruta.startsWith('/api/modular/evaluar')?900:150);
  if(ruta==='/api/login'||ruta==='/api/registro'){
    S.perfil=perfilBase(b.nombre&&b.nombre.trim()||'Valentina Ríos',b.email||'demo@pullex.co');
    return json({token:'demo',perfil:S.perfil});}
  if(!S.perfil)return error(401,'No autenticado');
  if(ruta==='/api/estado')return json({perfil:S.perfil,api:true,planes:PLANES,areas:AREAS,corpus:false});
  if(ruta==='/api/boletin')return json({fecha:new Date().toISOString().slice(0,10),contenido:
    '## Boletín de demostración\n\nEn la app real, aquí aparece cada día un boletín con noticias jurídicas, jurisprudencia reciente y novedades normativas de Colombia, generado con búsqueda web en fuentes oficiales.\n\n_Esta página es una demostración: no muestra noticias reales._'});
  if(ruta==='/api/preferencias'){Object.assign(S.perfil.preferencias,b);return json({ok:true,preferencias:S.perfil.preferencias})}
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
