// =========================================================================================
// PULLEX Perfiles — registro navegable de los 1.000 perfiles y el coordinador que elige unos pocos.
// Se abre desde Ajustes (no tiene botón propio en la barra: en celular ya hay seis). Se carga después de
// app.js y usa sus utilidades globales (auth, md, toast, PERFIL, ver).
// Sin JavaScript en línea: todo con addEventListener. Los datos del servidor se pintan con textContent;
// solo el resultado en Markdown de un perfil pasa por md() (marked + DOMPurify).
// =========================================================================================
const PER={listo:false,tab:'registro',meta:null,f:{q:'',area:'',sub:'',funcion:'',estado:'',pagina:1},turno:0,busq:null,
  sel:[],contexto:{},plan:null,ocupado:false};
const PER_TABS=[['registro','Registro'],['coordinador','Coordinador'],['ejecuciones','Mis ejecuciones']];
const PER_ESTADO={DEFINIDO:'Definido',CONECTADO_A_HERRAMIENTAS:'Conectado a herramientas',EJECUTADO:'Ejecutado',EVALUADO:'Evaluado',APROBADO:'Aprobado'};
const PER_EJEC={completada:'Completada',completada_con_observaciones:'Completada con observaciones',parcial:'Parcial',fallida:'Fallida'};
const PER_PASO={ejecutado:'Ejecutado',error:'Falló',omitido:'No se ejecutó'};

