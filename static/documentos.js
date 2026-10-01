// =========================================================================================
// PULLEX Documentos — el automatizador: Escritos (catálogo), Flujos, Asistente y Mis documentos.
// Se carga después de app.js y usa sus utilidades globales (auth, md, toast, PERFIL, pintarFuentes).
// Sin JavaScript en línea: todo con addEventListener. Los datos del servidor se pintan con
// textContent; solo el borrador en Markdown pasa por md() (marked + DOMPurify).
// =========================================================================================
const DOC={listo:false,tab:'escritos',catalogo:null,areas:[],flujos:null,maxPasos:6,tipo:null,flujo:null,
  plan:null,mis:[],ocupado:false,busq:null};
const DOC_PARA={abogado:'Abogado',ciudadano:'Ciudadano',funcionario:'Funcionario',estudiante:'Estudiante'};
const DOC_TABS=[['escritos','Escritos'],['flujos','Flujos'],['asistente','Asistente'],['mis','Mis documentos']];
const DOC_EJEMPLOS=['Prepara una tutela contra mi EPS porque no me entrega un medicamento formulado hace dos meses.',
  'Analiza si puedo cobrar judicialmente un pagaré vencido hace un año y redacta la demanda ejecutiva.',
  'Me despidieron sin justa causa después de tres años: calcula lo que me deben y redacta la reclamación.'];

// ------------------------------------------------------------------------- utilidades --
function dE(tag,attrs,...hijos){const e=document.createElement(tag);
  if(attrs)for(const [k,v] of Object.entries(attrs)){if(v==null||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;else if(k==='on')Object.entries(v).forEach(([ev,fn])=>e.addEventListener(ev,fn));
    else e.setAttribute(k,v===true?'':v)}
  hijos.flat().forEach(h=>{if(h==null||h===false)return;e.appendChild(typeof h==='string'?document.createTextNode(h):h)});
  return e}
function dBtn(txt,cls,fn,attrs){return dE('button',{type:'button',class:'doc-btn'+(cls?' '+cls:''),on:{click:fn},...(attrs||{})},txt)}
function dRestantes(n){if(typeof n!=='number'||!PERFIL)return;PERFIL.restantes=n;PERFIL.usadas=PERFIL.limite-n;
  const c=document.getElementById('c-rest');if(c)c.textContent=n;const u=document.getElementById('cf-uso');if(u)u.textContent=PERFIL.usadas+' / '+PERFIL.limite}
async function docApi(url,opc){const o=opc||{};const h={...auth()};if(o.body!==undefined)h['content-type']='application/json';
  const r=await fetch(url,{method:o.method||(o.body!==undefined?'POST':'GET'),headers:h,body:o.body!==undefined?JSON.stringify(o.body):undefined});
  const d=await r.json().catch(()=>({}));
  if(!r.ok){const e=new Error(typeof d.detail==='string'?d.detail:'No se pudo completar la solicitud.');e.errores=d.errores;e.status=r.status;throw e}
  if(typeof d.restantes==='number')dRestantes(d.restantes);return d}
async function docSSE(url,body,alEvento){
  const r=await fetch(url,{method:'POST',headers:{...auth(),'content-type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok){const d=await r.json().catch(()=>({}));const e=new Error(typeof d.detail==='string'?d.detail:'No se pudo iniciar.');e.errores=d.errores;e.status=r.status;throw e}
  const rd=r.body.getReader(),dec=new TextDecoder();let resto='';
  while(true){const {value,done}=await rd.read();if(done)break;resto+=dec.decode(value,{stream:true});
    const partes=resto.split('\n\n');resto=partes.pop();
    for(const l of partes){if(!l.startsWith('data: '))continue;let ev;try{ev=JSON.parse(l.slice(6))}catch(e){continue}alEvento(ev)}}
}
function docFecha(ts){try{return new Date(ts*1000).toLocaleString('es-CO',{dateStyle:'medium',timeStyle:'short'})}catch(e){return ''}}
async function docCopiar(texto){try{await navigator.clipboard.writeText(texto);toast('Copiado')}catch(e){toast('No se pudo copiar: selecciona el texto y cópialo.')}}
// Descarga el .docx (en la demostración se reemplaza por un aviso).
async function docDescargarWord(id,boton){
  if(boton){boton.disabled=true}
  try{const r=await fetch('/api/documentos/'+encodeURIComponent(id)+'/docx',{headers:auth()});
    if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(d.detail||'No se pudo exportar.')}
    const cd=r.headers.get('content-disposition')||'';const m=cd.match(/filename="([^"]+)"/);
    const bl=await r.blob();const u=URL.createObjectURL(bl);const a=dE('a',{href:u,download:m?m[1]:'pullex-documento.docx'});
    document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),2000);toast('Descargado en Word')}
  catch(e){toast(e.message)}
  if(boton)boton.disabled=false}

