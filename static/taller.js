// =========================================================================================
// PULLEX Academia — Academia de escritos: pestañas del Modular Lab (Casos · Taller de escritos ·
// Cómo contestar). Se carga después de app.js y usa sus utilidades globales ($, api, md, toast, ver,
// mlInit, mlElegir, PERFIL, CAMINO). Sin JavaScript en línea: todo con addEventListener. Lo que viene
// del servidor o del modelo se pinta con textContent; solo el escrito modelo (Markdown) pasa por md()
// (marked + DOMPurify).
// =========================================================================================
const TL={tab:'casos',opc:null,tipo:'tutela',nivel:'basico',fuente:'banco',esc:null,ev:null,timer:null,
  tallerListo:false,comoListo:false,leccion:'metodo',paso:0,ocupado:false};
const TL_TABS=['casos','taller','como'];
const TL_LS='pullex.taller.borrador.';

// ------------------------------------------------------------------------- utilidades --
function tE(tag,attrs,...hijos){const e=document.createElement(tag);
  if(attrs)for(const [k,v] of Object.entries(attrs)){if(v==null||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;
    else if(k==='on')Object.entries(v).forEach(([ev,fn])=>e.addEventListener(ev,fn));
    else e.setAttribute(k,v===true?'':v)}
  hijos.flat().forEach(h=>{if(h==null||h===false)return;e.appendChild(typeof h==='string'?document.createTextNode(h):h)});
  return e}
function tBtn(txt,cls,fn,attrs){return tE('button',{type:'button',class:cls||'bsec',on:{click:fn},...(attrs||{})},txt)}
function tParrafos(texto){return String(texto||'').split(/\n\s*\n/).map(p=>p.trim()).filter(Boolean).map(p=>tE('p',null,p))}
function tlLeer(id){try{const v=localStorage.getItem(TL_LS+id);return v?JSON.parse(v):null}catch(e){return null}}
function tlEscribir(id,d){try{localStorage.setItem(TL_LS+id,JSON.stringify(d));return true}catch(e){return false}}
function tlHora(){try{return new Date().toLocaleTimeString('es-CO',{hour:'numeric',minute:'2-digit'})}catch(e){return ''}}

// ----------------------------------------------------------------------------- pestañas --
function tlCasosWrap(){return document.querySelector('#v-modular > .wrap:not(.tl-panel)')}
function tlPanel(id){return id==='casos'?tlCasosWrap():document.getElementById('tl-'+id)}
function tlTab(id,opts){
  if(!TL_TABS.includes(id))return;TL.tab=id;
  TL_TABS.forEach(t=>{const b=document.getElementById('tl-tab-'+t),p=tlPanel(t);const on=t===id;
    if(b){b.classList.toggle('on',on);b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1}
    if(p)p.classList.toggle('hidden',!on)});
  if(id==='taller')tlTallerInit();
  if(id==='como')tlComoInit();
  if(id==='casos'&&typeof mlInit==='function')mlInit();
  if(opts&&opts.foco){const b=document.getElementById('tl-tab-'+id);if(b)b.focus()}
  if(!(opts&&opts.sinScroll)){const m=document.querySelector('main');if(m)m.scrollTop=0}
}
function tlTabTeclas(ev){
  const i=TL_TABS.indexOf(TL.tab);let j=null;
  if(ev.key==='ArrowRight')j=(i+1)%TL_TABS.length;else if(ev.key==='ArrowLeft')j=(i+TL_TABS.length-1)%TL_TABS.length;
  else if(ev.key==='Home')j=0;else if(ev.key==='End')j=TL_TABS.length-1;
  if(j===null)return;ev.preventDefault();tlTab(TL_TABS[j],{foco:true});
}
// Lleva a una pestaña desde cualquier parte (Inicio, lecciones). `o` puede traer tipo y nivel (Taller) o área y nivel (Casos).
async function tlIr(tab,o){
  o=o||{};
  if(typeof ver==='function'&&!document.getElementById('v-modular').classList.contains('on'))ver('modular');
  tlTab(tab);
  if(tab==='taller'){await tlTallerInit();if(o.tipo)tlElegirTipo(o.tipo);if(o.nivel)tlElegirNivel(o.nivel);
    tlNuevo();const t=TL.opc&&TL.opc.tipos.find(x=>x.id===TL.tipo);
    if(o.tipo&&t)toast('Elegí «'+t.nombre+'». Pulsa «Empezar a redactar».')}
  if(tab==='casos'&&o.area&&typeof mlInit==='function'){await mlInit();if(typeof mlElegir==='function')mlElegir(o.area,o.nivel)}
}

// ------------------------------------------------------------------------ Taller: arranque --
async function tlTallerInit(){
  const raiz=document.getElementById('tl-taller');if(!raiz)return;
  if(TL.tallerListo){tlCargarMis();return}
  TL.tallerListo=true;
  raiz.appendChild(tE('div',{class:'cab-vista'},tE('p',{class:'eyebrow claim',text:'PULLEX Academia'}),
    tE('h2',{class:'display',text:'Taller de escritos'}),
    tE('p',{text:'Practica la redacción de los escritos que más se piden: PULLEX te da un caso ficticio y la lista de partes obligatorias; tú redactas y recibes una evaluación con rúbrica, lo que falta, lo que sobra y cómo mejorar los fragmentos débiles.'})));
  const cfg=tE('div',{class:'panel',id:'tl-config'},tE('h3',{text:'Elige el escrito'}),
    tE('div',{class:'lb2',id:'tl-lb-tipo',text:'Tipo de escrito'}),
    tE('div',{class:'tl-tipos',id:'tl-tipos',role:'group','aria-labelledby':'tl-lb-tipo'},tE('div',{class:'skel'})),
    tE('div',{class:'lb2',id:'tl-lb-nivel',text:'Nivel'}),
    tE('div',{class:'opc',id:'tl-niveles',role:'group','aria-labelledby':'tl-lb-nivel'}),
    tE('div',{class:'lb2',id:'tl-lb-fuente',text:'Escenario'}),
    tE('div',{class:'tl-fuentes',id:'tl-fuentes',role:'group','aria-labelledby':'tl-lb-fuente'}),
    tE('div',{class:'ml-acc'},tBtn('Empezar a redactar','bpri',()=>tlEmpezar(),{id:'tl-empezar'})),
    tE('p',{class:'ml-costo',text:'Los escenarios del banco no gastan consultas. Un escenario nuevo con IA y cada evaluación usan una consulta (si algo falla, no se descuenta). El escrito modelo se abre después de tu primer intento evaluado.'}));
  raiz.appendChild(cfg);
  raiz.appendChild(tE('div',{class:'panel hidden',id:'tl-esc'}));
  raiz.appendChild(tE('div',{class:'panel hidden',id:'tl-eval','aria-live':'polite'}));
  raiz.appendChild(tE('div',{class:'panel hidden',id:'tl-modelo'}));
  raiz.appendChild(tE('div',{class:'panel',id:'tl-mis'},tE('h3',{text:'Tus escritos'}),
    tE('div',{id:'tl-mis-cuerpo',class:'vacio',text:'Cuando empieces un escenario, aquí quedará para retomarlo.'})));
  try{TL.opc=await api('/api/taller/opciones')}catch(e){toast(e.message);TL.tallerListo=false;raiz.textContent='';return}
  const tipos=document.getElementById('tl-tipos');tipos.textContent='';
  TL.opc.tipos.forEach(t=>tipos.appendChild(tE('button',{type:'button',class:'tl-tipo','data-tipo':t.id,
    'aria-pressed':String(t.id===TL.tipo),on:{click:()=>tlElegirTipo(t.id)}},tE('b',null,t.nombre),tE('span',null,t.area))));
  const niv=document.getElementById('tl-niveles');
  TL.opc.niveles.forEach(n=>niv.appendChild(tE('button',{type:'button','data-nivel':n.id,class:n.id===TL.nivel?'on':null,
    'aria-pressed':String(n.id===TL.nivel),title:n.descripcion,on:{click:()=>tlElegirNivel(n.id)}},n.nombre)));
  const fu=document.getElementById('tl-fuentes');
  [['banco','Del banco curado','Revisado con criterio conservador · gratis'],['ia','Nuevo con IA','Un caso distinto cada vez · 1 consulta']]
    .forEach(([id,t,d])=>fu.appendChild(tE('button',{type:'button',class:'tl-fuente','data-fuente':id,'aria-pressed':String(id===TL.fuente),
      on:{click:()=>tlElegirFuente(id)}},tE('b',null,t),tE('span',null,d))));
  tlCargarMis();
}
function tlMarcar(sel,attr,val){document.querySelectorAll(sel).forEach(b=>{const on=b.dataset[attr]===val;
  b.setAttribute('aria-pressed',String(on));b.classList.toggle('on',on)})}
function tlElegirTipo(id){TL.tipo=id;tlMarcar('#tl-tipos .tl-tipo','tipo',id)}
function tlElegirNivel(id){TL.nivel=id;tlMarcar('#tl-niveles button','nivel',id)}
function tlElegirFuente(id){TL.fuente=id;tlMarcar('#tl-fuentes .tl-fuente','fuente',id)}
function tlOcupado(b,t){if(!b)return ()=>{};const o=b.textContent;b.disabled=true;b.textContent=t;return ()=>{b.disabled=false;b.textContent=o}}

async function tlEmpezar(){
  if(TL.ocupado)return;TL.ocupado=true;
  const listo=tlOcupado(document.getElementById('tl-empezar'),TL.fuente==='ia'?'Creando el escenario…':'Abriendo…');
  try{tlMostrarEscenario(await api('/api/taller/escenario',{body:{tipo:TL.tipo,nivel:TL.nivel,fuente:TL.fuente}}));tlCargarMis()}
  catch(e){toast(e.message)}
  listo();TL.ocupado=false;
}
async function tlAbrir(id){
  try{tlMostrarEscenario(await api('/api/taller/escenario/'+encodeURIComponent(id)))}catch(e){toast(e.message)}
}
function tlNuevo(){['tl-esc','tl-eval','tl-modelo'].forEach(i=>{const p=document.getElementById(i);if(p)p.classList.add('hidden')});
  TL.esc=null;const c=document.getElementById('tl-config');if(c)c.scrollIntoView({behavior:'smooth',block:'start'})}

// ------------------------------------------------------------------------ Taller: escenario --
function tlMostrarEscenario(e){
  TL.esc=e;TL.ev=null;
  const p=document.getElementById('tl-esc');p.textContent='';
  const meta=tE('div',{class:'ml-meta'},tE('span',{class:'tag oro',text:e.tipo_nombre}),tE('span',{class:'tag',text:e.nivel_nombre}),
    tE('span',{class:'tag',text:e.curado?'Banco curado':'Generado con IA'}),
    e.revision_humana?tE('span',{class:'tag',text:'Pendiente de revisión humana'}):null,
    e.intentos?tE('span',{class:'tag',text:e.intentos+(e.intentos===1?' intento':' intentos')+(e.mejor!=null?' · mejor '+e.mejor+'/100':'')}):null);
  p.appendChild(meta);
  p.appendChild(tE('h3',{class:'ml-titulo',id:'tl-titulo',tabindex:'-1',text:e.titulo}));
  p.appendChild(tE('div',{class:'lb2',text:'Hechos (ficticios)'}));
  p.appendChild(tE('div',{class:'tl-hechos'},tParrafos(e.hechos)));
  p.appendChild(tE('div',{class:'tl-instr'},tE('span',{class:'eyebrow',text:'Tu tarea'}),tE('p',{id:'tl-instruccion',text:e.instruccion})));
  // Lista de comprobación: autoevaluación del estudiante (se guarda con el borrador); tras evaluar, PULLEX marca cada parte.
  const borr=tlLeer(e.id)||{};const marcas=new Set(borr.marcas||[]);
  const lista=tE('ul',{class:'tl-lista',id:'tl-lista'});
  e.lista.forEach(it=>{const idc='tl-chk-'+it.id;
    const chk=tE('input',{type:'checkbox',id:idc,'data-parte':it.id,on:{change:tlGuardarPronto}});chk.checked=marcas.has(it.id);
    lista.appendChild(tE('li',{'data-parte':it.id},chk,tE('label',{for:idc},tE('b',null,it.parte),tE('span',null,it.ayuda)),
      tE('em',{class:'tl-res','aria-live':'polite'})))});
  p.appendChild(tE('details',{class:'metodo tl-det',open:true},tE('summary',null,'Lista de comprobación · '+e.lista.length+' partes obligatorias'),
    tE('p',{class:'tl-nota',text:'Márcalas a medida que las escribas. Al evaluar, PULLEX te dirá cuáles encontró.'}),lista));
  const rub=tE('ul',{class:'tl-rub-lista'});
  e.rubrica.forEach(r=>rub.appendChild(tE('li',null,tE('span',null,r.nombre),tE('b',null,r.max+' pts'))));
  p.appendChild(tE('details',{class:'metodo tl-det'},tE('summary',null,'Cómo se evalúa (rúbrica de 100 puntos)'),rub,
    e.rubrica_nota?tE('p',{class:'tl-nota',text:e.rubrica_nota}):null));
  p.appendChild(tE('label',{class:'lb2 tl-lb',for:'tl-texto',text:'Tu escrito'}));
  const ta=tE('textarea',{id:'tl-texto',class:'inp tl-editor',rows:'18',spellcheck:'true','aria-describedby':'tl-cuenta tl-guardado',
    placeholder:'Redacta aquí el escrito completo, como lo radicarías: destinatario, partes, hechos numerados, fundamentos, peticiones, pruebas, notificaciones y firma.',
    on:{input:()=>{tlContar();tlGuardarPronto()}}});
  ta.value=borr.texto||'';p.appendChild(ta);
  p.appendChild(tE('div',{class:'tl-pie-editor'},tE('span',{id:'tl-guardado',class:'tl-guardado','aria-live':'polite'},
    borr.texto?'Borrador recuperado de este navegador':''),tE('span',{id:'tl-cuenta',class:'ml-cuenta'})));
  const bModelo=tBtn('Ver escrito modelo','bsec',()=>tlModelo(),{id:'tl-btn-modelo','aria-describedby':'tl-modelo-ayuda'});
  p.appendChild(tE('div',{class:'ml-acc'},tBtn('Evaluar mi escrito','bpri',()=>tlEvaluar(),{id:'tl-btn-eval'}),bModelo,
    tBtn('Otro escenario','bghost',()=>tlNuevo())));
  p.appendChild(tE('p',{class:'ml-costo',id:'tl-modelo-ayuda'}));
  tlEstadoModelo();tlContar();
  ['tl-eval','tl-modelo'].forEach(i=>document.getElementById(i).classList.add('hidden'));
  p.classList.remove('hidden');
  if(e.ultima_evaluacion)tlMostrarEval(e.ultima_evaluacion,true);
  p.scrollIntoView({behavior:'smooth',block:'start'});
  const t=document.getElementById('tl-titulo');if(t)t.focus({preventScroll:true});
}
function tlEstadoModelo(){
  const b=document.getElementById('tl-btn-modelo'),a=document.getElementById('tl-modelo-ayuda');if(!b||!TL.esc)return;
  const ok=!!TL.esc.modelo_disponible;b.disabled=!ok;
  a.textContent=ok?'Evaluar usa una consulta. El escrito modelo no gasta consultas.'
    :'Evaluar usa una consulta. El escrito modelo se abre después de evaluar tu primer intento: primero inténtalo tú.';
}
function tlContar(){
  const ta=document.getElementById('tl-texto');if(!ta)return;const v=ta.value;
  const pal=(v.trim().match(/\S+/g)||[]).length;const min=(TL.opc&&TL.opc.min_caracteres)||250;
  document.getElementById('tl-cuenta').textContent=pal+(pal===1?' palabra':' palabras')+' · '+v.length.toLocaleString('es-CO')+' caracteres'+
    (v.trim().length<min?' · mínimo '+min:'');
}
function tlGuardarPronto(){clearTimeout(TL.timer);TL.timer=setTimeout(tlGuardar,600)}
function tlGuardar(){
  if(!TL.esc)return;const ta=document.getElementById('tl-texto');if(!ta)return;
  const marcas=[...document.querySelectorAll('#tl-lista input:checked')].map(x=>x.dataset.parte);
  const ok=tlEscribir(TL.esc.id,{texto:ta.value,marcas,t:Date.now()});
  const g=document.getElementById('tl-guardado');
  if(g)g.textContent=ok?'Borrador guardado en este navegador · '+tlHora():'No se pudo guardar el borrador en este navegador (modo privado o almacenamiento lleno).';
}

// ------------------------------------------------------------------------ Taller: evaluación --
async function tlEvaluar(){
  if(!TL.esc||TL.ocupado)return;
  const ta=document.getElementById('tl-texto');const texto=ta.value.trim();const min=(TL.opc&&TL.opc.min_caracteres)||250;
  if(texto.length<min){toast('Redacta al menos las partes principales antes de evaluar (mínimo '+min+' caracteres).');ta.focus();return}
  tlGuardar();TL.ocupado=true;const listo=tlOcupado(document.getElementById('tl-btn-eval'),'Evaluando…');
  try{const ev=await api('/api/taller/evaluar',{body:{escenario_id:TL.esc.id,texto}});
    TL.esc.modelo_disponible=true;TL.esc.intentos=(TL.esc.intentos||0)+1;tlEstadoModelo();tlMostrarEval(ev);tlCargarMis()}
  catch(e){toast(e.message)}
  listo();TL.ocupado=false;tlEstadoModelo();
}
function tlCaja(titulo,clase,items,vacio){
  const box=tE('div',{class:'ev-box '+clase},tE('h4',null,titulo));const ul=tE('ul');
  (items&&items.length?items:[vacio||'—']).forEach(t=>ul.appendChild(tE('li',null,t)));box.appendChild(ul);return box}
function tlMostrarEval(ev,previa){
  TL.ev=ev;const p=document.getElementById('tl-eval');p.textContent='';
  p.appendChild(tE('h3',{tabindex:'-1',id:'tl-eval-h'},previa?'Tu última evaluación':'Tu evaluación'));
  const tot=tE('div',{class:'ev-total'},String(ev.total),tE('small',null,' / 100'));
  p.appendChild(tE('div',{class:'ev-cab'},tot,tE('div',{class:'ev-com',text:ev.comentario||''})));
  const rub=tE('div',{class:'rub'});
  ev.rubrica.forEach(r=>{const pct=Math.round(100*r.puntaje/r.max);const i=tE('i',{class:pct<60?'bajo':null});i.style.width=pct+'%';
    rub.appendChild(tE('div',{class:'r'},tE('span',null,r.nombre),tE('div',{class:'bar',role:'img','aria-label':r.nombre+': '+r.puntaje+' de '+r.max},i),
      tE('span',{class:'n',text:r.puntaje+'/'+r.max})))});
  p.appendChild(rub);
  const g=tE('div',{class:'ev-grid'});
  g.appendChild(tlCaja('Partes que faltan','falta',ev.faltan,'Ninguna: incluiste las partes obligatorias.'));
  g.appendChild(tlCaja('Errores de forma','norma',ev.errores_forma,'No encontramos errores de forma.'));
  g.appendChild(tlCaja('Lo que sobra','mejora',ev.sobra,'Nada sobra.'));
  g.appendChild(tlCaja('Conceptos para reforzar','bien',ev.conceptos_debiles,'Ninguno señalado.'));
  p.appendChild(g);
  if(ev.mejoras&&ev.mejoras.length){
    p.appendChild(tE('div',{class:'lb2',text:'Fragmentos que puedes mejorar'}));
    ev.mejoras.forEach((m,i)=>p.appendChild(tE('div',{class:'tl-mejora'},
      m.original?tE('div',{class:'tl-antes'},tE('span',{class:'eyebrow',text:'Tu versión'}),tE('p',null,m.original)):null,
      tE('div',{class:'tl-despues'},tE('span',{class:'eyebrow',text:'Versión mejorada'}),tE('p',null,m.mejorada)),
      m.por_que?tE('p',{class:'tl-porque'},tE('b',null,'Por qué: '),m.por_que):null)));
  }
  // La lista de comprobación del escenario se marca con lo que encontró la evaluación.
  (ev.lista||[]).forEach(it=>{const li=document.querySelector('#tl-lista li[data-parte="'+it.id+'"]');if(!li)return;
    li.classList.toggle('ok',it.presente);li.classList.toggle('falta',!it.presente);
    li.querySelector('.tl-res').textContent=it.presente?'PULLEX la encontró':'Falta o está incompleta'});
  if(ev.conocimiento&&ev.conocimiento.length){
    const txt={fallo:'por reforzar: vuelve en tus repasos mañana',acierto:'bien aplicado: el próximo repaso se aleja',visto:'registrado en tu mapa'};
    const ul=tE('ul');ev.conocimiento.forEach(c=>ul.appendChild(tE('li',null,tE('b',null,c.nombre),' — '+(txt[c.resultado]||''))));
    p.appendChild(tE('div',{class:'aprendido'},tE('h4',null,'Tu mapa se actualizó'),ul,tE('button',{type:'button',on:{click:()=>ver('mapa')}},'Ver mi mapa')))}
  p.appendChild(tE('div',{class:'ml-acc'},tBtn('Ver escrito modelo','bsec',()=>tlModelo()),
    tBtn('Corregir y volver a evaluar','bsec',()=>{const t=document.getElementById('tl-texto');if(t){t.scrollIntoView({behavior:'smooth',block:'center'});t.focus({preventScroll:true})}}),
    tBtn('Otro escenario','bpri',()=>tlNuevo())));
  p.appendChild(tE('p',{class:'nota-ia',text:'Evaluación orientativa generada por IA para practicar. No reemplaza la corrección de un docente; verifica cada norma en la fuente oficial.'}));
  p.classList.remove('hidden');
  if(!previa){p.scrollIntoView({behavior:'smooth',block:'start'});const h=document.getElementById('tl-eval-h');if(h)h.focus({preventScroll:true})}
}
async function tlModelo(){
  if(!TL.esc)return;
  if(!TL.esc.modelo_disponible){toast('Primero redacta tu versión y evalúala: el escrito modelo se abre después de intentarlo.');return}
  const p=document.getElementById('tl-modelo');p.textContent='';
  p.appendChild(tE('h3',{text:'Escrito modelo'}));p.appendChild(tE('div',{class:'skel'}));p.appendChild(tE('div',{class:'skel'}));
  p.classList.remove('hidden');p.scrollIntoView({behavior:'smooth',block:'start'});
  try{const d=await api('/api/taller/modelo',{body:{escenario_id:TL.esc.id}});
    p.textContent='';
    p.appendChild(tE('h3',{tabindex:'-1',id:'tl-modelo-h',text:'Escrito modelo'}));
    p.appendChild(tE('p',{class:'tl-nota',text:'Compáralo con el tuyo parte por parte, con la lista de comprobación al lado. Hay más de una forma correcta de redactar un escrito.'}));
    const cuerpo=tE('div',{class:'md tl-modelo-texto'});cuerpo.innerHTML=md(d.texto);p.appendChild(cuerpo);
    p.appendChild(tE('p',{class:'nota-ia',text:'Modelo de estudio generado por IA sobre hechos ficticios. No es un formato oficial: verifica la vigencia de cada norma antes de usarlo como referencia.'}));
    TL.esc.tiene_modelo=true;const h=document.getElementById('tl-modelo-h');if(h)h.focus({preventScroll:true});
  }catch(e){p.classList.add('hidden');toast(e.message)}
}
async function tlCargarMis(){
  const c=document.getElementById('tl-mis-cuerpo');if(!c)return;
  let d;try{d=await api('/api/taller/mis')}catch(e){return}
  if(!d.escenarios.length){c.className='vacio';return}
  c.className='rep-lista';c.textContent='';
  d.escenarios.slice(0,8).forEach(x=>c.appendChild(tE('div',{class:'rep'},
    tE('div',{class:'t'},tE('b',null,x.titulo),tE('span',null,x.tipo_nombre+' · '+x.nivel_nombre+' · '+
      (x.intentos?x.intentos+(x.intentos===1?' intento':' intentos')+(x.mejor!=null?' · mejor '+x.mejor+'/100':''):'sin evaluar'))),
    tE('div',{class:'racc'},tBtn(x.intentos?'Abrir':'Continuar','bsec',()=>tlAbrir(x.id))))));
}

// ---------------------------------------------------------------- Inicio: «Practica un escrito» --
async function tlTarjetaInicio(){
  const t=document.getElementById('tablero');if(!t||typeof CAMINO==='undefined'||CAMINO!=='aprender')return;
  let r;try{r=await api('/api/taller/recomendacion')}catch(e){return}
  const vieja=t.querySelector('.tcard[data-taller]');if(vieja)vieja.remove();
  const rec=r&&r.recomendacion;if(!rec||CAMINO!=='aprender')return;
  const nombreNivel=(typeof NOMBRE_NIVEL!=='undefined'&&NOMBRE_NIVEL[rec.nivel])||rec.nivel;
  t.appendChild(tE('div',{class:'tcard','data-taller':'1'},tE('div',{class:'k',text:'Practica un escrito'}),
    tE('div',{class:'v',text:rec.tipo_nombre}),tE('div',{class:'s',text:rec.motivo+' Nivel: '+nombreNivel+'.'}),
    tBtn('Ir al taller','bsec',()=>tlIr('taller',{tipo:rec.tipo,nivel:rec.nivel}))));
  t.classList.remove('hidden');
}

// ======================================================================== Cómo contestar --
// Lecciones estáticas. Las normas se nombran con «verificar vigencia» y sin números de sentencias.
const TL_LECCIONES=[
  {id:'metodo',n:'1',t:'Cómo contestar un modular',d:'El método PULLEX en 8 pasos, con un caso resuelto.',min:'6 min'},
  {id:'hechos',n:'2',t:'Hechos relevantes y distractores',d:'Lee el caso como lo lee quien lo calificará.',min:'4 min'},
  {id:'conectores',n:'3',t:'Conectores y párrafos',d:'El párrafo argumentativo y el conector que lo sostiene.',min:'4 min'},
  {id:'estructura',n:'4',t:'Estructura de los escritos',d:'Esqueleto de tutela, petición, demanda y recurso.',min:'5 min'},
  {id:'errores',n:'5',t:'Errores que hacen perder puntos',d:'Lo que más resta en una evaluación, y cómo evitarlo.',min:'3 min'}];

const TL_CASO_METODO='Valeria Rojas trabajó tres años, de 2022 a 2025, como recepcionista de la Clínica San Rafael (ficticia), en Cali, con contratos de «prestación de servicios» de seis meses que se renovaban sin pausa. Cumplía un horario de 7 a. m. a 3 p. m. fijado por la coordinadora, recibía órdenes por un grupo de chat, le llamaban la atención si llegaba tarde y le pagaban $1.900.000 cada mes contra una «cuenta de cobro». En las noches estudiaba enfermería. La clínica tiene sedes en Cali y en Palmira. Cuando no le renovaron el contrato, no le pagaron prestaciones. Pregunta del examen: ¿tiene Valeria derecho a reclamar prestaciones sociales?';
const TL_PASOS=[
  {l:'P',t:'Problema',q:'¿Qué pregunta jurídica hay que resolver?',
   c:'Si entre Valeria y la clínica existió un contrato de trabajo, pese a que firmaron contratos de prestación de servicios, y si por eso tiene derecho a prestaciones sociales.',
   e:'Responder «sí tiene derecho» sin formular el problema: el calificador busca que nombres la tensión (forma del contrato frente a la realidad).'},
  {l:'U',t:'Ubicación normativa',q:'¿Qué rama, código e institución intervienen?',
   c:'Derecho laboral individual. Constitución (primacía de la realidad sobre las formas, art. 53) y Código Sustantivo del Trabajo (elementos del contrato y presunción). Verifica la vigencia en la fuente oficial.',
   e:'Saltar al Código Civil porque el contrato «dice» prestación de servicios.'},
  {l:'L',t:'Lectura de los hechos',q:'¿Cuáles hechos importan y cuáles distraen?',
   c:'Relevantes: horario fijado por la coordinadora, órdenes por chat, llamados de atención, pago mensual fijo, tres años continuos. Distractores: que estudie enfermería en la noche y que la clínica tenga dos sedes.',
   e:'Copiar todos los hechos en la respuesta. Úsalos: cada hecho relevante debe servir a un requisito.'},
  {l:'L',t:'Legalidad',q:'¿Qué norma vigente regula el asunto y qué exige?',
   c:'El contrato de trabajo existe cuando concurren actividad personal, subordinación y salario; y se presume que toda relación de trabajo personal está regida por un contrato de trabajo (Código Sustantivo del Trabajo, verificar artículos y vigencia).',
   e:'Citar artículos de memoria con un número dudoso. Si no estás seguro, enuncia la regla y nombra el código.'},
  {l:'E',t:'Evidencia y precedente',q:'¿Qué prueba y qué jurisprudencia importan?',
   c:'Prueba de la subordinación: los mensajes del chat, el cuadro de horarios, los llamados de atención, testigos. Las altas cortes tienen una línea consolidada sobre el «contrato realidad»: menciónala como regla, sin inventar números de sentencias.',
   e:'Inventar una sentencia «para que se vea completo». Resta más de lo que suma.'},
  {l:'X',t:'Examen crítico',q:'Aplica cada requisito a los hechos, uno por uno.',
   c:'Actividad personal: ella misma atendía la recepción. Subordinación: horario impuesto, órdenes y llamados de atención. Salario: pago mensual fijo, aunque se llamara «honorarios». Los tres elementos concurren y la clínica no desvirtuó la presunción.',
   e:'Decir «se cumplen los requisitos» sin mostrar con qué hecho se cumple cada uno.'},
  {l:'I',t:'Interpretación (contraparte)',q:'¿Qué diría la contraparte? ¿Hay excepción?',
   c:'La clínica alegará autonomía: Valeria facturaba y pagaba su propia seguridad social. No prospera: prevalece la realidad sobre la forma. Sí podría prosperar si ella hubiera fijado su horario, podido delegar el trabajo o atendido a otros clientes.',
   e:'Ignorar el contraargumento. Mencionarlo y descartarlo con razones vale puntos.'},
  {l:'A',t:'Argumentación y conclusión',q:'Cierra con una conclusión defendible.',
   c:'Sí: existió un contrato de trabajo realidad y Valeria puede reclamar prestaciones, vacaciones y aportes. Debe actuar pronto: los derechos laborales prescriben (por regla general en tres años desde que son exigibles; verificar) y un reclamo escrito interrumpe ese término.',
   e:'Terminar sin conclusión o con una conclusión distinta a la pregunta.'}];

const TL_HECHOS_CASO='Pregunta: ¿procede la tutela de Jorge contra su EPS por la negación de una cirugía? Marca cada hecho como relevante o distractor.';
const TL_HECHOS=[
  {t:'El médico tratante de Jorge ordenó una cirugía de columna el 3 de mayo.',r:true,
   f:'Relevante: la orden del médico tratante es la base de la pretensión en salud.'},
  {t:'Jorge es hincha del Deportivo Cali y no se pierde un partido.',r:false,
   f:'Distractor: no se relaciona con ningún requisito de la tutela.'},
  {t:'La EPS negó la cirugía el 10 de mayo diciendo que «no hay agenda».',r:true,
   f:'Relevante: es la conducta que vulnera el derecho, y su motivo no es una razón médica.'},
  {t:'Jorge presentó la tutela el 2 de junio.',r:true,
   f:'Relevante: permite analizar la inmediatez (menos de un mes desde la negación).'},
  {t:'La clínica donde lo atienden fue remodelada en 2023.',r:false,
   f:'Distractor: la remodelación no cambia la obligación de la EPS.'},
  {t:'Según su médico, sin la cirugía Jorge pierde movilidad en las piernas.',r:true,
   f:'Relevante: muestra la urgencia y el riesgo de un perjuicio irremediable.'},
  {t:'Jorge tiene un hermano abogado que vive en Canadá.',r:false,
   f:'Distractor: Jorge puede presentar la tutela él mismo; no se necesita abogado.'},
  {t:'Jorge gana un salario mínimo y no puede pagar la cirugía de forma particular.',r:true,
   f:'Relevante: su falta de capacidad económica pesa en la subsidiariedad y en el mínimo vital.'}];

const TL_CONECTORES_FAM=[['Causa','porque, ya que, toda vez que'],['Consecuencia','por lo tanto, en consecuencia, de modo que'],
  ['Concesión','si bien, aunque, a pesar de que'],['Contraste','sin embargo, no obstante, en cambio'],
  ['Adición','además, asimismo, igualmente'],['Conclusión','en conclusión, en suma, así las cosas']];
const TL_OPCIONES_CON=['porque','sin embargo','por lo tanto','además','si bien','en conclusión','aunque','de modo que'];
const TL_HUECOS=[
  {antes:'La tutela procede en este caso ',ok:['porque'],fam:'causa',despues:' la EPS negó una cirugía ordenada por el médico tratante. '},
  {antes:'',ok:['si bien','aunque'],fam:'concesión',may:true,despues:' existe un trámite ante la Superintendencia de Salud, no es eficaz frente a la urgencia del paciente; '},
  {antes:'',ok:['por lo tanto','de modo que'],fam:'consecuencia',despues:', la acción respeta la subsidiariedad. '},
  {antes:'',ok:['además'],fam:'adición',may:true,despues:', la tutela se presentó tres semanas después de la negación, '},
  {antes:'',ok:['de modo que','por lo tanto'],fam:'consecuencia',despues:' se cumple la inmediatez. '},
  {antes:'',ok:['en conclusión'],fam:'conclusión',may:true,despues:', el juez debe ordenar la cirugía.'}];

const TL_ESQUELETOS=[
  {id:'tutela',t:'Acción de tutela',n:'Art. 86 de la Constitución y Decreto 2591 de 1991 (verificar vigencia). No exige abogado.',
   p:[['Juez de la República (reparto)','Lugar y fecha arriba.'],['Accionante y accionado','Quién, en qué calidad, contra quién.'],
      ['Hechos','Numerados, uno por numeral, con fechas.'],['Derechos vulnerados','Cada uno, con cómo se vulnera.'],
      ['Procedencia','Legitimación, subsidiariedad e inmediatez, con los hechos.'],['Fundamentos de derecho','Normas pertinentes; sin sentencias dudosas.'],
      ['Medida provisional','Solo si hay urgencia, con la razón.'],['Pretensiones','Órdenes concretas, a quién y en qué plazo.'],
      ['Pruebas y anexos','Lista de documentos.'],['Juramento','No haber presentado otra tutela por los mismos hechos.'],
      ['Notificaciones y firma','Dirección y correo.']]},
  {id:'peticion',t:'Derecho de petición',n:'Art. 23 de la Constitución y Ley 1755 de 2015 (verificar vigencia).',
   p:[['Lugar y fecha',''],['Destinatario','Entidad y dependencia.'],['Referencia','«Derecho de petición».'],['Peticionario','Nombre e identificación.'],
      ['Hechos','Lo necesario, con fechas.'],['Peticiones','Concretas y numeradas.'],['Fundamentos','Constitución y ley.'],['Anexos',''],
      ['Dirección para la respuesta','Física o electrónica.'],['Firma','']]},
  {id:'demanda_verbal',t:'Demanda (proceso verbal)',n:'Requisitos de la demanda en el Código General del Proceso (verificar artículos y vigencia).',
   p:[['Designación del juez','Competente por cuantía y territorio.'],['Partes','Nombre, domicilio, identificación, apoderado.'],
      ['Pretensiones','Claras, separadas: principales, subsidiarias, consecuenciales.'],['Hechos','Determinados, clasificados y numerados.'],
      ['Fundamentos de derecho',''],['Juramento estimatorio','Si pide perjuicios: razonado y discriminado.'],['Pruebas','Que pide y aporta.'],
      ['Cuantía y competencia',''],['Anexos','Poder, certificados, requisito de procedibilidad si aplica.'],['Notificaciones y firma','Canal digital de las partes.']]},
  {id:'reposicion',t:'Recurso (reposición o apelación)',n:'Recursos en el Código General del Proceso (verificar términos y procedencia).',
   p:[['Referencia','Despacho, radicado, partes.'],['Providencia recurrida','Fecha, decisión y notificación.'],
      ['Interposición','«Interpongo recurso de…» (y apelación en subsidio si procede).'],
      ['Sustentación','Razones concretas: dónde está el error. En la apelación de sentencias, reparos concretos.'],
      ['Petición','Revocar o reformar, y qué decidir en su lugar.'],['Oportunidad','Dentro del término desde la notificación.'],['Firma','']]}];

const TL_ERRORES=[
  ['Hechos','Contar la historia en un solo párrafo','Un hecho por numeral, en orden y con su fecha.'],
  ['Pretensiones','Pedir «lo que en derecho corresponda»','Pide órdenes concretas: qué, a quién y en qué plazo.'],
  ['Fundamentos','Citar sentencias de memoria','Si no puedes verificar el número, enuncia la regla y nombra la norma.'],
  ['Procedencia','Olvidar la procedencia o el término','En la tutela, legitimación, subsidiariedad e inmediatez; en recursos y demandas, la oportunidad y la caducidad.'],
  ['Pruebas','Anunciar pruebas que no se aportan','Enumera lo que anexas y pide lo que necesitas que se practique.'],
  ['Estructura','Olvidar juramento, notificaciones o firma','Repasa la lista de comprobación antes de entregar.'],
  ['Estilo','Adjetivos y ataques a la contraparte','El tono sobrio convence más: hechos y razones.'],
  ['Estilo','Transcribir normas completas','Cita el artículo y explica en una frase para qué lo usas.'],
  ['Problema','Responder otra pregunta (en el modular)','Copia la pregunta del examen y responde exactamente eso.'],
  ['Procedencia','Confundir prescripción y caducidad','La caducidad no se interrumpe como la prescripción y el juez la declara de oficio.']];
const TL_QUIZ={q:'¿Cuál de estas pretensiones de una tutela está mejor formulada?',
  o:[['Que se protejan mis derechos y se haga lo que en derecho corresponda.',false,'Es vaga: el juez no sabe qué ordenar.'],
     ['Que se ordene a la EPS Vida Plena entregar el medicamento formulado el 4 de agosto de 2026, dentro de las 48 horas siguientes a la notificación del fallo.',true,'Correcta: dice qué, a quién y en qué plazo.'],
     ['Que se sancione a la EPS por su actuar negligente y abusivo.',false,'La tutela no es para sancionar; además, los adjetivos no reemplazan la petición.']]};

function tlComoInit(){
  const raiz=document.getElementById('tl-como');if(!raiz||TL.comoListo)return;TL.comoListo=true;
  raiz.appendChild(tE('div',{class:'cab-vista'},tE('p',{class:'eyebrow claim',text:'PULLEX Academia'}),
    tE('h2',{class:'display',text:'Cómo contestar'}),
    tE('p',{text:'Lecciones cortas para responder modulares y redactar escritos. Cada una trae un ejercicio con respuesta inmediata y termina en «Practicar ahora». Nada de esto gasta consultas.'})));
  const lay=tE('div',{class:'tl-como-lay'});
  const nav=tE('div',{class:'tl-lecciones',role:'tablist','aria-label':'Lecciones','aria-orientation':'vertical'});
  TL_LECCIONES.forEach(l=>nav.appendChild(tE('button',{type:'button',role:'tab',id:'tl-lec-'+l.id,'aria-controls':'tl-leccion',
    'aria-selected':String(l.id===TL.leccion),tabindex:l.id===TL.leccion?'0':'-1',class:'tl-lec'+(l.id===TL.leccion?' on':''),
    on:{click:()=>tlLeccion(l.id,true),keydown:tlLecTeclas}},tE('span',{class:'tl-lec-n','aria-hidden':'true',text:l.n}),
    tE('span',{class:'tl-lec-t'},tE('b',null,l.t),tE('span',null,l.d+' · '+l.min)))));
  lay.appendChild(nav);
  lay.appendChild(tE('div',{class:'panel tl-leccion',id:'tl-leccion',role:'tabpanel','aria-labelledby':'tl-lec-'+TL.leccion,tabindex:'-1'}));
  raiz.appendChild(lay);
  tlLeccion(TL.leccion,false);
}
function tlLecTeclas(ev){
  const ids=TL_LECCIONES.map(l=>l.id);const i=ids.indexOf(TL.leccion);let j=null;
  if(ev.key==='ArrowDown'||ev.key==='ArrowRight')j=(i+1)%ids.length;else if(ev.key==='ArrowUp'||ev.key==='ArrowLeft')j=(i+ids.length-1)%ids.length;
  else if(ev.key==='Home')j=0;else if(ev.key==='End')j=ids.length-1;
  if(j===null)return;ev.preventDefault();tlLeccion(ids[j],false);document.getElementById('tl-lec-'+ids[j]).focus();
}
function tlLeccion(id,mover){
  TL.leccion=id;
  TL_LECCIONES.forEach(l=>{const b=document.getElementById('tl-lec-'+l.id);const on=l.id===id;b.classList.toggle('on',on);
    b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1});
  const p=document.getElementById('tl-leccion');p.textContent='';p.setAttribute('aria-labelledby','tl-lec-'+id);
  const l=TL_LECCIONES.find(x=>x.id===id);
  p.appendChild(tE('p',{class:'eyebrow',text:'Lección '+l.n+' de '+TL_LECCIONES.length+' · '+l.min}));
  p.appendChild(tE('h3',{class:'tl-lec-h',id:'tl-lec-h',tabindex:'-1',text:l.t}));
  ({metodo:tlLecMetodo,hechos:tlLecHechos,conectores:tlLecConectores,estructura:tlLecEstructura,errores:tlLecErrores})[id](p);
  if(mover&&window.matchMedia('(max-width:759px)').matches){p.scrollIntoView({behavior:'smooth',block:'start'})}
  if(mover){const h=document.getElementById('tl-lec-h');if(h)h.focus({preventScroll:true})}
}
function tlPracticar(p,texto,fn){
  p.appendChild(tE('div',{class:'tl-practicar'},tE('div',null,tE('b',null,'Practicar ahora'),tE('span',null,texto)),
    tBtn('Practicar ahora','bpri',fn,{'aria-label':'Practicar ahora: '+texto})));
}

// (a) Método PULLEX en 8 pasos, con un caso resuelto paso a paso.
function tlLecMetodo(p){
  p.appendChild(tE('p',{class:'tl-intro',text:'Un modular no se gana con memoria, sino con orden. El método PULLEX son ocho preguntas que te haces siempre en el mismo orden. Míralo aplicado a un caso.'}));
  p.appendChild(tE('div',{class:'tl-caso'},tE('span',{class:'eyebrow',text:'Caso'}),tE('p',null,TL_CASO_METODO)));
  const puntos=tE('div',{class:'tl-pasos-nav',role:'group','aria-label':'Pasos del método'});
  TL_PASOS.forEach((s,i)=>puntos.appendChild(tE('button',{type:'button',class:'tl-punto','data-i':String(i),
    'aria-label':'Paso '+(i+1)+': '+s.t,on:{click:()=>tlPaso(i)}},s.l)));
  p.appendChild(puntos);
  p.appendChild(tE('div',{class:'tl-paso',id:'tl-paso','aria-live':'polite'}));
  p.appendChild(tE('div',{class:'ml-acc tl-paso-acc'},tBtn('Anterior','bsec',()=>tlPaso(TL.paso-1),{id:'tl-paso-ant'}),
    tBtn('Siguiente','bpri',()=>tlPaso(TL.paso+1),{id:'tl-paso-sig'})));
  tlPaso(TL.paso||0);
  p.appendChild(tE('div',{class:'lb2',text:'Errores frecuentes al contestar un modular'}));
  const ul=tE('ul',{class:'tl-viñetas'});
  ['Responder sin leer la pregunta completa: subraya qué te piden (¿procede?, ¿qué acción?, ¿quién responde?).',
   'Mezclar el análisis de todos los requisitos en un solo párrafo.',
   'Citar normas sin aplicarlas a los hechos.',
   'Olvidar la tesis contraria o la excepción.',
   'Cerrar sin conclusión, o con una conclusión que no responde la pregunta.'].forEach(t=>ul.appendChild(tE('li',null,t)));
  p.appendChild(ul);
  tlPracticar(p,'Un caso de Derecho Laboral, nivel básico, en Casos.',()=>tlIr('casos',{area:'Laboral',nivel:'basico'}));
}
function tlPaso(i){
  i=Math.max(0,Math.min(TL_PASOS.length-1,i));TL.paso=i;const s=TL_PASOS[i];
  const c=document.getElementById('tl-paso');if(!c)return;c.textContent='';
  c.appendChild(tE('div',{class:'tl-paso-cab'},tE('span',{class:'tl-letra','aria-hidden':'true',text:s.l}),
    tE('div',null,tE('span',{class:'eyebrow',text:'Paso '+(i+1)+' de '+TL_PASOS.length}),tE('h4',{text:s.t}))));
  c.appendChild(tE('p',{class:'tl-q',text:s.q}));
  c.appendChild(tE('div',{class:'tl-en-caso'},tE('b',null,'En el caso: '),s.c));
  c.appendChild(tE('div',{class:'tl-error'},tE('b',null,'Error frecuente: '),s.e));
  document.querySelectorAll('.tl-punto').forEach(b=>{const on=+b.dataset.i===i;b.classList.toggle('on',on);
    if(on)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current')});
  const a=document.getElementById('tl-paso-ant'),n=document.getElementById('tl-paso-sig');
  if(a)a.disabled=i===0;if(n){n.disabled=i===TL_PASOS.length-1;n.textContent=i===TL_PASOS.length-1?'Fin del método':'Siguiente'}
}

// (b) Hechos relevantes y distractores, con retroalimentación inmediata.
function tlLecHechos(p){
  p.appendChild(tE('p',{class:'tl-intro',text:'Quien redacta un caso de examen esconde hechos que no sirven para nada. Un hecho es relevante si sirve para probar o descartar un requisito de la norma; si quitarlo no cambia la respuesta, es un distractor.'}));
  p.appendChild(tE('div',{class:'tl-caso'},tE('span',{class:'eyebrow',text:'Ejercicio'}),tE('p',null,TL_HECHOS_CASO)));
  const res={};const marcador=tE('p',{class:'tl-marcador',id:'tl-hechos-marcador','aria-live':'polite'});
  const pintar=()=>{const n=Object.keys(res).length,ok=Object.values(res).filter(Boolean).length;
    marcador.textContent=n?('Llevas '+ok+' de '+n+' bien'+(n===TL_HECHOS.length?(ok===n?'. ¡Todos bien!':'. Revisa los que fallaste: lee la explicación.'):'.')):'Marca los '+TL_HECHOS.length+' hechos.'};
  const ol=tE('ol',{class:'tl-hechos-lista'});
  TL_HECHOS.forEach((h,i)=>{
    const fb=tE('p',{class:'tl-fb','aria-live':'polite'});
    const li=tE('li',{class:'tl-hecho'},tE('p',{class:'tl-hecho-t',text:h.t}));
    const grupo=tE('div',{class:'tl-elige',role:'group','aria-label':'Hecho '+(i+1)});
    [['Relevante',true],['Distractor',false]].forEach(([t,v])=>grupo.appendChild(tE('button',{type:'button',class:'tl-op','aria-pressed':'false',
      'data-hecho':String(i),'data-valor':String(v),on:{click:ev=>{
        grupo.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===ev.currentTarget)));
        const bien=v===h.r;res[i]=bien;li.classList.toggle('bien',bien);li.classList.toggle('mal',!bien);
        fb.textContent=(bien?'Correcto. ':'No exactamente. ')+h.f;pintar()}}},t)));
    li.appendChild(grupo);li.appendChild(fb);ol.appendChild(li)});
  p.appendChild(ol);pintar();p.appendChild(marcador);
  p.appendChild(tE('div',{class:'ml-acc'},tBtn('Volver a empezar','bghost',()=>tlLeccion('hechos',true))));
  tlPracticar(p,'Un caso de Derecho Constitucional, nivel básico, en Casos.',()=>tlIr('casos',{area:'Constitucional',nivel:'basico'}));
}

