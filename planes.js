// =========================================================================================
// PULLEX — acceso por plan (docs/15-PLANES-Y-PROVEEDORES.md). Se carga después de app.js y usa sus
// utilidades globales (ESTADO, PERFIL, $, el, ver, toast). Sin JavaScript en línea: los botones usan
// addEventListener y los datos del servidor se pintan con textContent.
//   Básico  = Consultar.
//   Pro     = Consultar + Academia (Laboratorio de casos, Mi mapa y el Taller de escritos).
//   Premium = todo: + Automatizador (Documentos, Flujos y Asistente).
//   Prueba  = todo, limitado por sus consultas gratis. Administrador = todo.
// El servidor es quien decide (403 «plan_insuficiente»); esto solo evita que el usuario choque con él.
// =========================================================================================
const VISTA_FUNCION={modular:'academia',mapa:'academia',taller:'academia',documentos:'automatizador',perfiles:'automatizador'};
const FUNCIONES_TODAS=['chat','academia','automatizador'];
const FUNCION_INFO={
  chat:{corto:'Consultar',d:'Chat jurídico con fuentes, adjuntos y búsqueda en sitios oficiales.'},
  academia:{corto:'Laboratorio de casos y Mi mapa',d:'Casos tipo examen con rúbrica, mapa del Derecho, banco de errores y repasos.',
    eyebrow:'PULLEX Academia',titulo:'Entrena como en el examen, con un tutor que recuerda tus errores',
    lead:'Laboratorio de casos y Mi mapa del Derecho están en el plan Pro. Resuelves casos tipo examen, PULLEX te evalúa con rúbrica y tu mapa personal te dice qué repasar y cuándo.',
    beneficios:['Casos tipo examen en 9 áreas, con pistas y solución de referencia',
      'Evaluación con rúbrica: lo que identificaste, lo que omitiste y cómo mejorar',
      'Mi mapa del Derecho: 61 conceptos con tu estado en cada uno',
      'Banco de errores y repasos espaciados a 1, 3, 7, 15 y 30 días']},
  automatizador:{corto:'Documentos y flujos',d:'Escritos de 15 áreas, flujos de varios pasos y asistente; exporta a Word.',
    eyebrow:'Automatizador',titulo:'Del caso al borrador, sin empezar desde la hoja en blanco',
    lead:'Documentos, Flujos y Asistente están en el plan Premium. Completas un formulario y PULLEX arma el borrador con la estructura procesal colombiana, listo para que lo revises.',
    beneficios:['203 tipos de escritos: tutelas, peticiones, demandas, recursos, contratos y más',
      '7 flujos de varios pasos: investigar, analizar y redactar en orden',
      'Un asistente que propone un plan editable y lo ejecuta paso a paso',
      'Exporta a Word y guarda todo en «Mis documentos»']},
};
const PLANES_PAGOS=['basico','pro','premium'];

function plFunciones(){
  if(typeof ESTADO!=='undefined'&&ESTADO&&Array.isArray(ESTADO.funciones))return ESTADO.funciones;
  if(typeof PERFIL!=='undefined'&&PERFIL&&Array.isArray(PERFIL.funciones))return PERFIL.funciones;
  return FUNCIONES_TODAS; // sin datos no se bloquea nada: el servidor decide igual
}
function tieneFuncion(f){return !f||plFunciones().includes(f)}
function vistaBloqueada(v){return !tieneFuncion(VISTA_FUNCION[v])}
function plPlanes(){return (ESTADO&&ESTADO.planes)||{}}
function plIncluye(plan){const m=ESTADO&&ESTADO.plan_funciones;return (m&&m[plan])||(plan==='premium'?FUNCIONES_TODAS:plan==='pro'?['chat','academia']:['chat'])}
function plRequerido(f){return (ESTADO&&ESTADO.plan_requerido&&ESTADO.plan_requerido[f])||(f==='automatizador'?'premium':'pro')}
function plNombre(plan){const p=plPlanes()[plan];return p?p.nombre:plan}
function plPrecio(plan){const p=plPlanes()[plan];return p?'$'+Number(p.precio||0).toLocaleString('es-CO'):''}
function plIcono(id,cls){const s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('class','i '+(cls||'xs'));
  s.setAttribute('aria-hidden','true');const u=document.createElementNS('http://www.w3.org/2000/svg','use');u.setAttribute('href','#i-'+id);
  s.appendChild(u);return s}