// --------------------------------------------------------------------------- arranque --
function docInit(){
  const raiz=document.getElementById('doc-raiz');if(!raiz)return;
  if(!DOC.listo){DOC.listo=true;docConstruir(raiz)}
  if(DOC.tab==='mis')docCargarMis();
}
function docConstruir(raiz){
  raiz.textContent='';
  raiz.appendChild(dE('div',{class:'doc-cab'},dE('p',{class:'doc-claim',text:'PULLEX Documentos'}),dE('h2',{text:'Automatizador'}),
    dE('p',{text:'Borradores de escritos de todas las áreas del derecho colombiano, flujos de trabajo de varios pasos y un asistente que investiga, analiza y redacta por ti. Todo lo que sale de aquí es un borrador para revisar.'})));
  const tabs=dE('div',{class:'doc-tabs',role:'tablist','aria-label':'Secciones del automatizador'});
  DOC_TABS.forEach(([id,nombre])=>tabs.appendChild(dE('button',{type:'button',role:'tab',id:'doc-tab-'+id,'aria-controls':'doc-panel-'+id,
    'aria-selected':String(id===DOC.tab),tabindex:id===DOC.tab?'0':'-1',class:'doc-tab'+(id===DOC.tab?' on':''),
    on:{click:()=>docTab(id),keydown:docTabTeclas}},nombre)));
  raiz.appendChild(tabs);
  DOC_TABS.forEach(([id])=>raiz.appendChild(dE('div',{role:'tabpanel',id:'doc-panel-'+id,'aria-labelledby':'doc-tab-'+id,
    class:'doc-panel'+(id===DOC.tab?'':' hidden'),tabindex:'-1'})));
  docEscritosVista();docFlujosVista();docAsistenteVista();
}
function docTabTeclas(ev){
  const i=DOC_TABS.findIndex(([id])=>id===DOC.tab);let j=null;
  if(ev.key==='ArrowRight')j=(i+1)%DOC_TABS.length;else if(ev.key==='ArrowLeft')j=(i+DOC_TABS.length-1)%DOC_TABS.length;
  else if(ev.key==='Home')j=0;else if(ev.key==='End')j=DOC_TABS.length-1;
  if(j===null)return;ev.preventDefault();docTab(DOC_TABS[j][0]);document.getElementById('doc-tab-'+DOC_TABS[j][0]).focus()}
function docTab(id){
  DOC.tab=id;
  DOC_TABS.forEach(([t])=>{const b=document.getElementById('doc-tab-'+t);const on=t===id;b.classList.toggle('on',on);
    b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('doc-panel-'+t).classList.toggle('hidden',!on)});
  if(id==='mis')docCargarMis();if(id==='flujos')docFlujosVista();
}
function docPanel(id){return document.getElementById('doc-panel-'+id)}
function docSubir(){const m=document.querySelector('main');if(m)m.scrollTop=0}

// ------------------------------------------------------------------------- Escritos --
async function docEscritosVista(){
  const p=docPanel('escritos');p.textContent='';
  const q=dE('input',{type:'search',id:'doc-q',class:'doc-inp',placeholder:'Ej.: tutela, pagaré, despido, mandamiento de pago',autocomplete:'off'});
  const area=dE('select',{id:'doc-area',class:'doc-inp'},dE('option',{value:''},'Todas las áreas'));
  const para=dE('select',{id:'doc-para',class:'doc-inp'},dE('option',{value:''},'Para cualquier persona'),
    ...Object.entries(DOC_PARA).map(([k,v])=>dE('option',{value:k},v)));
  p.appendChild(dE('div',{class:'doc-filtros',role:'search'},
    dE('div',{class:'doc-f-q'},dE('label',{for:'doc-q',text:'Buscar documento'}),q),
    dE('div',null,dE('label',{for:'doc-area',text:'Área'}),area),
    dE('div',null,dE('label',{for:'doc-para',text:'Para'}),para)));
  p.appendChild(dE('p',{id:'doc-n',class:'doc-n','aria-live':'polite'}));
  p.appendChild(dE('div',{id:'doc-grid',class:'doc-grid'}));
  p.appendChild(dE('div',{id:'doc-trabajo'}));
  const buscar=()=>{clearTimeout(DOC.busq);DOC.busq=setTimeout(docBuscar,220)};
  q.addEventListener('input',buscar);area.addEventListener('change',docBuscar);para.addEventListener('change',docBuscar);
  try{const d=await docApi('/api/documentos/catalogo');DOC.areas=d.areas;
    d.areas.forEach(a=>area.appendChild(dE('option',{value:a.area},a.area+' ('+a.n+')')));
    DOC.total=d.total;docPintarTarjetas(d.tipos,d.total)}
  catch(e){document.getElementById('doc-n').textContent=e.message}
}
async function docBuscar(){
  const q=document.getElementById('doc-q').value.trim(),a=document.getElementById('doc-area').value,pq=document.getElementById('doc-para').value;
  const ps=new URLSearchParams();if(q)ps.set('q',q);if(a)ps.set('area',a);if(pq)ps.set('para',pq);
  // Solo se pinta la respuesta de la búsqueda más reciente (las respuestas pueden llegar en desorden).
  const turno=DOC.turno=(DOC.turno||0)+1;
  try{const d=await docApi('/api/documentos/catalogo?'+ps.toString());if(turno===DOC.turno)docPintarTarjetas(d.tipos,d.total)}
  catch(e){if(turno===DOC.turno)toast(e.message)}
}
function docPintarTarjetas(tipos,total){
  document.getElementById('doc-n').textContent=tipos.length===total?total+' tipos de documento':tipos.length+' de '+total+' tipos de documento';
  const g=document.getElementById('doc-grid');g.textContent='';
  if(!tipos.length){g.appendChild(dE('p',{class:'doc-vacio',text:'No hay documentos con ese criterio. Prueba con otra palabra o quita los filtros.'}));return}
  tipos.forEach(t=>{
    const chips=dE('span',{class:'doc-chips'},...t.para_quien.map(x=>dE('span',{class:'doc-chip',text:DOC_PARA[x]||x})));
    if(t.borrador_funcionario)chips.prepend(dE('span',{class:'doc-chip proy',text:'Proyecto para despacho'}));
    g.appendChild(dE('button',{type:'button',class:'doc-card','data-tipo':t.id,on:{click:()=>docAbrirTipo(t.id)}},
      dE('span',{class:'doc-card-area',text:t.area+' · '+t.subarea}),dE('b',{text:t.nombre}),dE('span',{class:'doc-card-d',text:t.descripcion}),chips))});
}
function docModoTrabajo(on){['doc-grid','doc-n'].forEach(id=>document.getElementById(id).classList.toggle('hidden',on));
  const f=docPanel('escritos').querySelector('.doc-filtros');if(f)f.classList.toggle('hidden',on)}