// ------------------------------------------------------------------------- utilidades --
function pE(tag,attrs,...hijos){const e=document.createElement(tag);
  if(attrs)for(const [k,v] of Object.entries(attrs)){if(v==null||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;else if(k==='on')Object.entries(v).forEach(([ev,fn])=>e.addEventListener(ev,fn));
    else e.setAttribute(k,v===true?'':v)}
  hijos.flat(Infinity).forEach(h=>{if(h==null||h===false)return;e.appendChild(typeof h==='string'?document.createTextNode(h):h)});
  return e}
function pBtn(txt,cls,fn,attrs){return pE('button',{type:'button',class:'per-btn'+(cls?' '+cls:''),on:{click:fn},...(attrs||{})},txt)}
function pId(id){return document.getElementById(id)}
function pLista(items,cls){return pE('ul',{class:'per-lista'+(cls?' '+cls:'')},(items||[]).map(x=>pE('li',{text:x})))}
function pBloque(titulo,...hijos){return pE('section',{class:'per-sec'},pE('h4',{text:titulo}),...hijos)}
function pEstado(id){return pE('span',{class:'per-est e-'+String(id).toLowerCase(),text:PER_ESTADO[id]||id})}
function pFecha(ts){try{return new Date(ts*1000).toLocaleString('es-CO',{dateStyle:'medium',timeStyle:'short'})}catch(e){return ''}}
function pSubir(){const m=document.querySelector('main');if(m)m.scrollTop=0}
function pRestantes(n){if(typeof n!=='number'||!PERFIL)return;PERFIL.restantes=n;PERFIL.usadas=PERFIL.limite-n;
  const c=pId('c-rest');if(c)c.textContent=n;const u=pId('cf-uso');if(u)u.textContent=PERFIL.usadas+' / '+PERFIL.limite}
async function pApi(url,cuerpo){const h={...auth()};if(cuerpo!==undefined)h['content-type']='application/json';
  const r=await fetch(url,{method:cuerpo!==undefined?'POST':'GET',headers:h,body:cuerpo!==undefined?JSON.stringify(cuerpo):undefined});
  const d=await r.json().catch(()=>({}));
  if(!r.ok){const e=new Error(typeof d.detail==='string'?d.detail:'No se pudo completar la solicitud.');e.status=r.status;e.datos=d;throw e}
  if(typeof d.restantes==='number')pRestantes(d.restantes);return d}

// --------------------------------------------------------------------------- arranque --
function perInit(){
  const raiz=pId('per-raiz');if(!raiz)return;
  if(!PER.listo){PER.listo=true;perConstruir(raiz)}
}
function perConstruir(raiz){
  raiz.textContent='';
  raiz.appendChild(pE('div',{class:'per-cab'},
    pBtn('← Volver a Ajustes','sec per-volver',()=>ver('config')),
    pE('p',{class:'per-claim',text:'Plataforma'}),pE('h2',{text:'Perfiles especializados'}),
    pE('p',{text:'Mil fichas: 10 áreas × 10 subespecialidades × 10 funciones. Un perfil es una ficha con instrucciones y un contrato de entrada y salida; no es un agente trabajando. El coordinador elige unos pocos para cada tarea y aquí se ve el estado real de cada uno.'})));
  const tabs=pE('div',{class:'per-tabs',role:'tablist','aria-label':'Secciones de Perfiles'});
  PER_TABS.forEach(([id,nombre])=>tabs.appendChild(pE('button',{type:'button',role:'tab',id:'per-tab-'+id,'aria-controls':'per-panel-'+id,
    'aria-selected':String(id===PER.tab),tabindex:id===PER.tab?'0':'-1',class:'per-tab'+(id===PER.tab?' on':''),
    on:{click:()=>perTab(id),keydown:perTabTeclas}},nombre)));
  raiz.appendChild(tabs);
  PER_TABS.forEach(([id])=>raiz.appendChild(pE('div',{role:'tabpanel',id:'per-panel-'+id,'aria-labelledby':'per-tab-'+id,
    class:'per-panel'+(id===PER.tab?'':' hidden'),tabindex:'-1'})));
  perRegistroVista();perCoordinadorVista();
}
function perTabTeclas(ev){
  const i=PER_TABS.findIndex(([id])=>id===PER.tab);let j=null;
  if(ev.key==='ArrowRight')j=(i+1)%PER_TABS.length;else if(ev.key==='ArrowLeft')j=(i+PER_TABS.length-1)%PER_TABS.length;
  else if(ev.key==='Home')j=0;else if(ev.key==='End')j=PER_TABS.length-1;
  if(j===null)return;ev.preventDefault();perTab(PER_TABS[j][0]);pId('per-tab-'+PER_TABS[j][0]).focus()}
function perTab(id){
  PER.tab=id;
  PER_TABS.forEach(([t])=>{const b=pId('per-tab-'+t);const on=t===id;b.classList.toggle('on',on);
    b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;pId('per-panel-'+t).classList.toggle('hidden',!on)});
  if(id==='ejecuciones')perEjecucionesVista();
}

// --------------------------------------------------------------------------- Registro --
async function perRegistroVista(){
  const p=pId('per-panel-registro');p.textContent='';
  p.appendChild(pE('p',{id:'per-cargando',class:'per-nota',text:'Cargando el registro…'}));
  let d;
  try{d=await pApi('/api/perfiles?meta=1&por_pagina=20')}
  catch(e){pId('per-cargando').textContent=e.message;return}
  PER.meta=d.meta;p.textContent='';
  p.appendChild(perResumenEstados());
  p.appendChild(perMatriz());
  p.appendChild(perFiltros());
  p.appendChild(pE('p',{id:'per-n',class:'per-n','aria-live':'polite'}));
  p.appendChild(pE('div',{id:'per-resultados'}));
  p.appendChild(pE('div',{id:'per-ficha',class:'hidden',tabindex:'-1'}));
  perPintarLista(d);
}
function perResumenEstados(){
  const m=PER.meta;
  const caja=pE('div',{class:'per-estados',role:'list','aria-label':'Perfiles por estado real'});
  m.estados.forEach(e=>caja.appendChild(pE('button',{type:'button',role:'listitem',class:'per-estado-t e-'+e.id.toLowerCase(),'data-estado':e.id,
    title:e.significado,on:{click:()=>{PER.f.estado=PER.f.estado===e.id?'':e.id;pId('per-f-estado').value=PER.f.estado;PER.f.pagina=1;perBuscar()}}},
    pE('b',{text:String(m.por_estado[e.id])}),pE('span',{text:e.nombre}))));
  return pE('div',{class:'per-bloque'},pE('h3',{class:'per-h',text:'Estado real de los '+m.total+' perfiles'}),caja,
    pE('p',{class:'per-nota',text:(m.por_estado.EJECUTADO===0?'Ningún perfil se ha ejecutado contra el modelo real. ':'')+
      '«Conectado a herramientas» significa que se puede ejecutar, no que alguien haya medido cómo responde. Los estados Evaluado y Aprobado exigen una evaluación con umbral y la aprobación de una persona.'}));
}
function perMatriz(){
  const m=PER.meta;
  const tabla=pE('table',{class:'per-matriz'});
  tabla.appendChild(pE('caption',{text:'Perfiles ejecutables hoy (de 10) por área y función. Toca una celda para ver esos perfiles.'}));
  tabla.appendChild(pE('thead',null,pE('tr',null,pE('th',{scope:'col',class:'per-m-esq'},pE('span',{class:'per-oculto',text:'Área'})),
    m.funciones.map(f=>pE('th',{scope:'col',title:f.nombre},pE('abbr',{title:f.nombre,text:f.id}))))));
  const cuerpo=pE('tbody');
  m.areas.forEach(a=>{
    const fila=pE('tr',null,pE('th',{scope:'row',title:a.nombre},pE('abbr',{title:a.nombre,text:a.id}),pE('span',{class:'per-m-area',text:a.nombre})));
    m.funciones.forEach(f=>{const c=m.matriz[a.id][f.id];const nivel=c.ejecutables===0?'n0':c.ejecutables===c.total?'n2':'n1';
      fila.appendChild(pE('td',null,pE('button',{type:'button',class:'per-celda '+nivel,'data-area':a.id,'data-funcion':f.id,
        'aria-label':a.id+' '+a.nombre+', '+f.id+' '+f.nombre+': '+c.ejecutables+' de '+c.total+' perfiles ejecutables',
        on:{click:()=>perFiltrarCelda(a.id,f.id)}},String(c.ejecutables))))});
    cuerpo.appendChild(fila)});
  tabla.appendChild(cuerpo);
  const leyenda=pE('details',{class:'per-leyenda'},pE('summary',{text:'Qué significa cada código'}),
    pE('div',{class:'per-leyenda-cols'},
      pE('div',null,pE('h4',{text:'Áreas'}),pE('ul',{class:'per-lista'},m.areas.map(a=>pE('li',null,pE('b',{text:a.id+' '}),a.nombre)))),
      pE('div',null,pE('h4',{text:'Funciones'}),pE('ul',{class:'per-lista'},m.funciones.map(f=>pE('li',null,pE('b',{text:f.id+' '}),f.nombre))))));
  return pE('div',{class:'per-bloque'},pE('h3',{class:'per-h',text:'Matriz área × función'}),pE('div',{class:'per-matriz-caja'},tabla),leyenda);
}
function perFiltrarCelda(area,funcion){
  PER.f.area=area;PER.f.funcion=funcion;PER.f.sub='';PER.f.estado='';PER.f.q='';PER.f.pagina=1;
  pId('per-q').value='';pId('per-f-area').value=area;perLlenarSubs();pId('per-f-funcion').value=funcion;pId('per-f-estado').value='';
  perBuscar().then(()=>{const n=pId('per-n');if(n)n.scrollIntoView({block:'start',behavior:'smooth'})});
}
function perFiltros(){
  const m=PER.meta;
  const q=pE('input',{type:'search',id:'per-q',class:'per-inp',placeholder:'Ej.: despido, tutela, copias de seguridad, A07-S04',autocomplete:'off'});
  const area=pE('select',{id:'per-f-area',class:'per-inp'},pE('option',{value:''},'Todas las áreas'),m.areas.map(a=>pE('option',{value:a.id},a.id+' · '+a.nombre)));
  const sub=pE('select',{id:'per-f-sub',class:'per-inp',disabled:true},pE('option',{value:''},'Todas las subespecialidades'));
  const funcion=pE('select',{id:'per-f-funcion',class:'per-inp'},pE('option',{value:''},'Todas las funciones'),m.funciones.map(f=>pE('option',{value:f.id},f.id+' · '+f.nombre)));
  const estado=pE('select',{id:'per-f-estado',class:'per-inp'},pE('option',{value:''},'Cualquier estado'),m.estados.map(e=>pE('option',{value:e.id},e.nombre+' ('+m.por_estado[e.id]+')')));
  q.addEventListener('input',()=>{clearTimeout(PER.busq);PER.busq=setTimeout(()=>{PER.f.q=q.value.trim();PER.f.pagina=1;perBuscar()},220)});
  area.addEventListener('change',()=>{PER.f.area=area.value;PER.f.sub='';perLlenarSubs();PER.f.pagina=1;perBuscar()});
  sub.addEventListener('change',()=>{PER.f.sub=sub.value;PER.f.pagina=1;perBuscar()});
  funcion.addEventListener('change',()=>{PER.f.funcion=funcion.value;PER.f.pagina=1;perBuscar()});
  estado.addEventListener('change',()=>{PER.f.estado=estado.value;PER.f.pagina=1;perBuscar()});
  const campo=(id,txt,ctl)=>pE('div',{class:'per-campo'},pE('label',{for:id,text:txt}),ctl);
  return pE('div',{class:'per-bloque'},pE('h3',{class:'per-h',text:'Buscar un perfil'}),
    pE('div',{class:'per-filtros',role:'search'},campo('per-q','Buscar por palabra o identificador',q),campo('per-f-area','Área',area),
      campo('per-f-sub','Subespecialidad',sub),campo('per-f-funcion','Función',funcion),campo('per-f-estado','Estado real',estado)),
    pE('div',{class:'per-acc'},pBtn('Quitar filtros','sec',perLimpiar,{id:'per-limpiar'})));
}
function perLlenarSubs(){
  const sub=pId('per-f-sub');sub.textContent='';sub.appendChild(pE('option',{value:''},'Todas las subespecialidades'));
  const a=PER.meta.areas.find(x=>x.id===PER.f.area);sub.disabled=!a;
  if(a)a.subespecialidades.forEach(s=>sub.appendChild(pE('option',{value:s.id},s.id+' · '+s.nombre)));
  sub.value=PER.f.sub||'';
}
function perLimpiar(){
  PER.f={q:'',area:'',sub:'',funcion:'',estado:'',pagina:1};
  pId('per-q').value='';pId('per-f-area').value='';perLlenarSubs();pId('per-f-funcion').value='';pId('per-f-estado').value='';perBuscar();
}
async function perBuscar(){
  const f=PER.f,ps=new URLSearchParams();
  if(f.q)ps.set('q',f.q);if(f.area)ps.set('area',f.area);if(f.sub)ps.set('subespecialidad',f.sub);
  if(f.funcion)ps.set('funcion',f.funcion);if(f.estado)ps.set('estado',f.estado);ps.set('pagina',String(f.pagina));
  // Solo se pinta la respuesta de la búsqueda más reciente (las respuestas pueden llegar en desorden).
  const turno=++PER.turno;
  try{const d=await pApi('/api/perfiles?'+ps.toString());if(turno===PER.turno)perPintarLista(d)}
  catch(e){if(turno===PER.turno)toast(e.message)}
}
function perPintarLista(d){
  perCerrarFicha(true);
  document.querySelectorAll('.per-estado-t').forEach(b=>b.classList.toggle('on',b.dataset.estado===PER.f.estado));
  pId('per-n').textContent=d.total===d.total_registro?d.total+' perfiles':d.total+' de '+d.total_registro+' perfiles';
  const c=pId('per-resultados');c.textContent='';
  if(!d.perfiles.length){c.appendChild(pE('p',{class:'per-vacio',text:'Ningún perfil cumple esos criterios. Prueba con otra palabra o quita los filtros.'}));return}
  const ul=pE('ul',{class:'per-items'});
  d.perfiles.forEach(p=>ul.appendChild(pE('li',null,pE('button',{type:'button',class:'per-item','data-perfil':p.id,on:{click:()=>perAbrirFicha(p.id)}},
    pE('span',{class:'per-item-cab'},pE('code',{text:p.id}),pEstado(p.estado_real)),
    pE('b',{text:p.nombre}),pE('span',{class:'per-item-p',text:p.proposito})))));
  c.appendChild(ul);
  if(d.paginas>1){
    const ir=n=>{PER.f.pagina=n;perBuscar().then(()=>{const x=pId('per-n');if(x)x.scrollIntoView({block:'start'})})};
    c.appendChild(pE('div',{class:'per-pag',role:'navigation','aria-label':'Páginas de resultados'},   // no <nav>: ese selector es el de la barra principal
      
      pBtn('Anterior','sec',()=>ir(d.pagina-1),{disabled:d.pagina<=1,id:'per-pag-ant'}),
      pE('span',{id:'per-pag-n',text:'Página '+d.pagina+' de '+d.paginas}),
      pBtn('Siguiente','sec',()=>ir(d.pagina+1),{disabled:d.pagina>=d.paginas,id:'per-pag-sig'})));
  }
}
function perCerrarFicha(silencio){
  const f=pId('per-ficha');if(!f)return;f.classList.add('hidden');f.textContent='';
  ['per-resultados','per-n'].forEach(id=>{const e=pId(id);if(e)e.classList.remove('hidden')});
  if(!silencio){const n=pId('per-n');if(n)n.scrollIntoView({block:'start'})}
}
async function perAbrirFicha(id){
  let p;try{p=await pApi('/api/perfiles/'+encodeURIComponent(id))}catch(e){toast(e.message);return}
  const f=pId('per-ficha');f.textContent='';
  ['per-resultados','per-n'].forEach(x=>pId(x).classList.add('hidden'));
  const pr=p.presupuesto,ca=p.condicion_de_activacion,ej=p.ejecuciones;
  const dl=pares=>pE('dl',{class:'per-dl'},pares.map(([k,v])=>[pE('dt',{text:k}),pE('dd',{text:String(v)})]));
  f.appendChild(pBtn('← Volver a la lista','sec per-volver',()=>perCerrarFicha()));
  f.appendChild(pE('div',{class:'per-ficha-cab'},pE('code',{class:'per-id',text:p.id}),pE('h3',{id:'per-ficha-t',tabindex:'-1',text:p.nombre}),
    pE('p',{class:'per-migas',text:p.area.id+' '+p.area.nombre+' › '+p.subespecialidad.id+' '+p.subespecialidad.nombre+' › '+p.funcion.id+' '+p.funcion.nombre})));
  f.appendChild(pE('div',{class:'per-estado-caja e-'+p.estado_real.toLowerCase()},
    pE('p',{class:'per-estado-linea'},pE('span',{text:'Estado real: '}),pEstado(p.estado_real)),
    pE('p',{id:'per-ficha-estado',text:p.estado_texto}),pE('p',{text:p.estado_motivo}),
    pE('p',{class:'per-nota',text:'Ejecuciones con el modelo real: '+ej.reales_completadas+' completadas de '+ej.reales+'. Ejecuciones simuladas (no cuentan): '+ej.simuladas+'.'})));
  f.appendChild(pBloque('Propósito',pE('p',{text:p.proposito})));
  f.appendChild(pBloque('Entradas',pLista(p.entradas)));
  f.appendChild(pBloque('Herramientas permitidas',pE('ul',{class:'per-lista'},p.herramientas_permitidas.map(h=>pE('li',null,h.nombre+' ',
    pE('span',{class:'per-tag '+(h.estado==='EXISTE'?'ok':'prop'),text:h.estado==='EXISTE'?'Existe hoy':'Propuesta: aún no existe'}),
    h.modo==='relevo'?pE('span',{class:'per-tag',text:'La acciona el usuario'}):null)))));
  f.appendChild(pBloque('Fuentes',pLista(p.fuentes)));
  f.appendChild(pBloque('Salida estructurada',pE('p',{class:'per-nota',text:p.salida_estructurada.formato}),
    pE('ol',{class:'per-lista'},p.salida_estructurada.secciones.map(s=>pE('li',null,pE('b',{text:s.titulo+'. '}),s.descripcion))),
    p.salida_estructurada.cierre?pE('p',{class:'per-nota',text:p.salida_estructurada.cierre}):null));
  f.appendChild(pBloque('Límites',pLista(p.limites)));
  f.appendChild(pBloque('Pruebas de aceptación',pLista(p.pruebas_de_aceptacion)));
  f.appendChild(pBloque('Presupuesto',dl([['Llamadas al modelo',pr.max_llamadas_modelo],['Tokens de salida (máx.)',pr.max_tokens_salida],
    ['Tiempo (máx.)',pr.tiempo_max_s+' s'],['Búsquedas web (máx.)',pr.max_busquedas_web],['Texto de entrada (máx.)',pr.max_caracteres_entrada+' caracteres'],
    ['Costo en tu plan',pr.consultas_del_plan+' consulta; se reintegra si falla']])));
  f.appendChild(pBloque('Condición de activación',pE('p',{text:ca.descripcion}),
    pE('p',{class:'per-nota',text:'Palabras que lo activan: '+ca.claves_subespecialidad.map(c=>c.replace(/\$$/,'')).join(', ')+'.'}),
    ca.solo_administracion?pE('p',{class:'per-nota',text:'Solo lo ejecuta la administración: consulta el repositorio y el estado del servicio.'}):null));
  f.appendChild(pBloque('Instrucciones (texto de sistema, '+p.instrucciones.length+' caracteres)',pE('pre',{class:'per-pre',text:p.instrucciones})));
  const usar=pBtn('Usar este perfil en el coordinador','pri',()=>perElegir(p.id),{id:'per-usar',disabled:!p.ejecutable_por_ti});
  f.appendChild(pE('div',{class:'per-acc'},usar,p.ejecutable_por_ti?null:pE('span',{class:'per-nota',text:'No lo puedes ejecutar: '+p.motivo_no_ejecutable})));
  f.classList.remove('hidden');pSubir();pId('per-ficha-t').focus({preventScroll:true});
}

// ------------------------------------------------------------------------- Coordinador --
function perElegir(id){
  if(PER.sel.includes(id)){toast('Ese perfil ya está elegido.')}
  else if(PER.sel.length>=4){toast('Una tarea admite como máximo 4 perfiles.');return}
  else PER.sel.push(id);
  perTab('coordinador');perPintarElegidos();pSubir();pId('per-tarea').focus();
}
function perPintarElegidos(){
  const c=pId('per-elegidos');if(!c)return;c.textContent='';
  if(!PER.sel.length){c.appendChild(pE('p',{class:'per-nota',text:'Sin perfiles elegidos a mano: el coordinador los escoge según la tarea.'}));return}
  c.appendChild(pE('p',{class:'per-nota',text:'Perfiles elegidos a mano ('+PER.sel.length+' de 4). El coordinador usará estos y no escogerá otros.'}));
  c.appendChild(pE('div',{class:'per-chips'},PER.sel.map(id=>pE('button',{type:'button',class:'per-chip','aria-label':'Quitar '+id,
    on:{click:()=>{PER.sel=PER.sel.filter(x=>x!==id);perPintarElegidos()}}},id+' ×'))));
}
function perCoordinadorVista(){
  const p=pId('per-panel-coordinador');p.textContent='';
  p.appendChild(pE('div',{class:'per-bloque'},pE('h3',{class:'per-h',text:'Coordinador'}),
    pE('p',{class:'per-nota',text:'Describe la tarea. El coordinador elige por reglas los pocos perfiles útiles (máximo 4) y los ejecuta uno después de otro. Ver el plan no gasta consultas; ejecutar cuesta 1 consulta por perfil y se reintegra si ese perfil falla.'}),
    pE('div',{class:'per-campo'},pE('label',{for:'per-tarea',text:'Tarea'}),
      pE('textarea',{id:'per-tarea',class:'per-inp',rows:'4',maxlength:'4000',placeholder:'Ej.: Me despidieron sin justa causa después de tres años con contrato a término indefinido.'})),
    pE('details',{class:'per-det'},pE('summary',{text:'Agregar material (opcional)'}),
      pE('div',{class:'per-campo'},pE('label',{for:'per-material',text:'Texto de documentos o datos del caso. Llega a los perfiles como datos, no como instrucciones.'}),
        pE('textarea',{id:'per-material',class:'per-inp',rows:'5',maxlength:'12000'}))),
    pE('label',{class:'per-check'},pE('input',{type:'checkbox',id:'per-web'}),pE('span',{text:'Permitir búsqueda web restringida a sitios oficiales (solo los perfiles que la tienen)'})),
    pE('div',{id:'per-elegidos'}),
    pE('div',{class:'per-acc'},pBtn('Ver plan (no gasta consultas)','pri',perPlan,{id:'per-ver-plan'}),pBtn('Empezar de nuevo','sec',perReiniciar,{id:'per-reiniciar'}))));
  p.appendChild(pE('div',{id:'per-plan','aria-live':'polite'}));
  p.appendChild(pE('div',{id:'per-resultado'}));
  perPintarElegidos();
}
function perReiniciar(){PER.sel=[];PER.contexto={};PER.plan=null;pId('per-tarea').value='';pId('per-material').value='';pId('per-web').checked=false;
  pId('per-plan').textContent='';pId('per-resultado').textContent='';perPintarElegidos()}
function perContexto(){const c={...PER.contexto};if(PER.sel.length)c.perfiles=PER.sel.slice();return c}
async function perPlan(){
  if(PER.ocupado)return;
  const tarea=pId('per-tarea').value.trim();
  const caja=pId('per-plan');pId('per-resultado').textContent='';
  if(!tarea){caja.textContent='';caja.appendChild(pE('p',{class:'per-error',role:'alert',text:'Escribe la tarea.'}));pId('per-tarea').focus();return}
  let plan;
  try{plan=await pApi('/api/coordinador/plan',{tarea,contexto:perContexto()})}
  catch(e){caja.textContent='';caja.appendChild(pE('p',{class:'per-error',role:'alert',text:e.message}));return}
  PER.plan=plan;perPintarPlan(plan);
}
function perPintarPlan(plan){
  const caja=pId('per-plan');caja.textContent='';
  const b=pE('div',{class:'per-bloque',id:'per-plan-caja','data-estado':plan.estado});
  if(plan.estado!=='LISTO'){
    b.appendChild(pE('h3',{class:'per-h',text:'Faltan datos para elegir los perfiles'}));
    b.appendChild(pE('p',{text:plan.motivo}));
    b.appendChild(pLista(plan.preguntas,'per-preguntas'));
    if(plan.opciones.length){b.appendChild(pE('p',{class:'per-nota',text:'Puedes elegir aquí y el coordinador vuelve a armar el plan:'}));
      b.appendChild(pE('div',{class:'per-chips'},plan.opciones.map(o=>pE('button',{type:'button',class:'per-chip','data-opcion':o.id,
        on:{click:()=>{PER.contexto=o.id.includes('-')?{subespecialidad:o.id}:{area:o.id};perPlan()}}},o.id+' · '+o.nombre))))}
    caja.appendChild(b);return}
  b.appendChild(pE('h3',{class:'per-h',text:'Plan del coordinador'}));
  const de=[];if(plan.subespecialidad)de.push('Tema: '+plan.subespecialidad.nombre+' ('+plan.subespecialidad.id+')');
  if(plan.intencion)de.push('La tarea pide: '+plan.intencion.nombre);de.push('Modo: secuencial (un perfil a la vez)');
  b.appendChild(pLista(de));
  b.appendChild(pE('ol',{class:'per-plan-pasos'},plan.perfiles.map(f=>pE('li',{class:'per-plan-paso'+(f.ejecutable?'':' no'),'data-perfil':f.id},
    pE('span',{class:'per-item-cab'},pE('code',{text:f.id}),pEstado(f.estado_real)),pE('b',{text:f.nombre}),
    pE('span',{class:'per-item-p',text:f.ejecutable?'Por qué: '+f.regla:'No se ejecutará: '+f.motivo_no_ejecutable}),
    pBtn('Ver ficha','sec chip',()=>{perTab('registro');perAbrirFicha(f.id)})))));
  const n=plan.costo.consultas;
  b.appendChild(pE('p',{id:'per-costo',class:'per-nota',text:'Costo: '+n+(n===1?' consulta':' consultas')+' · hasta '+plan.costo.llamadas_modelo+' llamadas al modelo · tiempo máximo '+plan.costo.tiempo_max_s+' s. '+plan.costo.nota}));
  if(plan.datos_utiles&&plan.datos_utiles.length)b.appendChild(pE('details',{class:'per-det'},pE('summary',{text:'Datos que conviene incluir en la tarea'}),pLista(plan.datos_utiles)));
  if(PER.meta&&PER.meta.motor.simulado)b.appendChild(pE('p',{class:'per-aviso',text:'Este servidor usa un modelo simulado: la ejecución prueba el flujo y no cuenta como perfil ejecutado.'}));
  b.appendChild(pE('div',{class:'per-acc'},pBtn(n?'Ejecutar ('+n+(n===1?' consulta)':' consultas)'):'Nada que ejecutar','pri',perEjecutar,{id:'per-ejecutar',disabled:n===0})));
  caja.appendChild(b);
}
async function perEjecutar(){
  if(PER.ocupado)return;
  const tarea=pId('per-tarea').value.trim(),boton=pId('per-ejecutar'),caja=pId('per-resultado');
  PER.ocupado=true;boton.disabled=true;boton.textContent='Ejecutando en secuencia…';caja.textContent='';
  caja.appendChild(pE('p',{class:'per-nota',role:'status',text:'Los perfiles se ejecutan uno después de otro. Puede tardar hasta un par de minutos.'}));
  try{const r=await pApi('/api/coordinador/ejecutar',{tarea,contexto:perContexto(),material:pId('per-material').value,web:pId('per-web').checked});
    caja.textContent='';perPintarResumen(caja,r);boton.textContent='Ejecutado';caja.scrollIntoView({block:'start',behavior:'smooth'})}
  catch(e){caja.textContent='';caja.appendChild(pE('p',{class:'per-error',role:'alert',text:e.message}));
    if(e.datos&&e.datos.plan){PER.plan=e.datos.plan;perPintarPlan(e.datos.plan)}else{boton.disabled=false;boton.textContent='Reintentar'}}
  PER.ocupado=false;
}
function perPintarResumen(caja,r){
  const b=pE('div',{class:'per-bloque per-resumen',id:'per-resumen','data-estado':r.estado});
  b.appendChild(pE('h3',{class:'per-h',text:'Resumen auditable'+(r.id?' n.º '+r.id:'')}));
  if(r.motor&&r.motor.simulado)b.appendChild(pE('p',{class:'per-aviso',id:'per-simulada',text:'EJECUCIÓN SIMULADA: el motor fue un doble de prueba, no el modelo real. No cuenta como perfil ejecutado ni dice nada de la calidad.'}));
  const rec=r.recursos||{};
  b.appendChild(pE('dl',{class:'per-dl'},[['Tarea',r.tarea],['Estado',PER_EJEC[r.estado]||r.estado],['Modo',r.modo==='SECUENCIAL'?'Secuencial':r.modo],
    ['Motor',(r.motor&&r.motor.modelo||'—')+(r.motor&&r.motor.simulado?' (simulado)':'')],
    ['Recursos',(rec.llamadas_modelo||0)+' llamadas al modelo · '+(rec.consultas_netas||0)+' consultas descontadas'+(rec.consultas_reintegradas?' ('+rec.consultas_reintegradas+' reintegradas)':'')+' · '+((rec.duracion_ms||0)/1000).toFixed(1)+' s'+(rec.tokens_salida!=null?' · '+rec.tokens_salida+' tokens de salida':'')],
    ['Comprobaciones',r.comprobaciones.pasan+' pasan · '+r.comprobaciones.fallan+' fallan (revisan el contrato de salida, no la corrección de fondo)']]
    .map(([k,v])=>[pE('dt',{text:k}),pE('dd',{text:String(v)})])));
  const d=r.discrepancias||{};
  if(d.hay){b.appendChild(pE('div',{class:'per-discrepancia',id:'per-discrepancia'},pE('h4',{text:'Los perfiles discrepan: requiere revisión humana'}),
    pE('p',{text:d.explicacion}),pE('p',{class:'per-nota',text:d.regla+' '+d.nota}),
    pE('ul',{class:'per-lista'},d.alternativas.map(a=>pE('li',null,pE('b',{text:a.perfil+' — sentido '+a.sentido+'. '}),a.fundamento||'')))))}
  (r.errores||[]).forEach(e=>b.appendChild(pE('p',{class:'per-error',text:e.perfil+': '+e.mensaje+(e.codigo?' (código '+e.codigo+')':'')})));
  (r.perfiles||[]).forEach((p,i)=>{
    const cab=pE('summary',null,pE('code',{text:p.id}),' ',pE('span',{class:'per-tag '+(p.estado==='ejecutado'?'ok':'prop'),text:PER_PASO[p.estado]||p.estado}),
      p.sentido?pE('span',{class:'per-tag',text:'Sentido: '+p.sentido}):null);
    const det=pE('details',{class:'per-det per-paso','data-perfil':p.id,open:p.estado==='ejecutado'&&i===r.perfiles.length-1||r.perfiles.length===1},cab,pE('p',{class:'per-nota',text:p.nombre}));
    if(p.motivo)det.appendChild(pE('p',{class:'per-nota',text:p.motivo}));
    if(p.resultado){const m=pE('div',{class:'md per-salida'});m.innerHTML=md(p.resultado);det.appendChild(m)}
    if(p.documento_id!=null)det.appendChild(pE('p',{class:'per-nota',text:'El entregable quedó guardado en Documentos › Mis documentos (n.º '+p.documento_id+'); desde allí se descarga en Word.'}));
    if(p.comprobaciones&&p.comprobaciones.length)det.appendChild(pBloque('Comprobaciones',pE('ul',{class:'per-lista per-comp'},
      p.comprobaciones.map(c=>pE('li',{class:c.resultado},pE('b',{text:(c.resultado==='pasa'?'Pasa':'Falla')+' · '+c.nombre+'. '}),c.detalle)))));
    if(p.herramientas&&p.herramientas.length)det.appendChild(pBloque('Herramientas',pE('ul',{class:'per-lista'},
      p.herramientas.map(h=>pE('li',null,pE('b',{text:h.nombre+': '}),h.resultado||(h.usada?'usada':'no usada'))))));
    if(p.fuentes&&p.fuentes.length)det.appendChild(pBloque('Fuentes',pE('ul',{class:'per-lista'},
      p.fuentes.map(f=>pE('li',{text:(f.titulo||'Fuente')+(f.ubicacion?' · '+f.ubicacion:'')+(f.estado_vigencia?' · '+f.estado_vigencia:'')+(f.nota?' · '+f.nota:'')})))));
    b.appendChild(det)});
  (r.avisos||[]).slice(r.motor&&r.motor.simulado?1:0).forEach(a=>b.appendChild(pE('p',{class:'per-nota',text:a})));
  caja.appendChild(b);
}

// --------------------------------------------------------------------- Mis ejecuciones --
async function perEjecucionesVista(){
  const p=pId('per-panel-ejecuciones');p.textContent='';
  p.appendChild(pE('p',{class:'per-nota',text:'Cada ejecución deja un resumen: tarea, perfiles, fuentes, herramientas, resultado, comprobaciones, errores y recursos. No se guardan razonamientos internos del modelo. Solo tú ves las tuyas.'}));
  const lista=pE('div',{id:'per-ejec-lista'}),abierta=pE('div',{id:'per-ejec-abierta'});p.appendChild(lista);p.appendChild(abierta);
  let d;try{d=await pApi('/api/coordinador/ejecuciones')}catch(e){lista.appendChild(pE('p',{class:'per-vacio',text:e.message}));return}
  if(!d.ejecuciones.length){lista.appendChild(pE('p',{class:'per-vacio',text:'Aún no has ejecutado ninguna tarea con el coordinador.'}));return}
  lista.appendChild(pE('ul',{class:'per-items'},d.ejecuciones.map(e=>pE('li',null,pE('button',{type:'button',class:'per-item','data-ejecucion':e.id,
    on:{click:async()=>{try{const r=await pApi('/api/coordinador/ejecuciones/'+e.id);abierta.textContent='';perPintarResumen(abierta,r);abierta.scrollIntoView({block:'start',behavior:'smooth'})}catch(x){toast(x.message)}}}},
    pE('span',{class:'per-item-cab'},pE('code',{text:'n.º '+e.id}),pE('span',{class:'per-tag',text:PER_EJEC[e.estado]||e.estado}),e.simulada?pE('span',{class:'per-tag prop',text:'Simulada'}):null),
    pE('b',{text:e.tarea}),pE('span',{class:'per-item-p',text:pFecha(e.creado)+' · '+e.perfiles_ids.join(', ')}))))));
}