// Flujo de pago que ya existe: pagar por Nequi y escribirle al administrador, que activa el plan en /admin.
// El botón abre ese correo ya escrito (asunto y cuerpo con el plan y el correo de la cuenta).
function plEnlacePago(plan){
  const c=(ESTADO&&ESTADO.contacto_planes)||{};const correo=c.correo||'';
  const p=plPlanes()[plan]||{};
  const asunto='Quiero mejorar mi plan de PULLEX a '+(p.nombre||plan);
  const cuerpo='Hola. Quiero pasar al plan '+(p.nombre||plan)+' ('+plPrecio(plan)+' al mes).\n\n'+
    'Correo de mi cuenta: '+((PERFIL&&PERFIL.email)||'')+'\n'+
    'Pago por '+(c.medio_pago||'Nequi')+': adjunto el comprobante (o te escribo cuando lo haga).\n\nGracias.';
  return 'mailto:'+correo+'?subject='+encodeURIComponent(asunto)+'&body='+encodeURIComponent(cuerpo);
}
function plBotonPago(plan,cls,texto){
  const a=el('a',cls,texto||('Mejorar a '+plNombre(plan)));a.href=plEnlacePago(plan);a.dataset.plan=plan;
  a.addEventListener('click',()=>setTimeout(()=>toast('Te abrimos el correo para activar '+plNombre(plan)+'. Si no se abre, escríbenos a '+
    (((ESTADO&&ESTADO.contacto_planes)||{}).correo||'soporte')+'.'),300));
  return a}

// ---- navegación: candado sutil en lo que el plan no incluye ----
function pintarCandados(){
  Object.keys(VISTA_FUNCION).forEach(v=>{const b=$('n-'+v);if(!b)return;
    const bloq=vistaBloqueada(v);b.classList.toggle('bloq',bloq);
    let c=b.querySelector('.nav-candado');
    if(bloq&&!c){c=plIcono('candado','nav-candado');b.appendChild(c)}
    if(!bloq&&c)c.remove();
    const txt=(b.querySelector('.l-largo')||b).textContent.trim();
    if(bloq){b.title=txt+' · incluido en el plan '+plNombre(plRequerido(VISTA_FUNCION[v]));
      b.setAttribute('aria-label',b.title)}
    else{b.removeAttribute('title');b.removeAttribute('aria-label')}
  });
}

// ---- pantalla de mejora de plan ----
function pintarMejora(f){
  const info=FUNCION_INFO[f]||FUNCION_INFO.academia;const req=plRequerido(f);
  const raiz=$('mejora-raiz');raiz.textContent='';
  const cab=el('div','mejora-cab');
  const eb=el('p','eyebrow');eb.appendChild(plIcono('candado'));eb.appendChild(document.createTextNode(info.eyebrow+' · plan '+plNombre(req)));
  cab.appendChild(eb);cab.appendChild(el('h2','display',info.titulo));cab.appendChild(el('p',null,info.lead));
  raiz.appendChild(cab);
  const ben=el('ul','mejora-ben');
  info.beneficios.forEach(t=>{const li=el('li');const ok=el('span','mb-ok');ok.appendChild(plIcono('check'));li.appendChild(ok);
    li.appendChild(el('span',null,t));ben.appendChild(li)});
  raiz.appendChild(ben);
  // Planes que incluyen la función, del más económico al más completo.
  const cards=el('div','planes-cards');
  const pagos=PLANES_PAGOS.filter(p=>plPlanes()[p]&&plIncluye(p).includes(f))
    .sort((a,b)=>plPlanes()[a].precio-plPlanes()[b].precio);
  pagos.forEach(p=>{
    const c=el('div','plan-card'+(p===req?' rec':''));c.dataset.plan=p;
    if(p===req)c.appendChild(el('span','pc-sello','Recomendado'));
    c.appendChild(el('div','pc-nombre',plNombre(p)));
    const pr=el('div','pc-precio',plPrecio(p));pr.appendChild(el('small',null,'COP / mes'));c.appendChild(pr);
    c.appendChild(el('div','pc-sub',Number(plPlanes()[p].limite).toLocaleString('es-CO')+' consultas al mes'));
    const ul=el('ul');
    FUNCIONES_TODAS.forEach(x=>{const si=plIncluye(p).includes(x);const li=el('li',si?null:'no');
      li.appendChild(plIcono(si?'check':'x'));li.appendChild(el('span',null,(si?'':'Sin ')+FUNCION_INFO[x].corto));ul.appendChild(li)});
    c.appendChild(ul);
    c.appendChild(plBotonPago(p,(p===req?'bpri':'bsec')+' pc-cta'));
    cards.appendChild(c)});
  raiz.appendChild(cards);
  const como=el('div','panel');
  como.appendChild(el('h3',null,'Cómo mejorar tu plan'));
  const pasos=el('ol','mejora-pasos');
  ['Paga el valor del plan por '+((((ESTADO&&ESTADO.contacto_planes)||{}).medio_pago)||'Nequi')+'.',
   'Pulsa «Mejorar»: se abre un correo ya escrito con tu plan y el correo de tu cuenta. Adjunta el comprobante.',
   'El administrador activa tu plan. Al volver a entrar verás todo desbloqueado; tus consultas y tu historial se conservan.']
    .forEach(t=>pasos.appendChild(el('li',null,t)));
  como.appendChild(pasos);
  const pie=el('div','mejora-pie');
  const act=el('div','actual');act.appendChild(document.createTextNode('Tu plan actual: '));
  act.appendChild(el('b',null,(PERFIL&&PERFIL.plan_nombre)||''));
  if(PERFIL)act.appendChild(document.createTextNode(' · te quedan '+PERFIL.restantes+' consultas'));
  pie.appendChild(act);
  const seguir=el('button','bsec','Seguir en Consultar');seguir.type='button';seguir.addEventListener('click',()=>ver('chat'));
  pie.appendChild(seguir);como.appendChild(pie);
  raiz.appendChild(como);
}