function docVolverCatalogo(){document.getElementById('doc-trabajo').textContent='';docModoTrabajo(false);DOC.tipo=null;
  const c=document.querySelector('#doc-grid .doc-card');docSubir();if(c)c.focus()}
async function docAbrirTipo(id,valores){
  let t;try{t=await docApi('/api/documentos/catalogo/'+encodeURIComponent(id))}catch(e){toast(e.message);return}
  if(DOC.tab!=='escritos')docTab('escritos');
  DOC.tipo=t;docModoTrabajo(true);const w=document.getElementById('doc-trabajo');w.textContent='';
  w.appendChild(dBtn('← Volver al catálogo','sec doc-volver',docVolverCatalogo));
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:t.nombre});
  w.appendChild(dE('div',{class:'doc-bloque'},dE('p',{class:'doc-card-area',text:t.area+' · '+t.subarea}),h,dE('p',{class:'doc-desc',text:t.descripcion}),
    t.borrador_funcionario?dE('p',{class:'doc-aviso',text:'Proyecto para revisión del funcionario: el resultado saldrá rotulado como BORRADOR y sin firma.'}):null,
    docDetalles('Qué secciones tendrá el escrito',dE('ol',{class:'doc-lista'},...t.estructura.map(s=>dE('li',{text:s})))),
    t.notas_de_forma.length?docDetalles('Requisitos de forma',dE('ul',{class:'doc-lista'},...t.notas_de_forma.map(s=>dE('li',{text:s})))):null,
    t.advertencias.length?docDetalles('Advertencias (términos, competencia, cuantía)',dE('ul',{class:'doc-lista'},...t.advertencias.map(s=>dE('li',{text:s})))):null));
  const form=docFormulario(t.campos,valores||{},'doc-f');
  const enviar=dBtn('Generar borrador','pri',()=>docGenerar(form,enviar),{id:'doc-generar'});
  w.appendChild(dE('form',{class:'doc-bloque doc-form',novalidate:true,on:{submit:ev=>{ev.preventDefault();docGenerar(form,enviar)}}},
    dE('p',{class:'doc-intro',text:'Si no tienes un dato, déjalo en blanco: quedará marcado entre corchetes para completarlo después. Los campos con * son obligatorios.'}),
    form.nodo,form.resumen,dE('div',{class:'doc-acc'},enviar),
    dE('p',{class:'doc-costo',text:'Usa 1 consulta. Si la generación falla, no se descuenta.'})));
  docSubir();h.focus();
}
function docDetalles(titulo,cuerpo){return dE('details',{class:'doc-det'},dE('summary',{text:titulo}),cuerpo)}

