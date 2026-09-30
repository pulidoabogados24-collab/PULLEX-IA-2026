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
const S={perfil:null,convs:[],msgs:{},casos:{},intentos:[],sig:1};
function perfilBase(nombre,email){return {email:email||'demo@pullex.co',nombre:nombre||'Valentina Ríos',plan:'pro',
  plan_nombre:'Pro',limite:500,usadas:12,restantes:488,activo:true,es_admin:false,email_verificado:true,
  preferencias:{areas:['Constitucional / Tutela','Penal'],modo:'auto',tema:'oscuro',web:true,memoria:'',camino:'aprender'}}}
function json(d,st){return new Response(JSON.stringify(d),{status:st||200,headers:{'content-type':'application/json'}})}
function error(st,m){return json({detail:m},st)}
function gastar(){const p=S.perfil;p.usadas++;p.restantes=p.limite-p.usadas;return p.restantes}
function trozos(t,n){const r=[];for(let i=0;i<t.length;i+=n)r.push(t.slice(i,i+n));return r}
function publico(c){return {id:c.id,area:c.area,nivel:c.nivel,titulo:c.d.titulo,enunciado:c.d.enunciado,pregunta:c.d.pregunta,
  n_pistas:(c.d.pistas||[]).length,cambio:c.d.cambio||null,padre_id:c.padre||null}}
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
function sse(textos){
  const enc=new TextEncoder();
  return new Response(new ReadableStream({async start(c){
    c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'restantes',restantes:S.perfil.restantes})+'\n\n'));
    await esperar(500);
    for(const t of textos){c.enqueue(enc.encode('data: '+JSON.stringify({tipo:'texto',texto:t})+'\n\n'));await esperar(18)}
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
    hist.push({rol:'user',contenido:msj},{rol:'assistant',contenido:txt});conv.t=Date.now();
    gastar();return sse(trozos(txt,24));}
  if(ruta==='/api/modular/opciones')return json({areas:['Constitucional','Penal','Civil','Laboral','Administrativo','Comercial','Familia','Procesal','Probatorio'],
    niveles:[{id:'basico',nombre:'Básico'},{id:'intermedio',nombre:'Intermedio'},{id:'avanzado',nombre:'Avanzado'},{id:'experto',nombre:'Experto'}],
    rubrica:RUBRICA.map(([id,n,mx])=>({id,nombre:n,max:mx}))});
  if(ruta==='/api/modular/caso'){
    let c;
    if(b.variacion_de){const p=S.casos[b.variacion_de];if(!p)return error(404,'Caso no encontrado');
      c={id:S.sig++,area:p.area,nivel:p.nivel,d:D.casos[p.area].variacion,padre:p.id}}
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
    const ev=evaluar(r,c.d);S.intentos.push({area:c.area,total:ev.total,debiles:ev.conceptos_debiles});
    return json({...ev,restantes:gastar()});}
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