// (c) Conectores y párrafos argumentativos: completar con el conector correcto.
function tlLecConectores(p){
  p.appendChild(tE('p',{class:'tl-intro',text:'Un buen párrafo argumentativo tiene cuatro piezas: una afirmación (la tesis), la razón (la norma o el requisito), la aplicación a los hechos y una conclusión parcial. Los conectores dicen al lector qué relación hay entre esas piezas; un conector equivocado cambia el argumento.'}));
  const tabla=tE('div',{class:'tl-familias'});
  TL_CONECTORES_FAM.forEach(([f,e])=>tabla.appendChild(tE('div',null,tE('b',null,f),tE('span',null,e))));
  p.appendChild(tabla);
  p.appendChild(tE('div',{class:'lb2',text:'Ejercicio: completa el párrafo'}));
  const par=tE('p',{class:'tl-parrafo'});const fbs=tE('ul',{class:'tl-fb-lista','aria-live':'polite'});
  TL_HUECOS.forEach((h,i)=>{
    if(h.antes)par.appendChild(document.createTextNode(h.antes));
    const sel=tE('select',{class:'inp tl-hueco','aria-label':'Conector '+(i+1),'data-hueco':String(i)});
    sel.appendChild(tE('option',{value:''},'(elige)'));
    TL_OPCIONES_CON.forEach(o=>sel.appendChild(tE('option',{value:o},h.may?o.charAt(0).toUpperCase()+o.slice(1):o)));
    const li=tE('li',{class:'hidden'});fbs.appendChild(li);
    sel.addEventListener('change',()=>{const v=sel.value;if(!v){li.classList.add('hidden');sel.classList.remove('bien','mal');return}
      const bien=h.ok.includes(v);sel.classList.toggle('bien',bien);sel.classList.toggle('mal',!bien);li.classList.remove('hidden');
      li.className=bien?'bien':'mal';
      li.textContent='Hueco '+(i+1)+': '+(bien?'correcto, aquí va un conector de '+h.fam+'.':'«'+v+'» no encaja: aquí hace falta un conector de '+h.fam+' (por ejemplo, «'+h.ok[0]+'»).')});
    par.appendChild(sel);par.appendChild(document.createTextNode(h.despues))});
  p.appendChild(par);p.appendChild(fbs);
  p.appendChild(tE('p',{class:'tl-nota',text:'Fíjate en el orden del párrafo: afirmación («la tutela procede»), razón (la orden médica negada), aplicación a cada requisito y conclusión. Esa es la misma estructura que espera la rúbrica en «Argumentación» y en «Estilo y conectores».'}));
  tlPracticar(p,'Un caso de Derecho Constitucional, nivel intermedio, en Casos.',()=>tlIr('casos',{area:'Constitucional',nivel:'intermedio'}));
}