// Formulario dinámico generado desde el catálogo, con validación accesible.
function docFormulario(campos,valores,prefijo){
  const nodo=dE('div',{class:'doc-campos'});const resumen=dE('div',{class:'doc-resumen hidden',role:'alert'});const ctl={};
  campos.forEach(c=>{
    const id=prefijo+'-'+c.id,idA=id+'-ayuda',idE=id+'-err';let inp;
    if(c.tipo==='textarea')inp=dE('textarea',{rows:c.max>6000?8:4,maxlength:c.max});
    else if(c.tipo==='select'){inp=dE('select',null,dE('option',{value:''},'Elige una opción'),...(c.opciones||[]).map(o=>dE('option',{value:o},o)))}
    else if(c.tipo==='fecha')inp=dE('input',{type:'date',min:'1900-01-01',max:'2100-12-31'});
    else if(c.tipo==='numero')inp=dE('input',{type:'text',inputmode:'decimal',maxlength:24,autocomplete:'off'});
    else inp=dE('input',{type:'text',maxlength:c.max});
    inp.id=id;inp.name=c.id;inp.className='doc-inp';
    if(c.requerido){inp.required=true;inp.setAttribute('aria-required','true')}
    if(c.ayuda)inp.setAttribute('aria-describedby',idA);
    const v=valores[c.id];if(v!=null)inp.value=String(v);
    inp.addEventListener('input',()=>docLimpiarError(inp));inp.addEventListener('change',()=>docLimpiarError(inp));
    const lb=dE('label',{for:id},c.etiqueta,c.requerido?dE('span',{class:'doc-req','aria-hidden':'true',text:' *'}):dE('span',{class:'doc-opc',text:' (opcional)'}));
    nodo.appendChild(dE('div',{class:'doc-campo'+(c.tipo==='textarea'?' ancho':''),'data-campo':c.id},lb,
      c.ayuda?dE('p',{class:'doc-ayuda',id:idA,text:c.ayuda}):null,inp,dE('p',{class:'doc-err hidden',id:idE})));
    ctl[c.id]={c,inp,idA,idE};
  });
  const leer=()=>{const o={};Object.values(ctl).forEach(({c,inp})=>{const v=inp.value.trim();if(v)o[c.id]=v});return o};
  const marcar=(errores)=>{let primero=null;const n=Object.keys(errores).length;
    Object.values(ctl).forEach(x=>docLimpiarError(x.inp));
    Object.entries(errores).forEach(([k,msg])=>{const x=ctl[k];if(!x)return;docMarcarError(x,msg);if(!primero)primero=x.inp});
    resumen.classList.toggle('hidden',!n);
    resumen.textContent=n?(n===1?'Hay 1 dato por revisar.':'Hay '+n+' datos por revisar.')+(errores._?' '+errores._:''):'';
    if(primero)primero.focus();return !n};
  const validar=()=>{const e={};
    Object.values(ctl).forEach(({c,inp})=>{const v=inp.value.trim();
      if(!v){if(c.requerido)e[c.id]='Este dato es obligatorio.';return}
      if(v.length>c.max)e[c.id]='Máximo '+c.max+' caracteres.';
      else if(c.tipo==='numero'&&!/^(\d{1,3}(\.\d{3})+(,\d+)?|\d{1,3}(,\d{3})+(\.\d+)?|\d+([.,]\d+)?)$/.test(v.replace(/[$\s]/g,'')))e[c.id]='Escribe solo números (por ejemplo 1500000).';
      else if(c.tipo==='fecha'&&!/^\d{4}-\d{2}-\d{2}$/.test(v))e[c.id]='Escribe una fecha válida (AAAA-MM-DD).';
      else if(c.tipo==='select'&&!(c.opciones||[]).includes(v))e[c.id]='Elige una de las opciones.'});
    return marcar(e)};
  return {nodo,resumen,leer,validar,marcar};
}
function docMarcarError(x,msg){x.inp.setAttribute('aria-invalid','true');x.inp.classList.add('error');
  const e=document.getElementById(x.idE);e.textContent=msg;e.classList.remove('hidden');
  x.inp.setAttribute('aria-describedby',[x.c.ayuda?x.idA:null,x.idE].filter(Boolean).join(' '))}
function docLimpiarError(inp){if(inp.getAttribute('aria-invalid')!=='true')return;inp.removeAttribute('aria-invalid');inp.classList.remove('error');
  const e=document.getElementById(inp.id+'-err');if(e){e.textContent='';e.classList.add('hidden')}
  const a=document.getElementById(inp.id+'-ayuda');if(a)inp.setAttribute('aria-describedby',a.id);else inp.removeAttribute('aria-describedby')}

async function docGenerar(form,boton){
  if(DOC.ocupado)return;if(!form.validar())return;
  if(PERFIL&&PERFIL.restantes<=0){toast('Se agotaron tus consultas. Actualiza tu plan.');return}
  DOC.ocupado=true;const t0=boton.textContent;boton.disabled=true;boton.textContent='Redactando borrador…';
  const w=document.getElementById('doc-trabajo');const espera=dE('div',{class:'doc-espera',role:'status'},
    dE('div',{class:'skel'}),dE('div',{class:'skel'}),dE('p',{text:'PULLEX está redactando el borrador. Puede tardar hasta un minuto.'}));
  w.appendChild(espera);espera.scrollIntoView({behavior:'smooth',block:'nearest'});
  try{const d=await docApi('/api/documentos/generar',{body:{tipo:DOC.tipo.id,campos:form.leer()}});
    espera.remove();docMostrarResultado(w,d,{nuevo:true})}
  catch(e){espera.remove();if(e.errores)form.marcar(e.errores);toast(e.message)}
  boton.disabled=false;boton.textContent=t0;DOC.ocupado=false;
}