// ---- tabla comparativa de planes (Ajustes) ----
function pintarTablaPlanes(){
  const c=$('planes');if(!c)return;c.textContent='';
  const pl=plPlanes();const cols=PLANES_PAGOS.filter(k=>pl[k]);if(!cols.length)return;
  const actual=PERFIL&&PERFIL.plan;
  const t=el('table','planes-tabla');
  t.appendChild(el('caption',null,'Comparación de planes'));
  const th=el('thead');const trh=el('tr');trh.appendChild(el('th',null,''));
  cols.forEach(k=>{const h=el('th',k===actual?'actual':null);h.scope='col';
    if(k===actual)h.appendChild(el('span','pt-tu','Tu plan'));
    h.appendChild(el('span','pt-nombre',pl[k].nombre));const pr=el('span','pt-precio',plPrecio(k));
    pr.appendChild(el('span','pt-mes','/mes'));h.appendChild(pr);trh.appendChild(h)});
  th.appendChild(trh);t.appendChild(th);
  const tb=el('tbody');
  const fila=(titulo,desc,celda)=>{const tr=el('tr');const h=el('th');h.scope='row';h.appendChild(el('span','pt-f',titulo));
    if(desc)h.appendChild(el('span','pt-d',desc));tr.appendChild(h);
    cols.forEach(k=>{const td=el('td',k===actual?'actual':null);celda(k,td);tr.appendChild(td)});tb.appendChild(tr)};
  fila('Consultas al mes',null,(k,td)=>{td.textContent=Number(pl[k].limite).toLocaleString('es-CO')});
  FUNCIONES_TODAS.forEach(f=>fila(FUNCION_INFO[f].corto,FUNCION_INFO[f].d,(k,td)=>{
    const si=plIncluye(k).includes(f);td.className=(td.className?td.className+' ':'')+(si?'si':'no');
    if(si)td.appendChild(plIcono('check','s'));else td.appendChild(document.createTextNode('—'));
    td.appendChild(el('span','sr',si?'Incluido':'No incluido'))}));
  t.appendChild(tb);
  // Botones de mejora solo hacia planes superiores al actual (por precio).
  const precioActual=(pl[actual]||{}).precio||0;const esPrueba=actual==='prueba';
  if(!(PERFIL&&PERFIL.es_admin)){
    const tf=el('tfoot');const tr=el('tr');tr.appendChild(el('td'));
    cols.forEach(k=>{const td=el('td',k===actual?'actual':null);
      if(k!==actual&&(esPrueba||pl[k].precio>precioActual))td.appendChild(plBotonPago(k,(k==='premium'?'bpri':'bsec')+' pt-cta','Mejorar'));
      tr.appendChild(td)});
    tf.appendChild(tr);t.appendChild(tf)}
  c.appendChild(t);
  if(esPrueba)c.appendChild(el('p','planes-nota','Estás en la prueba gratis: tienes acceso a todo hasta agotar tus '+
    ((pl.prueba||{}).limite||10)+' consultas. Después eliges el plan que mejor te sirva.'));
}

// ---- el servidor dijo «plan insuficiente» (p. ej. el administrador cambió el plan con la app abierta) ----
function planInsuficiente(d){
  if(!d||d.codigo!=='plan_insuficiente')return false;
  if(ESTADO&&Array.isArray(ESTADO.funciones))ESTADO.funciones=ESTADO.funciones.filter(x=>x!==d.funcion);
  if(PERFIL&&Array.isArray(PERFIL.funciones))PERFIL.funciones=PERFIL.funciones.filter(x=>x!==d.funcion);
  pintarCandados();
  const v=Object.keys(VISTA_FUNCION).find(x=>VISTA_FUNCION[x]===d.funcion);
  if(v)ver(v);
  return true;
}
