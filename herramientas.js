// =========================================================================================
// PULLEX Herramientas — Calculadora de términos (J05) y Liquidación (J06).
// Se carga después de app.js y usa sus utilidades globales (auth, toast). Sin JavaScript en línea:
// todo con addEventListener. Los datos del servidor se pintan con textContent (nunca como HTML).
// El cálculo lo hace el servidor (procedimientos/): aquí solo hay formulario y presentación.
// =========================================================================================
const HERR={listo:false,cargando:false,tab:'terminos',opc:null,ultimo:{terminos:null,liquidacion:null}};
const HERR_TABS=[['terminos','Términos'],['liquidacion','Liquidación']];
const HERR_ESTADOS={VERIFICADA_EN_FUENTE_OFICIAL:'Verificada en fuente oficial',NO_VERIFICADO:'No verificado',
  'REVISIÓN_HUMANA_PENDIENTE':'Revisión humana pendiente'};
const HERR_TRI=[['','No lo sé'],['si','Sí'],['no','No']];

// ------------------------------------------------------------------------- utilidades --
function hE(tag,attrs,...hijos){const e=document.createElement(tag);
  if(attrs)for(const [k,v] of Object.entries(attrs)){if(v==null||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;
    else if(k==='on')Object.entries(v).forEach(([ev,fn])=>e.addEventListener(ev,fn));
    else e.setAttribute(k,v===true?'':v)}
  hijos.flat().forEach(h=>{if(h==null||h===false)return;e.appendChild(typeof h==='string'?document.createTextNode(h):h)});
  return e}
function hBtn(txt,cls,fn,attrs){return hE('button',{type:'button',class:'herr-btn'+(cls?' '+cls:''),on:{click:fn},...(attrs||{})},txt)}
async function herrApi(url,body){
  const h={...auth()};if(body!==undefined)h['content-type']='application/json';
  const r=await fetch(url,{method:body!==undefined?'POST':'GET',headers:h,body:body!==undefined?JSON.stringify(body):undefined});
  const d=await r.json().catch(()=>({}));
  if(!r.ok){const e=new Error(typeof d.detail==='string'?d.detail:'No se pudo completar la solicitud.');e.status=r.status;throw e}
  return d}
function hCampo(id,etiqueta,control,ayuda,req){
  const lab=hE('label',{for:id},etiqueta,req?hE('span',{class:'herr-req','aria-hidden':'true'},' *'):hE('span',{class:'herr-opc'},' (opcional)'));
  if(req)control.setAttribute('aria-required','true');
  const partes=[lab];
  if(ayuda){const a=hE('p',{class:'herr-ayuda',id:id+'-ay',text:ayuda});control.setAttribute('aria-describedby',id+'-ay');partes.push(a)}
  partes.push(control);return hE('div',{class:'herr-campo',id:id+'-c'},partes)}
function hInput(id,tipo,attrs){return hE('input',{id,class:'herr-inp',type:tipo||'text',autocomplete:'off',...(attrs||{})})}
function hSelect(id,opciones,attrs){const s=hE('select',{id,class:'herr-inp',...(attrs||{})});
  opciones.forEach(([v,t])=>s.appendChild(hE('option',{value:v},t)));return s}
function hVal(id){const e=document.getElementById(id);return e?e.value.trim():''}
function hTri(id){const v=hVal(id);return v==='si'?true:v==='no'?false:null}
function hPesos(n){return typeof n==='number'?'$ '+n.toLocaleString('es-CO'):'—'}
function hFecha(iso){if(!iso)return '';const [a,m,d]=iso.split('-').map(Number);
  return new Date(a,m-1,d).toLocaleDateString('es-CO',{weekday:'long',day:'numeric',month:'long',year:'numeric'})}
async function herrCopiar(texto){try{await navigator.clipboard.writeText(texto);toast('Copiado')}
  catch(e){toast('No se pudo copiar: selecciona el texto y cópialo.')}}
function hLista(titulo,items,cls){if(!items||!items.length)return null;
  return hE('section',{class:'herr-bloque '+(cls||'')},hE('h4',{text:titulo}),hE('ul',null,items.map(t=>hE('li',{text:String(t)}))))}
function hNormas(normas){if(!normas||!normas.length)return null;
  return hE('section',{class:'herr-bloque herr-normas'},hE('h4',{text:'Normas y reglas usadas'}),
    hE('ul',null,normas.map(n=>hE('li',null,
      hE('span',{class:'herr-regla-id',text:n.id+' v'+n.version}),' ',
      n.enlace?hE('a',{href:n.enlace,target:'_blank',rel:'noopener noreferrer',text:n.norma}):hE('span',{text:n.norma}),
      ' ',hE('span',{class:'herr-chip '+(n.estado==='VERIFICADA_EN_FUENTE_OFICIAL'?'ok':'pend'),text:HERR_ESTADOS[n.estado]||n.estado}),
      n.consultado?hE('span',{class:'herr-meta',text:' · consultada el '+n.consultado}):null,
      n.vigencia_comprobada_a_la_fecha===false&&n.estado==='VERIFICADA_EN_FUENTE_OFICIAL'?
        hE('span',{class:'herr-meta',text:' · vigencia a la fecha del cálculo sin comprobar'}):null))))}
function hMarcarFaltantes(prefijo,faltantes){
  document.querySelectorAll('#herr-panel-'+HERR.tab+' [aria-invalid]').forEach(e=>e.removeAttribute('aria-invalid'));
  let primero=null;
  (faltantes||[]).forEach(f=>{const clave=String(f).split(/[:\s(]/)[0].replace(/\[\d+\]/g,'').replace(/\./g,'-');
    let e=document.getElementById(prefijo+clave);
    // Un campo oculto no puede recibir foco: se marca el selector que lo gobierna (el término).
    if(e&&e.offsetParent===null)e=document.getElementById(prefijo+'termino_id');
    if(e&&e.offsetParent!==null&&e.matches('input,select,textarea')){e.setAttribute('aria-invalid','true');if(!primero)primero=e}});
  return primero}

// --------------------------------------------------------------------------- arranque --
function herrInit(){
  const raiz=document.getElementById('herr-raiz');if(!raiz||HERR.listo||HERR.cargando)return;
  HERR.cargando=true;raiz.textContent='';
  raiz.appendChild(hE('div',{class:'cab-vista'},hE('p',{class:'eyebrow',text:'PULLEX Herramientas'}),hE('h2',{text:'Cálculos verificables'}),
    hE('p',{text:'Calculadoras deterministas: no usan IA ni gastan consultas. Cada resultado muestra la norma, los supuestos y lo que debe decidir un profesional.'})));
  const estado=hE('p',{class:'herr-cargando',role:'status',text:'Cargando…'});raiz.appendChild(estado);
  herrApi('/api/procedimientos').then(d=>{HERR.opc=d;HERR.listo=true;estado.remove();herrConstruir(raiz)})
    .catch(e=>{estado.textContent=e.status===404?'Las herramientas de cálculo no están disponibles en esta versión.':
      'No se pudieron cargar las herramientas: '+e.message})
    .finally(()=>{HERR.cargando=false});
}
function herrConstruir(raiz){
  const tabs=hE('div',{class:'herr-tabs',role:'tablist','aria-label':'Herramientas'});
  HERR_TABS.forEach(([id,nombre])=>tabs.appendChild(hE('button',{type:'button',role:'tab',id:'herr-tab-'+id,'aria-controls':'herr-panel-'+id,
    'aria-selected':String(id===HERR.tab),tabindex:id===HERR.tab?'0':'-1',class:'herr-tab'+(id===HERR.tab?' on':''),
    on:{click:()=>herrTab(id),keydown:herrTabTeclas}},nombre)));
  raiz.appendChild(tabs);
  HERR_TABS.forEach(([id])=>raiz.appendChild(hE('div',{role:'tabpanel',id:'herr-panel-'+id,'aria-labelledby':'herr-tab-'+id,
    class:'herr-panel'+(id===HERR.tab?'':' hidden'),tabindex:'-1'})));
  herrTerminosVista();herrLiquidacionVista();
}
function herrTabTeclas(ev){
  const i=HERR_TABS.findIndex(([id])=>id===HERR.tab);let j=null;
  if(ev.key==='ArrowRight')j=(i+1)%HERR_TABS.length;else if(ev.key==='ArrowLeft')j=(i+HERR_TABS.length-1)%HERR_TABS.length;
  else if(ev.key==='Home')j=0;else if(ev.key==='End')j=HERR_TABS.length-1;
  if(j===null)return;ev.preventDefault();herrTab(HERR_TABS[j][0]);document.getElementById('herr-tab-'+HERR_TABS[j][0]).focus()}
function herrTab(id){HERR.tab=id;
  HERR_TABS.forEach(([t])=>{const b=document.getElementById('herr-tab-'+t);const on=t===id;b.classList.toggle('on',on);
    b.setAttribute('aria-selected',String(on));b.tabIndex=on?0:-1;document.getElementById('herr-panel-'+t).classList.toggle('hidden',!on)})}

// ---------------------------------------------------------------- filas dinámicas (fechas) --
function herrFila(cont,prefijo,conTasa){
  const n=(+cont.dataset.n||0)+1;cont.dataset.n=n;const id=prefijo+n;
  const fila=hE('div',{class:'herr-fila',role:'group','aria-label':(conTasa?'Período ':'Suspensión ')+n},
    hE('div',null,hE('label',{for:id+'-d',text:'Desde'}),hInput(id+'-d','date',{'data-k':'desde'})),
    hE('div',null,hE('label',{for:id+'-h',text:'Hasta'}),hInput(id+'-h','date',{'data-k':'hasta'})),
    conTasa?hE('div',null,hE('label',{for:id+'-t',text:'Tasa anual (%)'}),hInput(id+'-t','text',{'data-k':'tasa_pct',inputmode:'decimal',placeholder:'Ej.: 25,5'})):
      hE('div',null,hE('label',{for:id+'-m',text:'Motivo'}),hInput(id+'-m','text',{'data-k':'motivo',maxlength:'160'})),
    hBtn('Quitar','herr-mini',()=>fila.remove(),{'aria-label':'Quitar '+(conTasa?'período ':'suspensión ')+n}));
  cont.appendChild(fila);return fila}
function herrFilas(cont){return [...cont.querySelectorAll('.herr-fila')].map(f=>{const o={};
  f.querySelectorAll('[data-k]').forEach(i=>{if(i.value.trim())o[i.dataset.k]=i.value.trim()});return o}).filter(o=>Object.keys(o).length)}

// ------------------------------------------------------------------------------ términos --
function herrTerminosVista(){
  const p=document.getElementById('herr-panel-terminos'),T=HERR.opc.terminos;p.textContent='';
  const regimen=hSelect('herr-t-regimen',[['','Elige…']].concat(T.regimenes.map(r=>[r.id,r.nombre])));
  const termino=hSelect('herr-t-termino_id',[['','Elige primero el régimen']]);
  const forma=hSelect('herr-t-forma_notificacion',[['','Elige…']].concat(T.formas_notificacion.map(f=>[f.id,f.nombre])));
  const propio=hE('div',{class:'herr-campos hidden',id:'herr-t-propio'},
    hCampo('herr-t-cantidad','Número',hInput('herr-t-cantidad','number',{min:'1',max:'400',inputmode:'numeric'}),'',true),
    hCampo('herr-t-unidad','Unidad',hSelect('herr-t-unidad',[['dias','Días'],['meses','Meses'],['anios','Años']]),'',true),
    hCampo('herr-t-tipo_dias','Clase de días',hSelect('herr-t-tipo_dias',[['','Elige…'],['habiles','Hábiles'],['calendario','Calendario']]),
      'Solo aplica si la unidad es días.',true));
  const judicial=hE('div',{class:'herr-campos hidden',id:'herr-t-judicial'},
    hCampo('herr-t-vacancia_judicial','¿El despacho tuvo vacancia judicial colectiva (20 de diciembre a 10 de enero)?',hSelect('herr-t-vacancia_judicial',HERR_TRI),
      'Si no lo sabes y el dato cambia el resultado, verás los dos escenarios.'),
    hCampo('herr-t-semana_santa_judicial','¿El despacho no atendió lunes, martes y miércoles santos?',hSelect('herr-t-semana_santa_judicial',HERR_TRI),''));
  const acuse=hE('div',{class:'herr-check hidden',id:'herr-t-acuse-c'},hE('input',{type:'checkbox',id:'herr-t-acuse_constatado'}),
    hE('label',{for:'herr-t-acuse_constatado',text:'Hay acuse de recibo o se constató el acceso del destinatario al mensaje'}));
  const susp=hE('div',{class:'herr-filas',id:'herr-t-susp'});
  const refrescar=()=>{
    const r=regimen.value,reg=T.regimenes.find(x=>x.id===r);
    termino.textContent='';
    const ops=[['',r?'Elige…':'Elige primero el régimen']].concat(T.tabla.filter(t=>!r||t.regimen===r).map(t=>[t.id,
      t.etiqueta+(t.cantidad?' — '+t.cantidad+' '+(t.unidad==='dias'?'días':t.unidad==='meses'?'meses':'años'):' — plazo sin verificar para hoy')]));
    ops.push(['otro','Otro término: indico el número']);
    ops.forEach(([v,t])=>termino.appendChild(hE('option',{value:v},t)));
    propio.classList.add('hidden');judicial.classList.toggle('hidden',!(reg&&reg.judicial))};
  regimen.addEventListener('change',refrescar);
  termino.addEventListener('change',()=>{const t=T.tabla.find(x=>x.id===termino.value);
    propio.classList.toggle('hidden',!(termino.value==='otro'||(t&&(!t.cantidad||!t.tipo_dias&&t.unidad==='dias'))));
    document.getElementById('herr-t-nota').textContent=t?('Norma: '+t.norma+'. Se cuenta desde: '+t.evento_inicial+'.'):''});
  forma.addEventListener('change',()=>acuse.classList.toggle('hidden',forma.value!=='mensaje_datos'));
  const form=hE('form',{class:'herr-form',novalidate:true,on:{submit:ev=>{ev.preventDefault();herrCalcularTermino()}}},
    hE('div',{class:'herr-campos'},
      hCampo('herr-t-regimen','Régimen',regimen,'¿Ante quién corre el término?',true),
      hCampo('herr-t-termino_id','Término',termino,'Solo aparecen términos verificados en fuente oficial.',true)),
    hE('p',{class:'herr-nota',id:'herr-t-nota','aria-live':'polite'}),propio,
    hE('div',{class:'herr-campos'},
      hCampo('herr-t-fecha_notificacion','Fecha de la notificación o recepción',hInput('herr-t-fecha_notificacion','date'),
        'El día en que quedó surtida. El término se cuenta desde el día siguiente.',true),
      hCampo('herr-t-forma_notificacion','Forma de notificación',forma,'',true)),
    acuse,judicial,
    hE('div',{class:'herr-check'},hE('input',{type:'checkbox',id:'herr-t-sabado_habil'}),
      hE('label',{for:'herr-t-sabado_habil',text:'El despacho o la entidad atiende los sábados'})),
    hE('fieldset',{class:'herr-fs'},hE('legend',{text:'Suspensiones de términos (opcional)'}),susp,
      hBtn('Agregar suspensión','',()=>herrFila(susp,'herr-t-s',false).querySelector('input').focus())),
    hE('div',{class:'herr-acc'},hE('button',{type:'submit',class:'herr-btn pri',id:'herr-t-calcular'},'Calcular término'),
      hBtn('Limpiar','',()=>{form.reset();susp.textContent='';refrescar();acuse.classList.add('hidden');
        document.getElementById('herr-t-res').textContent='';document.getElementById('herr-t-nota').textContent=''})));
  p.appendChild(form);
  p.appendChild(hE('div',{id:'herr-t-res',class:'herr-res','aria-live':'polite'}));
  refrescar();
}
async function herrCalcularTermino(){
  const boton=document.getElementById('herr-t-calcular'),res=document.getElementById('herr-t-res');
  const tid=hVal('herr-t-termino_id');
  const cuerpo={regimen:hVal('herr-t-regimen'),fecha_notificacion:hVal('herr-t-fecha_notificacion'),
    forma_notificacion:hVal('herr-t-forma_notificacion'),sabado_habil:document.getElementById('herr-t-sabado_habil').checked,
    vacancia_judicial:hTri('herr-t-vacancia_judicial'),semana_santa_judicial:hTri('herr-t-semana_santa_judicial'),
    acuse_constatado:document.getElementById('herr-t-acuse_constatado').checked,
    suspensiones:herrFilas(document.getElementById('herr-t-susp')),cronologia:true};
  if(tid&&tid!=='otro')cuerpo.termino_id=tid;
  if(!document.getElementById('herr-t-propio').classList.contains('hidden')){
    if(hVal('herr-t-cantidad'))cuerpo.cantidad=hVal('herr-t-cantidad');
    if(tid==='otro')cuerpo.unidad=hVal('herr-t-unidad');
    if(hVal('herr-t-tipo_dias'))cuerpo.tipo_dias=hVal('herr-t-tipo_dias')}
  boton.disabled=true;boton.textContent='Calculando…';
  try{const r=await herrApi('/api/procedimientos/terminos',cuerpo);HERR.ultimo.terminos=r;herrPintarTermino(r)}
  catch(e){res.textContent='';res.appendChild(hE('p',{class:'herr-error',role:'alert',text:e.message}))}
  boton.disabled=false;boton.textContent='Calcular término';
}
function herrTextoTermino(r){
  const l=['CÓMPUTO DE TÉRMINO — PULLEX IA (J05 v'+r.version+', registro '+r.version_registro+')'];
  if(r.estado==='CALCULADO')l.push('Vence: '+r.fecha_vencimiento_texto+' ('+r.fecha_vencimiento+')','Empieza a contarse: '+r.inicio_computo);
  else l.push('Estado: '+r.estado+' (sin fecha definitiva)');
  (r.escenarios||[]).forEach(e=>l.push('Escenario: '+JSON.stringify(e)));
  [['Faltan',r.faltantes],['Contradicciones',r.contradicciones],['Supuestos',r.supuestos],['Advertencias',r.advertencias],
   ['Juicio profesional',r.juicio_profesional]].forEach(([t,xs])=>{if(xs&&xs.length){l.push('',t+':');xs.forEach(x=>l.push('- '+x))}});
  if(r.normas&&r.normas.length){l.push('','Normas:');r.normas.forEach(n=>l.push('- '+n.id+' v'+n.version+': '+n.norma+' ['+n.estado+']'+(n.enlace?' '+n.enlace:'')))}
  if(r.cronologia&&r.cronologia.length){l.push('','Cronología:');r.cronologia.forEach(c=>l.push(c.fecha+' '+c.dia+' — '+(c.cuenta!=null?'día '+c.cuenta:(c.motivo||''))))}
  l.push('','Huella del cálculo: '+r.huella,r.aviso||'');return l.join('\n')}
function herrPintarTermino(r){
  const res=document.getElementById('herr-t-res');res.textContent='';
  const titulo=hE('h3',{class:'herr-h',tabindex:'-1',text:r.estado==='CALCULADO'?'Resultado':r.estado==='ABSTENCION'?'Sin fecha definitiva: faltan datos':'Datos contradictorios'});
  const caja=hE('div',{class:'herr-caja '+(r.estado==='CALCULADO'?'ok':'pend')},titulo);
  if(r.estado==='CALCULADO'){
    caja.appendChild(hE('p',{class:'herr-fecha',id:'herr-t-vence',text:'Vence el '+r.fecha_vencimiento_texto}));
    caja.appendChild(hE('p',{class:'herr-meta',text:'Empieza a contarse el '+hFecha(r.inicio_computo)+'. '+
      (r.termino&&r.termino.etiqueta?r.termino.etiqueta+'. ':'')+(r.termino?r.termino.cantidad+' '+(r.termino.unidad==='dias'?'días '+(r.termino.tipo_dias==='habiles'?'hábiles':'calendario'):r.termino.unidad==='meses'?'meses':'años'):'')}))}
  [hLista('Qué falta',r.faltantes,'falta'),hLista('Contradicciones en los datos',r.contradicciones,'falta')].forEach(x=>x&&caja.appendChild(x));
  if(r.escenarios&&r.escenarios.length){
    caja.appendChild(hE('section',{class:'herr-bloque'},hE('h4',{text:'Escenarios posibles'}),hE('ul',{id:'herr-t-escenarios'},r.escenarios.map(e=>hE('li',{text:
      (e.vacancia_judicial!==undefined?(e.vacancia_judicial?'Con':'Sin')+' vacancia judicial':'')+
      (e.semana_santa_judicial!==undefined?(e.vacancia_judicial!==undefined?', ':'')+(e.semana_santa_judicial?'con':'sin')+' cierre en Semana Santa':'')+
      ': vence el '+e.fecha_vencimiento_texto})))))}
  [hLista('Supuestos del cálculo',r.supuestos),hLista('Advertencias',r.advertencias,'adv'),
   hLista('Lo que decide un profesional',r.juicio_profesional),hNormas(r.normas)].forEach(x=>x&&caja.appendChild(x));
  if(r.cronologia&&r.cronologia.length){
    const tabla=hE('table',{class:'herr-tabla'},hE('caption',{text:'Cronología día por día'}),
      hE('thead',null,hE('tr',null,hE('th',{scope:'col',text:'Fecha'}),hE('th',{scope:'col',text:'Día'}),hE('th',{scope:'col',text:'Cuenta'}),hE('th',{scope:'col',text:'Observación'}))),
      hE('tbody',null,r.cronologia.map(c=>hE('tr',{class:c.cuenta!=null?'herr-si':'herr-no'},hE('td',{text:c.fecha}),hE('td',{text:c.dia}),
        hE('td',{text:c.cuenta!=null?String(c.cuenta):'—'}),hE('td',{text:c.motivo||''})))));
    caja.appendChild(hE('details',{class:'herr-det',open:r.cronologia.length<=45},hE('summary',{text:'Cronología ('+r.cronologia.length+' días)'}),
      hE('div',{class:'herr-scroll',tabindex:'0',role:'region','aria-label':'Cronología día por día'},tabla)))}
  caja.appendChild(hE('p',{class:'herr-aviso',text:r.aviso||''}));
  caja.appendChild(hE('div',{class:'herr-acc'},hBtn('Copiar resultado','',()=>herrCopiar(herrTextoTermino(r)),{id:'herr-t-copiar'}),
    hE('span',{class:'herr-meta',text:'Huella del cálculo: '+r.huella})));
  res.appendChild(caja);
  const inval=hMarcarFaltantes('herr-t-',r.faltantes);
  (r.estado==='CALCULADO'||!inval?titulo:inval).focus();
}

// --------------------------------------------------------------------------- liquidación --
function herrLiquidacionVista(){
  const p=document.getElementById('herr-panel-liquidacion'),L=HERR.opc.liquidacion;p.textContent='';
  const tipo=hSelect('herr-l-tipo',[['prestaciones','Prestaciones sociales'],['intereses_mora','Intereses de mora'],['indexacion','Indexación (IPC)']]);
  const conceptos=hE('fieldset',{class:'herr-fs'},hE('legend',{text:'Conceptos'}),L.conceptos.map(c=>hE('div',{class:'herr-check'},
    hE('input',{type:'checkbox',id:'herr-l-c-'+c.id,value:c.id,checked:true}),hE('label',{for:'herr-l-c-'+c.id,text:c.nombre}))));
  const prest=hE('div',{id:'herr-l-f-prestaciones'},
    hE('div',{class:'herr-campos'},
      hCampo('herr-l-fecha_inicio','Fecha de inicio del contrato',hInput('herr-l-fecha_inicio','date'),'',true),
      hCampo('herr-l-fecha_fin','Fecha final o de corte',hInput('herr-l-fecha_fin','date'),'Último día trabajado.',true),
      hCampo('herr-l-salario_mensual','Salario mensual base ($)',hInput('herr-l-salario_mensual','text',{inputmode:'decimal'}),
        'Tú indicas la base: la herramienta no supone salarios ni mínimos.',true),
      hCampo('herr-l-auxilio_transporte_mensual','Auxilio de transporte mensual ($)',hInput('herr-l-auxilio_transporte_mensual','text',{inputmode:'decimal'}),
        'Escribe 0 si no aplica. El valor oficial del año debes verificarlo tú.',true),
      hCampo('herr-l-auxilio_en_base_prestaciones','¿El auxilio entra en la base de cesantías y prima?',
        hSelect('herr-l-auxilio_en_base_prestaciones',[['','Elige…'],['si','Sí'],['no','No']]),'Obligatorio si el auxilio es mayor que 0 (regla no verificada).'),
      hCampo('herr-l-vacaciones_dias_tomados','Días de vacaciones ya disfrutados o pagados',hInput('herr-l-vacaciones_dias_tomados','text',{inputmode:'decimal'}),'')),
    conceptos);
  const periodos=hE('div',{class:'herr-filas',id:'herr-l-periodos'});
  const inter=hE('div',{id:'herr-l-f-intereses_mora',class:'hidden'},
    hE('div',{class:'herr-campos'},
      hCampo('herr-l-capital','Capital ($)',hInput('herr-l-capital','text',{inputmode:'decimal'}),'',true),
      hCampo('herr-l-clase','Clase de interés',hSelect('herr-l-clase',[['','Elige…']].concat(L.clases_interes.map(c=>[c.id,c.nombre]))),'',true),
      hCampo('herr-l-metodo','Método',hSelect('herr-l-metodo',[['','Elige…']].concat(L.metodos.map(m=>[m.id,m.nombre]))),
        'El interés legal civil siempre es simple.'),
      hCampo('herr-l-base_dias','Base de días del año',hSelect('herr-l-base_dias',[['','Elige…'],['360','360'],['365','365']]),'',true),
      hCampo('herr-l-fuente_tasas','Fuente de las tasas',hInput('herr-l-fuente_tasas','text',{maxlength:'300'}),
        'Ej.: certificación de la Superintendencia Financiera, con número y fecha.')),
    hE('fieldset',{class:'herr-fs'},hE('legend',{text:'Períodos de mora'}),
      hE('p',{class:'herr-ayuda',text:'En el interés moratorio comercial, la tasa de cada período es el interés bancario corriente efectivo anual; la herramienta lo multiplica por 1,5.'}),
      periodos,hBtn('Agregar período','',()=>herrFila(periodos,'herr-l-p',true).querySelector('input').focus())));
  const index=hE('div',{id:'herr-l-f-indexacion',class:'hidden'},hE('div',{class:'herr-campos'},
      hCampo('herr-l-valor_historico','Valor histórico ($)',hInput('herr-l-valor_historico','text',{inputmode:'decimal'}),'',true),
      hCampo('herr-l-ipc_inicial','IPC inicial',hInput('herr-l-ipc_inicial','text',{inputmode:'decimal'}),'Índice del mes inicial (DANE).',true),
      hCampo('herr-l-ipc_final','IPC final',hInput('herr-l-ipc_final','text',{inputmode:'decimal'}),'Índice del mes final (DANE).',true),
      hCampo('herr-l-periodo_inicial','Mes del índice inicial',hInput('herr-l-periodo_inicial','month'),''),
      hCampo('herr-l-periodo_final','Mes del índice final',hInput('herr-l-periodo_final','month'),''),
      hCampo('herr-l-fuente_ipc','Fuente de los índices',hInput('herr-l-fuente_ipc','text',{maxlength:'300'}),'Ej.: serie de empalme del IPC del DANE, consultada el…',true)));
  tipo.addEventListener('change',()=>{['prestaciones','intereses_mora','indexacion'].forEach(t=>
    document.getElementById('herr-l-f-'+t).classList.toggle('hidden',t!==tipo.value));
    if(tipo.value==='intereses_mora'&&!periodos.querySelector('.herr-fila'))herrFila(periodos,'herr-l-p',true);
    document.getElementById('herr-l-res').textContent=''});
  const form=hE('form',{class:'herr-form',novalidate:true,on:{submit:ev=>{ev.preventDefault();herrLiquidar()}}},
    hE('div',{class:'herr-campos'},hCampo('herr-l-tipo','¿Qué quieres liquidar?',tipo,'',true)),prest,inter,index,
    hE('div',{class:'herr-acc'},hE('button',{type:'submit',class:'herr-btn pri',id:'herr-l-calcular'},'Liquidar'),
      hBtn('Limpiar','',()=>{form.reset();periodos.textContent='';tipo.dispatchEvent(new Event('change'))})));
  p.appendChild(form);
  p.appendChild(hE('div',{id:'herr-l-res',class:'herr-res','aria-live':'polite'}));
}
async function herrLiquidar(){
  const boton=document.getElementById('herr-l-calcular'),res=document.getElementById('herr-l-res'),tipo=hVal('herr-l-tipo');
  const cuerpo={tipo};const pon=(k,id)=>{const v=hVal(id||'herr-l-'+k);if(v!=='')cuerpo[k]=v};
  if(tipo==='prestaciones'){['fecha_inicio','fecha_fin','salario_mensual','auxilio_transporte_mensual','vacaciones_dias_tomados'].forEach(k=>pon(k));
    const a=hVal('herr-l-auxilio_en_base_prestaciones');if(a)cuerpo.auxilio_en_base_prestaciones=a==='si';
    cuerpo.conceptos=[...document.querySelectorAll('#herr-l-f-prestaciones input[type=checkbox]:checked')].map(c=>c.value)}
  else if(tipo==='intereses_mora'){['capital','clase','metodo','base_dias','fuente_tasas'].forEach(k=>pon(k));
    cuerpo.periodos=herrFilas(document.getElementById('herr-l-periodos'))}
  else{['valor_historico','ipc_inicial','ipc_final','periodo_inicial','periodo_final','fuente_ipc'].forEach(k=>pon(k))}
  boton.disabled=true;boton.textContent='Calculando…';
  try{const r=await herrApi('/api/procedimientos/liquidacion',cuerpo);HERR.ultimo.liquidacion=r;herrPintarLiquidacion(r)}
  catch(e){res.textContent='';res.appendChild(hE('p',{class:'herr-error',role:'alert',text:e.message}))}
  boton.disabled=false;boton.textContent='Liquidar';
}
function herrTextoLiquidacion(r){
  const l=['LIQUIDACIÓN — PULLEX IA (J06 v'+r.version+', registro '+r.version_registro+')','Tipo: '+r.tipo,
    r.estado==='CALCULADO'?'Total: '+hPesos(r.total):'Estado: '+r.estado+' (sin liquidación)'];
  (r.desglose||[]).forEach(d=>l.push('- '+d.nombre+(d.periodo?' ['+d.periodo.desde+' a '+d.periodo.hasta+', '+d.dias+' días]':'')+': '+d.formula_valores+' = '+hPesos(d.valor)));
  if(r.total_con_capital!=null)l.push('Capital más intereses: '+hPesos(r.total_con_capital));
  if(r.parametros&&Object.keys(r.parametros).length){l.push('','Parámetros:');Object.entries(r.parametros).forEach(([k,v])=>{if(v!=null)l.push('- '+k+': '+v)})}
  if(r.redondeo)l.push('','Redondeo: '+r.redondeo.descripcion);
  [['Faltan',r.faltantes],['Contradicciones',r.contradicciones],['Supuestos',r.supuestos],['Advertencias',r.advertencias],
   ['Juicio profesional',r.juicio_profesional]].forEach(([t,xs])=>{if(xs&&xs.length){l.push('',t+':');xs.forEach(x=>l.push('- '+x))}});
  if(r.normas&&r.normas.length){l.push('','Normas:');r.normas.forEach(n=>l.push('- '+n.id+' v'+n.version+': '+n.norma+' ['+n.estado+']'+(n.enlace?' '+n.enlace:'')))}
  l.push('','Huella del cálculo: '+r.huella,r.aviso||'');return l.join('\n')}
function herrPintarLiquidacion(r){
  const res=document.getElementById('herr-l-res');res.textContent='';
  const titulo=hE('h3',{class:'herr-h',tabindex:'-1',text:r.estado==='CALCULADO'?'Resultado':r.estado==='ABSTENCION'?'Sin liquidación: faltan datos':'Datos contradictorios'});
  const caja=hE('div',{class:'herr-caja '+(r.estado==='CALCULADO'?'ok':'pend')},titulo);
  if(r.estado==='CALCULADO'){
    caja.appendChild(hE('p',{class:'herr-fecha',id:'herr-l-total',text:'Total: '+hPesos(r.total)}));
    if(r.total_con_capital!=null)caja.appendChild(hE('p',{class:'herr-meta',text:'Capital más intereses: '+hPesos(r.total_con_capital)}));
    const tabla=hE('table',{class:'herr-tabla'},hE('caption',{text:'Desglose'}),
      hE('thead',null,hE('tr',null,hE('th',{scope:'col',text:'Concepto'}),hE('th',{scope:'col',text:'Período y días'}),hE('th',{scope:'col',text:'Fórmula con valores'}),hE('th',{scope:'col',class:'num',text:'Valor'}))),
      hE('tbody',null,r.desglose.map(d=>hE('tr',null,hE('th',{scope:'row',text:d.nombre}),
        hE('td',{text:d.periodo?d.periodo.desde+' a '+d.periodo.hasta+' · '+d.dias+' días':'—'}),
        hE('td',{class:'formula',text:d.formula_valores+(d.valor_exacto?' = '+d.valor_exacto:'')}),hE('td',{class:'num',text:hPesos(d.valor)})))));
    caja.appendChild(hE('div',{class:'herr-scroll',tabindex:'0',role:'region','aria-label':'Desglose de la liquidación'},tabla));
    const ps=Object.entries(r.parametros||{}).filter(([,v])=>v!=null).map(([k,v])=>k.replace(/_/g,' ')+': '+v);
    const lp=hLista('Parámetros',ps);if(lp)caja.appendChild(lp);
    if(r.redondeo)caja.appendChild(hE('p',{class:'herr-meta',text:'Redondeo: '+r.redondeo.descripcion}))}
  [hLista('Qué falta',r.faltantes,'falta'),hLista('Contradicciones en los datos',r.contradicciones,'falta'),hLista('Supuestos del cálculo',r.supuestos),
   hLista('Advertencias',r.advertencias,'adv'),hLista('Lo que decide un profesional',r.juicio_profesional),hNormas(r.normas)].forEach(x=>x&&caja.appendChild(x));
  caja.appendChild(hE('p',{class:'herr-aviso',text:r.aviso||''}));
  caja.appendChild(hE('div',{class:'herr-acc'},hBtn('Copiar resultado','',()=>herrCopiar(herrTextoLiquidacion(r)),{id:'herr-l-copiar'}),
    hE('span',{class:'herr-meta',text:'Huella del cálculo: '+r.huella})));
  res.appendChild(caja);
  const inval=hMarcarFaltantes('herr-l-',r.faltantes);
  (r.estado==='CALCULADO'||!inval?titulo:inval).focus();
}