// Vista del borrador: render seguro, lista de datos a verificar, advertencias, fuentes y acciones.
function docMostrarResultado(cont,doc,opc){
  const viejo=cont.querySelector('.doc-res');if(viejo)viejo.remove();
  const estado={texto:doc.texto,editando:false};
  const cuerpo=dE('div',{class:'md doc-texto'});cuerpo.innerHTML=md(doc.texto);
  const area=dE('textarea',{class:'doc-inp doc-editor hidden',rows:18,'aria-label':'Editar el texto del borrador'});
  const titulo=dE('h3',{class:'doc-h',tabindex:'-1',text:doc.titulo||'Documento'});
  const bEditar=dBtn('Editar texto','sec',()=>{
    if(!estado.editando){area.value=estado.texto;estado.editando=true;cuerpo.classList.add('hidden');area.classList.remove('hidden');bEditar.textContent='Ver vista previa';area.focus()}
    else{estado.texto=area.value;estado.editando=false;cuerpo.innerHTML=md(estado.texto);cuerpo.classList.remove('hidden');area.classList.add('hidden');bEditar.textContent='Editar texto'}});
  const bGuardar=dBtn('Guardar','pri',async()=>{const texto=estado.editando?area.value:estado.texto;
    bGuardar.disabled=true;try{const d=await docApi('/api/documentos/'+doc.id,{method:'PUT',body:{texto}});estado.texto=d.texto;
      if(!estado.editando)cuerpo.innerHTML=md(estado.texto);toast('Cambios guardados en Mis documentos')}catch(e){toast(e.message)}bGuardar.disabled=false});
  const acciones=dE('div',{class:'doc-acc doc-acc-res'},
    dBtn('Copiar','sec',()=>docCopiar(estado.editando?area.value:estado.texto)),
    dBtn('Descargar Word','sec',ev=>docDescargarWord(doc.id,ev.currentTarget)),
    bEditar,dBtn('Editar y regenerar','sec',()=>docRegenerar(doc)),bGuardar);
  const res=dE('section',{class:'doc-res doc-bloque','aria-label':'Borrador generado'},
    dE('p',{class:'doc-aviso',text:doc.borrador_funcionario?'Proyecto generado por IA para revisión del funcionario. No es una providencia.':'Borrador generado por IA. Revísalo completo antes de usarlo.'}),
    titulo,acciones,cuerpo,area);
  if(doc.verificar&&doc.verificar.length)res.appendChild(dE('div',{class:'doc-verif'},dE('h4',{text:'Datos que debes completar o verificar ('+doc.verificar.length+')'}),
    dE('ul',null,...doc.verificar.map(v=>dE('li',{text:v})))));
  if(doc.advertencias&&doc.advertencias.length)res.appendChild(dE('div',{class:'doc-adv'},dE('h4',{text:'Advertencias'}),
    dE('ul',null,...doc.advertencias.map(v=>dE('li',{text:v})))));
  if(doc.fuentes&&doc.fuentes.length&&typeof pintarFuentes==='function'){const w=dE('div',null,dE('div',{class:'bd'}));pintarFuentes(w,doc.fuentes);res.appendChild(w)}
  cont.appendChild(res);
  if(opc&&opc.nuevo)toast('Borrador listo y guardado en Mis documentos');
  res.scrollIntoView({behavior:'smooth',block:'start'});titulo.focus({preventScroll:true});
}
function docRegenerar(doc){
  if(doc.origen==='documento'&&doc.tipo){docAbrirTipo(doc.tipo,doc.campos||{});return}
  if(doc.origen==='flujo'&&doc.tipo&&doc.tipo.startsWith('flujo:')){docTab('flujos');docAbrirFlujo(doc.tipo.slice(6),doc.campos||{});return}
  if(doc.origen==='asistente'){docTab('asistente');const t=document.getElementById('doc-tarea');if(t){t.value=(doc.campos&&doc.campos.tarea)||'';t.focus()}return}
  toast('Este documento no se puede regenerar automáticamente.');
}

// --------------------------------------------------------------------------- Flujos --
function docFlujosVista(){
  const p=docPanel('flujos');if(p.dataset.listo)return DOC.flujosP;p.dataset.listo='1';p.textContent='';
  DOC.flujosP=docFlujosCargar(p);return DOC.flujosP}