// (d) Estructura de los escritos más comunes.
function tlLecEstructura(p){
  p.appendChild(tE('p',{class:'tl-intro',text:'Cada escrito tiene un esqueleto. Si lo dominas, solo tienes que llenarlo con los hechos del caso. Abre cada uno y practica con un escenario del Taller.'}));
  TL_ESQUELETOS.forEach((s,i)=>{
    const ol=tE('ol',{class:'tl-esqueleto'});s.p.forEach(([t,d])=>ol.appendChild(tE('li',null,tE('b',null,t),d?tE('span',null,d):null)));
    p.appendChild(tE('details',{class:'metodo tl-det',open:i===0?true:null},tE('summary',null,s.t),ol,tE('p',{class:'tl-nota',text:s.n}),
      tE('div',{class:'ml-acc'},tBtn('Practicar ahora','bpri',()=>tlIr('taller',{tipo:s.id,nivel:'basico'}),{'aria-label':'Practicar ahora: '+s.t+' en el Taller'}))))});
  tlPracticar(p,'Un escenario del Taller de escritos: acción de tutela, nivel básico.',()=>tlIr('taller',{tipo:'tutela',nivel:'basico'}));
}

// (e) Errores que hacen perder puntos, con una pregunta de control.
function tlLecErrores(p){
  p.appendChild(tE('p',{class:'tl-intro',text:'Estos son los errores que más puntos restan en la rúbrica de escritos y en los modulares. Cada uno dice en qué criterio pesa.'}));
  const g=tE('div',{class:'tl-errores'});
  TL_ERRORES.forEach(([crit,t,s])=>g.appendChild(tE('div',{class:'tl-err'},tE('span',{class:'tag',text:crit}),tE('b',null,t),tE('span',null,s))));
  p.appendChild(g);
  p.appendChild(tE('div',{class:'lb2',text:'Pregunta de control'}));
  p.appendChild(tE('p',{class:'tl-q',text:TL_QUIZ.q}));
  const fb=tE('p',{class:'tl-fb','aria-live':'polite'});const grupo=tE('div',{class:'tl-quiz',role:'group','aria-label':TL_QUIZ.q});
  TL_QUIZ.o.forEach(([t,ok,f])=>grupo.appendChild(tE('button',{type:'button',class:'tl-op tl-op-larga','aria-pressed':'false',on:{click:ev=>{
    grupo.querySelectorAll('button').forEach(b=>{b.setAttribute('aria-pressed',String(b===ev.currentTarget));b.classList.remove('bien','mal')});
    ev.currentTarget.classList.add(ok?'bien':'mal');fb.textContent=(ok?'Correcto. ':'No. ')+f}}},t)));
  p.appendChild(grupo);p.appendChild(fb);
  tlPracticar(p,'Redacta una tutela en el Taller y revisa tu evaluación con esta lista.',()=>tlIr('taller',{tipo:'tutela',nivel:'basico'}));
}