async function docFlujosCargar(p){
  p.appendChild(dE('p',{class:'doc-intro',text:'Recetas de varios pasos: llenas un formulario una sola vez y PULLEX ejecuta cada paso en orden, usando el resultado del anterior. Cada paso usa 1 consulta.'}));
  const g=dE('div',{class:'doc-grid',id:'doc-flujos'});p.appendChild(g);p.appendChild(dE('div',{id:'doc-flujo-trabajo'}));
  try{const d=await docApi('/api/flujos');DOC.flujos=d.flujos;DOC.maxPasos=d.max_pasos||6;
    d.flujos.forEach(f=>g.appendChild(dE('button',{type:'button',class:'doc-card','data-flujo':f.id,on:{click:()=>docAbrirFlujo(f.id)}},
      dE('span',{class:'doc-card-area',text:f.area+' · '+f.n_pasos+' pasos · '+f.n_pasos+' consultas'}),dE('b',{text:f.nombre}),
      dE('span',{class:'doc-card-d',text:f.descripcion}),
      dE('ol',{class:'doc-mini-pasos'},...f.pasos.map(x=>dE('li',{text:x.titulo}))))))}
  catch(e){delete p.dataset.listo;g.appendChild(dE('p',{class:'doc-vacio',text:e.message}))}
}
function docAbrirFlujo(id,valores){
  const f=(DOC.flujos||[]).find(x=>x.id===id);if(!f){docFlujosVista().then(()=>{if((DOC.flujos||[]).some(x=>x.id===id))docAbrirFlujo(id,valores)});return}
  DOC.flujo=f;document.getElementById('doc-flujos').classList.add('hidden');
  const w=document.getElementById('doc-flujo-trabajo');w.textContent='';
  w.appendChild(dBtn('← Volver a los flujos','sec doc-volver',()=>{w.textContent='';document.getElementById('doc-flujos').classList.remove('hidden');DOC.flujo=null;docSubir()}));
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:f.nombre});
  const form=docFormulario(f.campos,valores||{},'doc-fl');
  const correr=dBtn('Ejecutar los '+f.n_pasos+' pasos','pri',()=>docEjecutarFlujo(form,correr),{id:'doc-flujo-ejecutar'});
  w.appendChild(dE('div',{class:'doc-bloque'},h,dE('p',{class:'doc-desc',text:f.descripcion}),
    dE('ol',{class:'doc-lista'},...f.pasos.map(x=>dE('li',{text:x.titulo})))));
  w.appendChild(dE('form',{class:'doc-bloque doc-form',novalidate:true,on:{submit:ev=>{ev.preventDefault();docEjecutarFlujo(form,correr)}}},
    form.nodo,form.resumen,dE('div',{class:'doc-acc'},correr),
    dE('p',{class:'doc-costo',text:'Usa '+f.n_pasos+' consultas (una por paso). Si un paso falla, no se descuenta y el flujo se detiene.'})));
  w.appendChild(dE('div',{id:'doc-flujo-progreso'}));
  docSubir();h.focus();
}
async function docEjecutarFlujo(form,boton){
  if(DOC.ocupado)return;if(!form.validar())return;
  const f=DOC.flujo;DOC.ocupado=true;boton.disabled=true;
  const cont=document.getElementById('doc-flujo-progreso');
  try{await docCorrerPasos(cont,'/api/flujos/ejecutar',{flujo:f.id,campos:form.leer()},f.pasos.map(x=>x.titulo))}
  catch(e){if(e.errores)form.marcar(e.errores);toast(e.message)}
  boton.disabled=false;DOC.ocupado=false;
}
// Ejecuta pasos por SSE y pinta el progreso: lista de pasos con estado y el texto de cada uno.
async function docCorrerPasos(cont,url,body,titulos){
  cont.textContent='';
  const estado=dE('p',{class:'doc-estado',role:'status','aria-live':'polite',text:'Iniciando…'});
  const lista=dE('ol',{class:'doc-pasos'});const salidas=dE('div',{class:'doc-salidas'});
  const box=dE('section',{class:'doc-bloque doc-progreso','aria-label':'Progreso del trabajo'},estado,lista,salidas);cont.appendChild(box);
  const items={},textos={},bufs={};let docId=null,raf=null;
  const pintarLista=ts=>{lista.textContent='';ts.forEach((t,i)=>{const n=i+1;const li=dE('li',{class:'doc-paso pend','data-n':n},
    dE('span',{class:'doc-paso-est',text:'Pendiente'}),dE('span',{text:t}));items[n]=li;lista.appendChild(li)})};
  const marcar=(n,cls,txt)=>{const li=items[n];if(!li)return;li.className='doc-paso '+cls;li.querySelector('.doc-paso-est').textContent=txt};
  const render=()=>{Object.entries(bufs).forEach(([n,b])=>{if(textos[n])textos[n].innerHTML=md(b)});raf=null};
  pintarLista(titulos||[]);box.scrollIntoView({behavior:'smooth',block:'start'});
  let fin=null;
  await docSSE(url,body,ev=>{
    if(ev.tipo==='inicio'){if(ev.pasos)pintarLista(ev.pasos);estado.textContent='Trabajando: '+ev.total+' pasos.'}
    else if(ev.tipo==='restantes')dRestantes(ev.restantes);
    else if(ev.tipo==='paso'){marcar(ev.n,'curso','En curso');estado.textContent='Paso '+ev.n+': '+ev.titulo+'…';
      const s=dE('section',{class:'doc-salida','data-n':ev.n},dE('h4',{text:'Paso '+ev.n+'. '+ev.titulo}));textos[ev.n]=dE('div',{class:'md'});bufs[ev.n]='';
      s.appendChild(textos[ev.n]);salidas.appendChild(s)}
    else if(ev.tipo==='texto'){bufs[ev.n]=(bufs[ev.n]||'')+ev.texto;if(!raf)raf=requestAnimationFrame(render)}
    else if(ev.tipo==='paso_fin')marcar(ev.n,'ok','Listo');
    else if(ev.tipo==='error'){marcar(ev.n,'mal','Error');salidas.appendChild(dE('p',{class:'doc-error',role:'alert',text:ev.mensaje}))}
    else if(ev.tipo==='documento')docId=ev.id;
    else if(ev.tipo==='fin')fin=ev});
  if(raf)cancelAnimationFrame(raf);render();
  Object.keys(items).forEach(n=>{if(items[n].classList.contains('pend')||items[n].classList.contains('curso'))marcar(+n,'pend','No ejecutado')});
  estado.textContent=fin&&fin.completo?'Listo: todos los pasos terminaron. El resultado quedó en Mis documentos.':
    (fin&&fin.pasos_completados?'Se completaron '+fin.pasos_completados+' pasos; lo producido quedó en Mis documentos.':'No se completó ningún paso.');
  if(docId){box.appendChild(dE('div',{class:'doc-acc'},
    dBtn('Copiar todo','sec',()=>docCopiar(Object.values(bufs).join('\n\n'))),
    dBtn('Descargar Word','sec',ev=>docDescargarWord(docId,ev.currentTarget)),
    dBtn('Abrir en Mis documentos','pri',()=>{docTab('mis');docAbrirMio(docId)})))}
  box.appendChild(dE('p',{class:'doc-costo',text:'Resultado generado por IA: revísalo y verifica normas, términos y cifras antes de usarlo.'}));
}

// ------------------------------------------------------------------------ Asistente --
function docAsistenteVista(){
  const p=docPanel('asistente');p.textContent='';
  const ta=dE('textarea',{id:'doc-tarea',class:'doc-inp',rows:4,maxlength:4000,'aria-describedby':'doc-tarea-ayuda'});
  const err=dE('p',{class:'doc-err hidden',id:'doc-tarea-err'});
  const proponer=dBtn('Proponer un plan','pri',()=>docProponer(ta,err,proponer),{id:'doc-proponer'});
  p.appendChild(dE('div',{class:'doc-bloque'},
    dE('label',{for:'doc-tarea',class:'doc-lb',text:'¿Qué necesitas que PULLEX haga?'}),
    dE('p',{class:'doc-ayuda',id:'doc-tarea-ayuda',text:'Escribe la tarea completa. PULLEX propone un plan de 3 a 6 pasos; lo revisas, lo ajustas y solo entonces se ejecuta. No envía correos ni radica nada: solo produce análisis y borradores.'}),
    ta,err,dE('div',{class:'doc-ejemplos'},dE('span',{text:'Ejemplos:'}),...DOC_EJEMPLOS.map(x=>dBtn(x.length>60?x.slice(0,58)+'…':x,'chip',()=>{ta.value=x;ta.focus()},{title:x}))),
    dE('div',{class:'doc-acc'},proponer),dE('p',{class:'doc-costo',text:'Proponer el plan usa 1 consulta; luego cada paso usa 1 consulta (máximo 6 pasos).'})));
  p.appendChild(dE('div',{id:'doc-plan'}));p.appendChild(dE('div',{id:'doc-asist-progreso'}));
}
async function docProponer(ta,err,boton){
  if(DOC.ocupado)return;const v=ta.value.trim();
  if(v.length<15){ta.setAttribute('aria-invalid','true');err.textContent='Describe la tarea con un poco más de detalle.';err.classList.remove('hidden');
    ta.setAttribute('aria-describedby','doc-tarea-ayuda doc-tarea-err');ta.focus();return}
  ta.removeAttribute('aria-invalid');err.classList.add('hidden');ta.setAttribute('aria-describedby','doc-tarea-ayuda');
  DOC.ocupado=true;boton.disabled=true;const t0=boton.textContent;boton.textContent='Pensando el plan…';
  try{const d=await docApi('/api/asistente/tarea',{body:{tarea:v}});DOC.plan=d;document.getElementById('doc-asist-progreso').textContent='';docPintarPlan()}
  catch(e){toast(e.message)}
  boton.disabled=false;boton.textContent=t0;DOC.ocupado=false;
}
function docPintarPlan(){
  const c=document.getElementById('doc-plan');c.textContent='';const plan=DOC.plan;if(!plan)return;
  const lista=dE('ol',{class:'doc-plan-pasos'});
  const costo=dE('p',{class:'doc-costo','aria-live':'polite'});
  const actualizar=()=>{const n=lista.children.length;costo.textContent='Ejecutar usa '+n+(n===1?' consulta':' consultas')+' (una por paso).';
    agregar.disabled=n>=DOC.maxPasos;[...lista.children].forEach((li,i)=>{li.querySelector('.doc-plan-n').textContent='Paso '+(i+1);
      li.querySelector('.doc-plan-quitar').disabled=lista.children.length<=1})};
  const fila=(p)=>{const k=Math.random().toString(36).slice(2,8);
    const t=dE('input',{type:'text',class:'doc-inp doc-plan-t',id:'pt-'+k,maxlength:120,value:p.titulo||''});
    const i=dE('textarea',{class:'doc-inp doc-plan-i',id:'pi-'+k,rows:2,maxlength:1500});i.value=p.instruccion||'';
    const li=dE('li',{class:'doc-plan-paso'},dE('div',{class:'doc-plan-cab'},dE('b',{class:'doc-plan-n'}),
      dBtn('Quitar','sec doc-plan-quitar',()=>{li.remove();actualizar()})),
      dE('label',{for:'pt-'+k,text:'Título del paso'}),t,dE('label',{for:'pi-'+k,text:'Qué debe hacer'}),i);return li};
  plan.pasos.forEach(p=>lista.appendChild(fila(p)));
  const agregar=dBtn('Agregar paso','sec',()=>{if(lista.children.length>=DOC.maxPasos)return;const li=fila({titulo:'',instruccion:''});lista.appendChild(li);actualizar();li.querySelector('input').focus()});
  const ejecutar=dBtn('Confirmar y ejecutar','pri',()=>docEjecutarPlan(lista,ejecutar),{id:'doc-ejecutar-plan'});
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:'Plan propuesto: '+plan.titulo});
  c.appendChild(dE('section',{class:'doc-bloque','aria-label':'Plan propuesto'},h,
    dE('p',{class:'doc-intro',text:'Revisa el plan. Puedes cambiar títulos e instrucciones, quitar pasos o agregar hasta '+DOC.maxPasos+'. Nada se ejecuta hasta que confirmes.'}),
    lista,dE('div',{class:'doc-acc'},agregar,dBtn('Descartar','sec',()=>{DOC.plan=null;c.textContent=''}),ejecutar),costo));
  actualizar();h.focus();
}
async function docEjecutarPlan(lista,boton){
  if(DOC.ocupado)return;
  const pasos=[...lista.children].map(li=>({titulo:li.querySelector('.doc-plan-t').value.trim(),instruccion:li.querySelector('.doc-plan-i').value.trim()}));
  const malo=[...lista.children].find((li,i)=>!pasos[i].titulo||!pasos[i].instruccion);
  if(malo){const x=!malo.querySelector('.doc-plan-t').value.trim()?malo.querySelector('.doc-plan-t'):malo.querySelector('.doc-plan-i');
    x.setAttribute('aria-invalid','true');x.addEventListener('input',()=>x.removeAttribute('aria-invalid'),{once:true});x.focus();toast('Cada paso necesita un título y una instrucción.');return}
  DOC.ocupado=true;boton.disabled=true;
  const cont=document.getElementById('doc-asist-progreso');
  try{await docCorrerPasos(cont,'/api/asistente/ejecutar',{id:DOC.plan.id,pasos},pasos.map(p=>p.titulo));
    document.getElementById('doc-plan').querySelectorAll('input,textarea,button').forEach(x=>x.disabled=true)}
  catch(e){toast(e.message);boton.disabled=false}
  DOC.ocupado=false;
}