// -------------------------------------------------------------------------- integración --
(function tlArrancar(){
  TL_TABS.forEach(t=>{const b=document.getElementById('tl-tab-'+t);if(b){b.addEventListener('click',()=>tlTab(t));b.addEventListener('keydown',tlTabTeclas)}});
  const w=tlCasosWrap();if(w){if(!w.id)w.id='tl-panel-casos';w.setAttribute('role','tabpanel');w.setAttribute('aria-labelledby','tl-tab-casos')}
  const bc=document.getElementById('tl-tab-casos');if(bc&&w)bc.setAttribute('aria-controls',w.id);
  // Mostrar un caso del Modular Lab (desde Mi mapa, el tablero o «Practicar») siempre vuelve a la pestaña Casos.
  if(typeof mlMostrarCaso==='function'){const o=mlMostrarCaso;mlMostrarCaso=function(){if(TL.tab!=='casos')tlTab('casos',{sinScroll:true});return o.apply(this,arguments)}}
  if(typeof mlElegir==='function'){const o=mlElegir;mlElegir=function(){if(TL.tab!=='casos')tlTab('casos',{sinScroll:true});return o.apply(this,arguments)}}
  // Tablero de Inicio: agrega «Practica un escrito» cuando aplica (después de que app.js arma el tablero).
  if(typeof cargarTablero==='function'){const o=cargarTablero;cargarTablero=async function(){const r=await o.apply(this,arguments);tlTarjetaInicio();return r}}
})();