// ------------------------------------------------------------------- Mis documentos --
const DOC_ORIGEN={documento:'Escrito',flujo:'Flujo',asistente:'Asistente'};
async function docCargarMis(){
  const p=docPanel('mis');
  if(!p.querySelector('#doc-mis-lista')){p.textContent='';p.appendChild(dE('div',{id:'doc-mis-lista',class:'doc-mis'}));p.appendChild(dE('div',{id:'doc-mis-abierto'}))}
  const l=document.getElementById('doc-mis-lista');
  try{const d=await docApi('/api/documentos/mis');DOC.mis=d.documentos;l.textContent='';
    if(!d.documentos.length){l.appendChild(dE('p',{class:'doc-vacio',text:'Aún no tienes documentos. Cuando generes un escrito, ejecutes un flujo o uses el asistente, el resultado quedará guardado aquí.'}));return}
    l.appendChild(dE('p',{class:'doc-n',text:d.documentos.length+(d.documentos.length===1?' documento guardado':' documentos guardados')}));
    const ul=dE('ul',{class:'doc-mis-ul'});
    d.documentos.forEach(x=>{const li=dE('li',{class:'doc-mis-f','data-id':x.id},
      dE('div',{class:'doc-mis-t'},dE('b',{text:x.titulo||'Documento'}),
        dE('span',{text:(DOC_ORIGEN[x.origen]||'Documento')+(x.tipo_nombre?' · '+x.tipo_nombre:'')+' · '+docFecha(x.actualizado)})),
      dE('div',{class:'doc-acc'},dBtn('Abrir','sec',()=>docAbrirMio(x.id)),dBtn('Word','sec',ev=>docDescargarWord(x.id,ev.currentTarget)),
        dBtn('Borrar','sec peligro',()=>docConfirmarBorrar(li,x))));ul.appendChild(li)});
    l.appendChild(ul)}
  catch(e){l.textContent='';l.appendChild(dE('p',{class:'doc-vacio',text:e.message}))}
}
function docConfirmarBorrar(li,x){
  const previo=li.querySelector('.doc-conf');if(previo)return;
  const si=dBtn('Sí, borrar','peligro pri',async()=>{si.disabled=true;try{await docApi('/api/documentos/'+x.id,{method:'DELETE'});toast('Documento borrado');
    const ab=document.getElementById('doc-mis-abierto');if(ab&&ab.dataset.id===String(x.id))ab.textContent='';docCargarMis()}catch(e){toast(e.message);si.disabled=false}});
  const conf=dE('div',{class:'doc-conf',role:'group','aria-label':'Confirmar borrado'},dE('span',{text:'¿Borrar «'+(x.titulo||'Documento')+'»? No se puede deshacer.'}),
    dBtn('Cancelar','sec',()=>conf.remove()),si);
  li.appendChild(conf);si.focus();
}
async function docAbrirMio(id){
  if(DOC.tab!=='mis')docTab('mis');
  try{const d=await docApi('/api/documentos/'+encodeURIComponent(id));const c=document.getElementById('doc-mis-abierto')||docPanel('mis');
    c.textContent='';c.dataset.id=String(id);docMostrarResultado(c,d)}
  catch(e){toast(e.message)}
}
