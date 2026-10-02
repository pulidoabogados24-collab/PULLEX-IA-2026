// =========================================================================================
// PULLEX Biblioteca — catálogo navegable de los modelos jurídicos del Drive (pestaña de Documentos).
// Se carga después de documentos.js y usa sus utilidades (dE, dBtn, docApi, docTab, docAbrirMio,
// docAbrirTipo, docSubir) y las de app.js (toast, PERFIL). Sin JavaScript en línea: todo con
// addEventListener. Todo lo que llega del servidor se pinta con textContent (nunca innerHTML): los
// títulos y extractos vienen de archivos de Drive y se tratan como texto, no como HTML.
// =========================================================================================
const BIB={listo:false,resumen:null,pagina:1,turno:0,comparar:[],busq:null,ultima:null};
const BIB_FILTROS=[['clase','Tipo documental'],['area','Área'],['tipo','Tipo de escrito'],['tramite','Trámite'],
  ['autoridad','Autoridad'],['anio','Año'],['carpeta','Carpeta'],['estado','Procesamiento']];
const BIB_RELACION={duplicado_exacto:'Duplicado exacto',posible_duplicado:'Posible duplicado',homonimo:'Mismo nombre',
  version_similar:'Versión similar',titulo_parecido:'Título parecido'};
const BIB_SIN_VALOR=['por clasificar','no aplica'];

// ------------------------------------------------------------------------- utilidades --
function bibNumero(n){return Number(n||0).toLocaleString('es-CO')}
function bibPlural(n,uno,varios){return bibNumero(n)+' '+(n===1?uno:varios)}
function bibPanel(){return document.getElementById('doc-panel-biblioteca')}
function bibZona(id){return document.getElementById(id)}
// Las variantes llevan prefijo propio (bib-c-…): «aviso» y «ok» ya son clases globales de la app.
function bibChip(texto,variante){return dE('span',{class:'bib-chip'+(variante?' bib-c-'+variante:''),text:texto})}
// Chips de estado: siempre con texto (el color solo refuerza).
function bibChips(m){
  const c=dE('span',{class:'bib-chips'});
  c.appendChild(bibChip(m.estado_texto,bibClaseEstado(m.estado_procesamiento)));
  c.appendChild(bibChip(m.validacion_texto,m.validacion_juridica==='validado'?'ok':'aviso'));
  if(m.historico)c.appendChild(bibChip('Histórico','aviso'));
  if(m.incompleto)c.appendChild(bibChip('Ficha incompleta','aviso'));
  if(m.derechos==='redistribucion_por_confirmar'||m.derechos==='no_redistribuible')c.appendChild(bibChip('De un tercero'));
  if(m.acceso==='restringido')c.appendChild(bibChip('Solo administrador'));
  return c}
function bibClaseEstado(e){return {ENCONTRADO:'encontrado','LEÍDO':'leido','EXTRAÍDO':'extraido',INDEXADO:'indexado',VALIDADO:'validado',PENDIENTE:'pendiente'}[e]||'encontrado'}
function bibValor(v){return v==null||v===''?'Sin dato':String(v)}
function bibMeta(m){
  const partes=[m.clase_texto||m.clase];
  if(m.area&&!BIB_SIN_VALOR.includes(m.area))partes.push(m.area);
  if(m.tipo_escrito&&!BIB_SIN_VALOR.includes(m.tipo_escrito))partes.push(m.tipo_escrito);
  if(m.anio)partes.push(String(m.anio));
  return partes.join(' · ')}
// Enlace al original: solo https de Drive/Docs (el servidor ya lo filtra; aquí se comprueba otra vez).
function bibEnlaceDrive(url,texto){
  if(typeof url!=='string'||!/^https:\/\/(drive|docs)\.google\.com\//.test(url))return null;
  return dE('a',{class:'doc-btn bib-drive',href:url,target:'_blank',rel:'noopener noreferrer'},texto||'Abrir original en Drive')}

// --------------------------------------------------------------------------- arranque --
function bibInit(){
  const p=bibPanel();if(!p||BIB.listo)return;BIB.listo=true;p.textContent='';
  p.appendChild(dE('section',{class:'doc-bloque bib-intro','aria-label':'Qué hay en la biblioteca'},
    dE('h3',{class:'doc-h',text:'Biblioteca de modelos'}),
    dE('p',{id:'bib-resumen',class:'doc-desc','aria-live':'polite',text:'Cargando el catálogo…'}),
    dE('div',{id:'bib-cobertura'})));
  p.appendChild(dE('div',{id:'bib-lista'}));
  p.appendChild(dE('div',{id:'bib-trabajo'}));
  bibConstruirBuscador(bibZona('bib-lista'));
  bibCargarResumen();
}
async function bibCargarResumen(){
  try{const r=await docApi('/api/biblioteca/resumen');BIB.resumen=r;bibPintarResumen(r);bibLlenarFiltros(r);bibBuscar()}
  catch(e){bibZona('bib-resumen').textContent=e.message}
}
function bibPintarResumen(r){
  const otras=(r.por_clase||[]).filter(c=>c.clase!=='modelo');
  let t=r.modelos?'Hay '+bibPlural(r.modelos,'modelo jurídico disponible','modelos jurídicos disponibles')+' para tu cuenta (plantillas y minutas).'
    :'Todavía no hay modelos jurídicos (plantillas o minutas) disponibles para tu cuenta.';
  if(otras.length)t+=' El catálogo también tiene '+otras.map(c=>bibNumero(c.n)+' en «'+c.texto+'»').join(', ')+'.';
  t+=' Todo lo que aparece aquí es una referencia de trabajo: revisa cada documento antes de usarlo.';
  bibZona('bib-resumen').textContent=t;
  const c=bibZona('bib-cobertura');c.textContent='';
  const notas=((r.cobertura||{}).notas||[]).slice();
  if(r.busqueda&&r.busqueda.nota)notas.push('Búsqueda: '+r.busqueda.nota);
  if(r.texto_de_terceros==='solo administrador')notas.push('La vista previa del texto de un documento de terceros solo la ve el administrador.');
  if(notas.length)c.appendChild(dE('details',{class:'doc-det bib-cob',open:!r.modelos},dE('summary',{text:'Qué cubre hoy la biblioteca y qué falta'}),
    dE('ul',{class:'doc-lista'},...notas.map(n=>dE('li',{text:n})))));
  if(r.es_admin)c.appendChild(dE('div',{class:'doc-acc'},dBtn('Ver inventario completo (auditoría)','sec',bibAuditoria,{id:'bib-auditoria'})));
}

// --------------------------------------------------------------------------- buscador --
function bibConstruirBuscador(cont){
  const q=dE('input',{type:'search',id:'bib-q',class:'doc-inp',maxlength:300,autocomplete:'off',
    placeholder:'Ej.: petición fotomulta, tutela salud, «no me responden una solicitud»','aria-describedby':'bib-q-ayuda'});
  const form=dE('form',{class:'doc-bloque bib-form',role:'search','aria-label':'Buscar en la biblioteca',novalidate:true,
    on:{submit:ev=>{ev.preventDefault();BIB.pagina=1;bibBuscar()}}},
    dE('div',{class:'bib-q'},dE('label',{for:'bib-q',class:'doc-lb',text:'Buscar por nombre, contenido o describiendo el problema'}),
      dE('div',{class:'bib-q-fila'},q,dE('button',{type:'submit',class:'doc-btn pri',id:'bib-buscar'},'Buscar'))),
    dE('p',{class:'doc-ayuda',id:'bib-q-ayuda',text:'Busca por palabras, sinónimos jurídicos y trámites. Cada resultado dice por qué coincide.'}),
    dE('div',{class:'bib-filtros',id:'bib-filtros'},...BIB_FILTROS.map(([k,nombre])=>dE('div',{class:'bib-f'},
      dE('label',{for:'bib-f-'+k,text:nombre}),dE('select',{id:'bib-f-'+k,class:'doc-inp','data-filtro':k,
        on:{change:()=>{BIB.pagina=1;bibBuscar()}}})))),
    dE('div',{class:'doc-acc'},dBtn('Quitar filtros','sec',bibLimpiar,{id:'bib-limpiar'})));
  q.addEventListener('input',()=>{clearTimeout(BIB.busq);BIB.busq=setTimeout(()=>{BIB.pagina=1;bibBuscar()},300)});
  cont.appendChild(form);
  cont.appendChild(bibConstruirRecomendar());
  cont.appendChild(dE('div',{id:'bib-comparar-barra',class:'bib-barra hidden',role:'region','aria-label':'Modelos elegidos para comparar'}));
  cont.appendChild(dE('p',{id:'bib-n',class:'doc-n',role:'status','aria-live':'polite'}));
  cont.appendChild(dE('div',{id:'bib-otras'}));
  cont.appendChild(dE('ul',{id:'bib-resultados',class:'bib-resultados'}));
  // role=navigation en un <div>: la etiqueta <nav> ya tiene estilos globales (la barra de secciones de la app).
  cont.appendChild(dE('div',{id:'bib-paginas',class:'bib-paginas',role:'navigation','aria-label':'Páginas de resultados'}));
}
function bibLlenarFiltros(r){
  const f=r.facetas||{},et=r.etiquetas||{};
  const llenar=(k,primera,opciones)=>{const s=bibZona('bib-f-'+k);if(!s)return;const previo=s.value;s.textContent='';
    s.appendChild(dE('option',{value:''},primera));opciones.forEach(([v,t])=>s.appendChild(dE('option',{value:v},t)));
    if([...s.options].some(o=>o.value===previo))s.value=previo};
  const conN=(lista,nombre)=>(lista||[]).map(x=>[String(x.valor),(nombre?nombre(x.valor):x.valor)+' ('+bibNumero(x.n)+')']);
  const s=bibZona('bib-f-clase');s.textContent='';
  const clases=(f.clase||[]).map(x=>x.valor);
  ['modelo',...clases.filter(c=>c!=='modelo')].forEach(c=>{const n=(f.clase||[]).find(x=>x.valor===c);
    s.appendChild(dE('option',{value:c},((et.clase||{})[c]||c)+' ('+bibNumero(n?n.n:0)+')'))});
  s.appendChild(dE('option',{value:'todas'},'Todo el catálogo ('+bibNumero(r.total)+')'));
  llenar('area','Todas las áreas',conN(f.area));
  llenar('tipo','Todos los tipos',conN(f.tipo));
  llenar('tramite','Todos los trámites',conN(f.tramite));
  llenar('autoridad','Todas las autoridades',conN(f.autoridad));
  llenar('anio','Todos los años',conN(f.anio));
  llenar('carpeta','Todas las carpetas',conN(f.carpeta));
  llenar('estado','Cualquier estado',conN(f.estado,v=>(et.estado||{})[v]||v));
  const a=bibZona('bib-f-anio');if(a&&r.anio_nota)a.title=r.anio_nota;
}
function bibLimpiar(){bibZona('bib-q').value='';BIB_FILTROS.forEach(([k])=>{const s=bibZona('bib-f-'+k);if(s)s.value=k==='clase'?'modelo':''});
  BIB.pagina=1;bibBuscar();bibZona('bib-q').focus()}
function bibParametros(){
  const ps=new URLSearchParams();const q=bibZona('bib-q').value.trim();if(q)ps.set('q',q);
  BIB_FILTROS.forEach(([k])=>{const s=bibZona('bib-f-'+k);if(s&&s.value)ps.set(k,s.value)});
  if(BIB.pagina>1)ps.set('pagina',String(BIB.pagina));return ps}
async function bibBuscar(){
  clearTimeout(BIB.busq);
  // Solo se pinta la respuesta de la búsqueda más reciente (pueden llegar en desorden).
  const turno=++BIB.turno;const n=bibZona('bib-n');
  try{const d=await docApi('/api/biblioteca/buscar?'+bibParametros().toString());if(turno!==BIB.turno)return;BIB.ultima=d;bibPintarResultados(d)}
  catch(e){if(turno===BIB.turno){n.textContent=e.message;bibZona('bib-resultados').textContent=''}}
}
function bibPintarResultados(d){
  const n=bibZona('bib-n'),ul=bibZona('bib-resultados'),otras=bibZona('bib-otras');ul.textContent='';otras.textContent='';
  const et=((BIB.resumen||{}).etiquetas||{}).clase||{};const nombre=d.clase==='todas'?'documentos':(et[d.clase]||d.clase).toLowerCase();
  n.textContent=d.total?bibPlural(d.total,'resultado','resultados')+' en '+nombre+(d.paginas>1?' · página '+d.pagina+' de '+d.paginas:'')+
      ' · orden por '+d.orden:'Sin resultados en '+nombre+(d.q?' para «'+d.q+'»':'')+'.';
  const it=d.interpretacion;
  if(it&&(it.sinonimos.length||it.tramites.length))otras.appendChild(dE('p',{class:'bib-interp',text:'Se amplió la búsqueda'+
    (it.sinonimos.length?' con términos relacionados: '+it.sinonimos.slice(0,6).join(', '):'')+
    (it.tramites.length?(it.sinonimos.length?'; y':'')+' con el trámite que sugiere tu descripción: '+it.tramites.join(', '):'')+'.'}));
  if(d.otras_clases_detalle&&d.otras_clases_detalle.length){
    const caja=dE('div',{class:'bib-otras'},dE('span',{text:(d.total?'También coinciden':'Coinciden')+' en otros tipos documentales:'}));
    d.otras_clases_detalle.forEach(o=>caja.appendChild(dBtn(o.texto+' ('+bibNumero(o.n)+')','chip',()=>{bibZona('bib-f-clase').value=o.clase;BIB.pagina=1;bibBuscar()})));
    otras.appendChild(caja)}
  if(!d.total){ul.appendChild(dE('li',{class:'doc-vacio bib-vacio'},d.clase==='modelo'
    ?'No hay un modelo que coincida. La biblioteca no inventa uno parecido: prueba con otras palabras, describe tu caso en «Recomendar» o redacta un borrador nuevo en la pestaña Escritos.'
    :'No hay documentos con ese criterio. Prueba con otras palabras o quita los filtros.'))}
  d.resultados.forEach(m=>ul.appendChild(bibTarjeta(m)));
  bibPintarPaginas(d);bibPintarBarraComparar();
}
function bibTarjeta(m){
  const elegido=BIB.comparar.some(x=>x.id===m.id);
  const titulo=dE('button',{type:'button',class:'bib-titulo','data-id':m.id,on:{click:()=>bibAbrirFicha(m.id)}},m.titulo);
  const marca=dE('input',{type:'checkbox',id:'bib-cmp-'+m.id,class:'bib-cmp',checked:elegido,on:{change:ev=>bibAlternarComparar(m,ev.currentTarget)}});
  const li=dE('li',{class:'bib-item','data-id':m.id},
    dE('div',{class:'bib-item-cab'},dE('span',{class:'bib-id',text:m.id}),dE('span',{class:'bib-meta',text:bibMeta(m)})),
    titulo,bibChips(m),
    dE('p',{class:'bib-ruta',text:'Carpeta: '+m.ruta}));
  if(m.coincidencias&&m.coincidencias.length){
    const porque=dE('ul',{class:'bib-porque','aria-label':'Por qué coincide'});
    m.coincidencias.slice(0,4).forEach(c=>porque.appendChild(dE('li',null,c.texto,c.extracto?dE('q',{class:'bib-extracto',text:c.extracto}):null)));
    li.appendChild(porque)}
  li.appendChild(dE('div',{class:'bib-item-acc'},dBtn('Ver ficha','sec',()=>bibAbrirFicha(m.id)),
    dE('label',{class:'bib-cmp-l',for:'bib-cmp-'+m.id},marca,' Comparar')));
  return li}
function bibPintarPaginas(d){
  const nav=bibZona('bib-paginas');nav.textContent='';if(d.paginas<=1)return;
  const ir=p=>{BIB.pagina=p;bibBuscar().then(()=>{const n=bibZona('bib-n');if(n)n.scrollIntoView({block:'start'})})};
  nav.appendChild(dBtn('← Anterior','sec',()=>ir(d.pagina-1),{disabled:d.pagina<=1}));
  nav.appendChild(dE('span',{text:'Página '+d.pagina+' de '+d.paginas}));
  nav.appendChild(dBtn('Siguiente →','sec',()=>ir(d.pagina+1),{disabled:d.pagina>=d.paginas}));
}

// --------------------------------------------------------------------------- comparar --
function bibAlternarComparar(m,casilla){
  const i=BIB.comparar.findIndex(x=>x.id===m.id);
  if(i>=0)BIB.comparar.splice(i,1);
  else{if(BIB.comparar.length>=2){if(casilla)casilla.checked=false;toast('Solo se comparan dos documentos a la vez. Quita uno para elegir otro.');return}
    BIB.comparar.push({id:m.id,titulo:m.titulo})}
  bibPintarBarraComparar();
}
function bibPintarBarraComparar(){
  const b=bibZona('bib-comparar-barra');if(!b)return;b.textContent='';b.classList.toggle('hidden',!BIB.comparar.length);
  if(!BIB.comparar.length)return;
  b.appendChild(dE('span',{class:'bib-barra-t',text:BIB.comparar.length===2?'Listos para comparar:':'Elige otro documento para comparar con:'}));
  BIB.comparar.forEach(x=>b.appendChild(dBtn('Quitar «'+(x.titulo.length>38?x.titulo.slice(0,36)+'…':x.titulo)+'»','chip',()=>{
    BIB.comparar=BIB.comparar.filter(y=>y.id!==x.id);const c=bibZona('bib-cmp-'+x.id);if(c)c.checked=false;bibPintarBarraComparar()},{title:x.titulo})));
  b.appendChild(dBtn('Comparar','pri',bibComparar,{id:'bib-comparar',disabled:BIB.comparar.length!==2}));
}
async function bibComparar(){
  if(BIB.comparar.length!==2)return;
  let d;try{d=await docApi('/api/biblioteca/comparar?a='+encodeURIComponent(BIB.comparar[0].id)+'&b='+encodeURIComponent(BIB.comparar[1].id))}
  catch(e){toast(e.message);return}
  const w=bibModoTrabajo(true);
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:'Comparación de dos documentos'});
  const fila=(campo,a,b,igual)=>dE('tr',{class:igual?'':'bib-dif'},dE('th',{scope:'row',text:campo}),dE('td',{'data-l':'A',text:bibValor(a)}),dE('td',{'data-l':'B',text:bibValor(b)}),
    dE('td',{class:'bib-eq',text:igual?'Igual':'Distinto'}));
  const tabla=dE('table',{class:'bib-tabla'},dE('caption',{text:'Datos de cada ficha'}),
    dE('thead',null,dE('tr',null,dE('th',{scope:'col',text:'Campo'}),dE('th',{scope:'col',text:'A · '+d.a.id}),dE('th',{scope:'col',text:'B · '+d.b.id}),dE('th',{scope:'col',text:'¿Coinciden?'}))),
    dE('tbody',null,...d.metadatos.map(m=>fila(m.campo,m.a,m.b,m.igual))));
  const tres=(titulo,x)=>dE('div',{class:'bib-tres'},dE('h4',{text:titulo}),
    ...[['En los dos',x.comunes],['Solo en A',x.solo_a],['Solo en B',x.solo_b]].map(([t,l])=>dE('div',null,dE('h5',{text:t+' ('+l.length+')'}),
      l.length?dE('ul',{class:'doc-lista'},...l.map(v=>dE('li',{text:v}))):dE('p',{class:'doc-vacio',text:'Ninguno.'}))));
  const est=d.estructura;
  w.appendChild(dBtn('← Volver a los resultados','sec doc-volver',bibVolver));
  w.appendChild(dE('section',{class:'doc-bloque bib-comparacion','aria-label':'Comparación'},h,
    dE('p',{class:'doc-aviso',text:d.nota}),
    dE('div',{class:'bib-tabla-w'},tabla),
    tres('Datos que pide cada uno',d.campos_requeridos),
    est.disponible?dE('div',null,tres('Secciones del texto',est),
      dE('p',{class:'doc-costo',text:'Secciones en común: '+(est.similitud==null?'sin dato':est.similitud+' %')+' · longitud del texto: A '+bibNumero(est.longitud.a)+' caracteres, B '+bibNumero(est.longitud.b)+'.'}))
      :dE('p',{class:'doc-aviso',text:est.motivo}),
    dE('div',{class:'doc-acc'},dBtn('Ver ficha de A','sec',()=>bibAbrirFicha(d.a.id)),dBtn('Ver ficha de B','sec',()=>bibAbrirFicha(d.b.id)))));
  docSubir();h.focus();
}

// ------------------------------------------------------------------------------ ficha --
function bibModoTrabajo(on){bibZona('bib-lista').classList.toggle('hidden',on);const w=bibZona('bib-trabajo');w.textContent='';return w}
function bibVolver(){bibModoTrabajo(false);docSubir();const t=document.querySelector('#bib-resultados .bib-titulo');(t||bibZona('bib-q')).focus()}
function bibLista(titulo,items,vacio){
  return dE('div',{class:'bib-campo'},dE('dt',{text:titulo}),dE('dd',null,items&&items.length?dE('ul',{class:'doc-lista'},...items.map(x=>dE('li',{text:x}))):dE('span',{class:'bib-nd',text:vacio})))}
function bibDato(titulo,valor,nota){return dE('div',{class:'bib-campo'},dE('dt',{text:titulo}),dE('dd',null,bibValor(valor),nota?dE('span',{class:'bib-nota',text:' '+nota}):null))}
async function bibAbrirFicha(id){
  let f;try{f=await docApi('/api/biblioteca/modelo/'+encodeURIComponent(id))}catch(e){toast(e.message);return}
  if(typeof DOC!=='undefined'&&DOC.tab!=='biblioteca')docTab('biblioteca');
  const w=bibModoTrabajo(true);
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:f.titulo});
  const avisos=dE('div',{class:'bib-avisos'},...(f.avisos||[]).map(a=>dE('p',{class:'doc-aviso bib-aviso bib-aviso-'+a.codigo,role:'note',text:a.texto})));
  const acciones=dE('div',{class:'doc-acc bib-acc'});
  const drive=bibEnlaceDrive(f.enlace);
  if(drive)acciones.appendChild(drive);else acciones.appendChild(dE('span',{class:'bib-nd',text:'Sin enlace al original.'}));
  const esEscrito=!['norma','jurisprudencia','doctrina','otro'].includes(f.clase);
  if(esEscrito)acciones.appendChild(dBtn('Crear copia de trabajo','pri',ev=>bibCopiar(f,ev.currentTarget),{id:'bib-copiar'}));
  const enComparar=BIB.comparar.some(x=>x.id===f.id);
  acciones.appendChild(dBtn(enComparar?'Ya está en la comparación':'Comparar con otro','sec',()=>{
    if(!BIB.comparar.some(x=>x.id===f.id)){if(BIB.comparar.length>=2)BIB.comparar.shift();BIB.comparar.push({id:f.id,titulo:f.titulo})}
    bibVolver();bibPintarResultados(BIB.ultima||{total:0,resultados:[],paginas:1,pagina:1,clase:'modelo',orden:'título'});
    const b=bibZona('bib-comparar-barra');if(b)b.scrollIntoView({block:'nearest'})},{id:'bib-ficha-comparar'}));
  if(f.generador)acciones.appendChild(dBtn('Redactar uno nuevo con el generador','sec',()=>docAbrirTipo(f.generador.tipo)));
  const cl=f.clasificacion||{};
  const regla=k=>cl[k]?'('+cl[k].confianza+' · '+cl[k].regla+')':'';
  const datos=(f.datos_requeridos||[]).map(d=>d.etiqueta+({detectado_en_texto:' (detectado en el texto)',tipico_del_tipo:' (típico de este tipo de escrito; el archivo aún no se ha leído)',
    revisado_por_persona:' (revisado por una persona)'}[d.origen]||''));
  const dl=dE('dl',{class:'bib-ficha'},
    bibDato('ID del catálogo',f.id),
    bibDato('Tipo documental',f.clase_texto,regla('clase')),
    dE('div',{class:'bib-campo'},dE('dt',{text:'Finalidad'}),dE('dd',null,f.finalidad||dE('span',{class:'bib-nd',text:'Por describir: nadie ha redactado la finalidad de este documento.'}),
      f.finalidad_nota?dE('span',{class:'bib-nota',text:' '+f.finalidad_nota}):null)),
    bibDato('Área',f.area,regla('area')),
    bibDato('Tipo de escrito',f.tipo_escrito,regla('tipo_escrito')),
    bibDato('Trámite',f.tramite),
    bibDato(f.autoridad_rol==='expidió'?'Autoridad que lo expidió':'Autoridad ante la que se presenta',f.autoridad),
    bibDato('Año',f.anio,'(según '+f.anio_origen+'; no prueba vigencia)'),
    bibDato('Carpeta',f.ruta),
    bibLista('Supuestos de uso',f.supuestos_uso,'Por describir: nadie los ha redactado.'),
    bibLista('Límites',f.limites,'Sin límites registrados.'),
    bibLista('Datos que hay que completar',datos,'No se detectaron campos.'),
    bibLista('Anexos',f.anexos,'No detectados.'),
    bibLista('Fuentes citadas',(f.fuentes_citadas||[]).map(c=>c.cita+' — '+c.estado),'Ninguna detectada'+(f.vista_previa&&f.vista_previa.disponible?'.':' (el texto no se ha leído en este catálogo).')),
    bibDato('Fecha de revisión',f.fecha_revision||'Nunca revisado por una persona',f.revisor?'('+f.revisor+')':''),
    bibDato('Estado de validación',f.validacion_texto,f.validacion_nota||''),
    bibDato('Procesamiento',f.estado_texto,f.motivo||''),
    f.registro_inventario&&f.registro_inventario.texto?bibDato('Registro del inventario',f.registro_inventario.texto):null,
    bibDato('Sensibilidad',f.sensibilidad==='SIN_INDICIOS'?'Sin indicios de datos personales (revisión automática, no garantía)':f.sensibilidad),
    bibDato('Derechos',f.derechos_texto),
    bibDato('Archivo',[f.extension?'.'+f.extension:null,f.tamano?bibNumero(Math.max(1,Math.round(f.tamano/1024)))+' KB':null,
      f.modificado?'modificado el '+f.modificado:null].filter(Boolean).join(' · ')||'Sin dato',f.extraccion&&f.extraccion.nota?f.extraccion.nota:''),
    bibDato('Última comprobación en Drive',(f.ultima_comprobacion||'').slice(0,10)));
  const rel=dE('div',{class:'bib-rel'},dE('h4',{text:'Versiones relacionadas'}));
  if((f.versiones_relacionadas||[]).length){const ul=dE('ul',{class:'bib-rel-ul'});
    f.versiones_relacionadas.forEach(v=>ul.appendChild(dE('li',null,bibChip(BIB_RELACION[v.relacion]||v.relacion),
      dE('button',{type:'button',class:'bib-titulo',on:{click:()=>bibAbrirFicha(v.id)}},v.titulo),
      dE('span',{class:'bib-nota',text:' '+v.id+' · '+v.ruta+'. '+v.detalle}),
      dBtn('Comparar con este','chip',()=>{BIB.comparar=[{id:f.id,titulo:f.titulo},{id:v.id,titulo:v.titulo}];bibComparar()}))));rel.appendChild(ul)}
  else rel.appendChild(dE('p',{class:'doc-vacio',text:'No se encontraron homónimos, duplicados ni versiones similares entre los documentos que puedes ver.'}));
  const vp=f.vista_previa||{};
  const previa=dE('div',{class:'bib-previa'},dE('h4',{text:'Vista previa'}),
    vp.disponible?dE('div',null,dE('p',{class:'bib-previa-t',text:vp.texto}),dE('p',{class:'doc-costo',text:'Es solo el comienzo del texto extraído. El documento completo está en Drive.'}))
      :dE('p',{class:'doc-vacio',text:vp.motivo||'Sin vista previa: aún no extraído.'}));
  w.appendChild(dBtn('← Volver a los resultados','sec doc-volver',bibVolver));
  w.appendChild(dE('article',{class:'doc-bloque bib-ficha-w','data-id':f.id,'aria-label':'Ficha del documento'},
    dE('p',{class:'doc-card-area',text:f.id+' · '+bibMeta(f)}),h,bibChips(f),avisos,acciones,dE('div',{id:'bib-copia-res','aria-live':'polite'}),previa,dl,rel,
    (f.alertas||[]).length?dE('div',{class:'doc-adv'},dE('h4',{text:'Alertas para el administrador'}),dE('ul',null,...f.alertas.map(a=>dE('li',{text:a})))):null));
  docSubir();h.focus();
}
async function bibCopiar(f,boton){
  boton.disabled=true;const t0=boton.textContent;boton.textContent='Creando la copia…';
  try{const c=await docApi('/api/biblioteca/modelo/'+encodeURIComponent(f.id)+'/copia',{method:'POST',body:{}});
    const z=bibZona('bib-copia-res');if(z){z.textContent='';z.appendChild(dE('div',{class:'doc-verif bib-copia'},dE('h4',{text:'Copia de trabajo creada'}),
      dE('p',{text:c.mensaje+' Quedó en «Mis documentos» como «'+c.titulo+'». El original en Drive no se modificó.'}),
      dE('div',{class:'doc-acc'},dBtn('Abrir la copia','pri',()=>{docTab('mis');docAbrirMio(c.id)},{id:'bib-abrir-copia'}))))}
    toast('Copia de trabajo creada en Mis documentos')}
  catch(e){toast(e.message)}
  boton.disabled=false;boton.textContent=t0;
}

// ------------------------------------------------------------------------- recomendar --
function bibConstruirRecomendar(){
  const ta=dE('textarea',{id:'bib-caso',class:'doc-inp',rows:3,maxlength:4000,'aria-describedby':'bib-caso-ayuda'});
  const err=dE('p',{class:'doc-err hidden',id:'bib-caso-err'});
  const ia=dE('input',{type:'checkbox',id:'bib-explicar'});
  const boton=dBtn('Recomendar modelos','pri',()=>bibRecomendar(ta,err,ia,boton),{id:'bib-recomendar'});
  return dE('details',{class:'doc-det bib-rec',id:'bib-rec'},dE('summary',{text:'¿No sabes qué modelo necesitas? Describe tu caso'}),
    dE('label',{for:'bib-caso',class:'doc-lb',text:'Cuenta en una o dos frases qué pasó y qué quieres pedir'}),
    dE('p',{class:'doc-ayuda',id:'bib-caso-ayuda',text:'La recomendación busca entre los modelos de la biblioteca y no usa consultas. Si no hay un modelo adecuado, lo dice: no fuerza uno parecido.'}),
    ta,err,dE('label',{class:'bib-cmp-l',for:'bib-explicar'},ia,' Pedir además una explicación redactada por IA (usa 1 consulta; solo si hay candidatos)'),
    dE('div',{class:'doc-acc'},boton),dE('div',{id:'bib-rec-res','aria-live':'polite'}));
}
async function bibRecomendar(ta,err,ia,boton){
  const v=ta.value.trim();
  if(v.length<15){ta.setAttribute('aria-invalid','true');err.textContent='Describe el caso con un poco más de detalle.';err.classList.remove('hidden');
    ta.setAttribute('aria-describedby','bib-caso-ayuda bib-caso-err');ta.focus();return}
  ta.removeAttribute('aria-invalid');err.classList.add('hidden');ta.setAttribute('aria-describedby','bib-caso-ayuda');
  boton.disabled=true;const t0=boton.textContent;boton.textContent='Buscando modelos…';
  const z=bibZona('bib-rec-res');
  try{const d=await docApi('/api/biblioteca/recomendar',{body:{caso:v,explicar:ia.checked}});z.textContent='';
    z.appendChild(dE('p',{class:d.hay_modelo_adecuado?'doc-estado':'doc-aviso',id:'bib-rec-msg',text:d.mensaje}));
    (d.candidatos||[]).forEach(c=>{
      const bloque=(t,l)=>l&&l.length?dE('div',null,dE('h5',{text:t}),dE('ul',{class:'doc-lista'},...l.map(x=>dE('li',{text:x})))):null;
      z.appendChild(dE('article',{class:'bib-item bib-cand','data-id':c.id},
        dE('div',{class:'bib-item-cab'},dE('span',{class:'bib-id',text:c.id}),bibChip('Plantilla recuperada de la biblioteca')),
        dE('button',{type:'button',class:'bib-titulo',on:{click:()=>bibAbrirFicha(c.id)}},c.titulo),bibChips(c),
        bloque('Por qué corresponde',c.por_que),bloque('Datos que el modelo pide y no veo en tu descripción',c.requisitos_faltantes),
        bloque('Qué hay que adaptar',c.adaptacion),
        dE('div',{class:'bib-item-acc'},dBtn('Ver ficha','sec',()=>bibAbrirFicha(c.id)))))});
    const ex=d.explicacion;
    if(d.explicacion_estado==='generada'&&ex)z.appendChild(dE('div',{class:'doc-verif'},dE('h4',{text:'Explicación redactada por IA'}),dE('p',{class:'doc-costo',text:ex.aviso}),
      ...ex.candidatos.map(c=>dE('p',null,dE('b',{text:c.id+': '}),c.por_que)),ex.nota?dE('p',{text:ex.nota}):null));
    else if(d.explicacion_estado==='fallida')z.appendChild(dE('p',{class:'doc-error',role:'alert',text:d.explicacion_error}));
    else if(d.explicacion_estado==='sin_motor')z.appendChild(dE('p',{class:'doc-aviso',text:'La explicación con IA no está disponible: el motor no está configurado. La recomendación de arriba no depende de la IA.'}));
    const nuevo=d.borrador_nuevo||{};
    if((nuevo.tipos||[]).length)z.appendChild(dE('div',{class:'bib-nuevo'},dE('h5',{text:d.hay_modelo_adecuado?'O redacta un borrador nuevo con el generador':'Redacta un borrador nuevo con el generador'}),
      dE('p',{class:'doc-costo',text:nuevo.nota}),
      dE('div',{class:'doc-acc'},...nuevo.tipos.map(t=>dBtn(t.nombre,'sec',()=>docAbrirTipo(t.tipo),{'data-generador':t.tipo})))));
    else if(!d.hay_modelo_adecuado)z.appendChild(dE('p',{class:'doc-costo',text:(nuevo.nota||'')+' Búscalo en la pestaña Escritos.'}))}
  catch(e){z.textContent='';z.appendChild(dE('p',{class:'doc-error',role:'alert',text:e.message}))}
  boton.disabled=false;boton.textContent=t0;
}

// -------------------------------------------------------------------- auditoría (admin) --
async function bibAuditoria(){
  let a;try{a=await docApi('/api/biblioteca/auditoria?por_pagina=100')}catch(e){toast(e.message);return}
  const w=bibModoTrabajo(true);
  const h=dE('h3',{class:'doc-h',tabindex:'-1',text:'Inventario completo (solo administrador)'});
  const conteo=(titulo,o,nombre)=>dE('div',{class:'bib-campo'},dE('dt',{text:titulo}),dE('dd',{text:Object.entries(o||{}).map(([k,v])=>(nombre?nombre(k):k)+': '+bibNumero(v)).join(' · ')||'Sin datos'}));
  const et=(BIB.resumen||{}).etiquetas||{};
  const ocultos=a.elementos.filter(e=>!e.visible_para_usuarios);
  w.appendChild(dBtn('← Volver a los resultados','sec doc-volver',bibVolver));
  w.appendChild(dE('section',{class:'doc-bloque','aria-label':'Auditoría de la biblioteca'},h,
    dE('p',{class:'doc-aviso',text:'Denominador del inventario: '+a.denominador+'. '+(String(a.denominador).startsWith('COMPLETO')?'':'Aún no se ha podido listar todo el Drive: estas cantidades son un mínimo.')}),
    dE('dl',{class:'bib-ficha'},
      bibDato('Archivos en el catálogo',bibNumero(a.total),'('+bibNumero(a.visibles_para_usuarios)+' visibles para los usuarios; '+bibNumero(a.retirados)+' retirados)'),
      conteo('Procesamiento en este catálogo',a.por_estado,k=>(et.estado||{})[k]||k),
      conteo('Según el inventario de Drive (procesado fuera)',a.por_estado_inventario),
      conteo('Tipo documental',a.por_clase,k=>(et.clase||{})[k]||k),conteo('Validación jurídica',a.por_validacion,k=>(et.validacion||{})[k]||k),
      conteo('Acceso',a.por_acceso),conteo('Sensibilidad',a.por_sensibilidad),conteo('Derechos',a.por_derechos),
      dE('div',{class:'bib-campo'},dE('dt',{text:'Por carpeta de primer nivel'}),dE('dd',null,dE('ul',{class:'doc-lista'},
        ...Object.entries(a.por_carpeta||{}).map(([c,e])=>dE('li',{text:c+' — '+Object.entries(e).map(([k,v])=>k+': '+bibNumero(v)).join(', ')}))))),
      bibDato('Última sincronización',(a.ultima_sincronizacion||'').replace('T',' ').slice(0,16),'reglas '+(a.reglas_version||''))),
    dE('h4',{text:'Lo que los usuarios NO ven (primeros '+ocultos.length+')'}),
    ocultos.length?dE('ul',{class:'bib-resultados'},...ocultos.map(e=>dE('li',{class:'bib-item'},dE('div',{class:'bib-item-cab'},dE('span',{class:'bib-id',text:e.id}),
      dE('span',{class:'bib-meta',text:'acceso '+e.acceso+' · '+e.sensibilidad+(e.retirado?' · retirado':'')})),dE('b',{text:e.titulo}),
      dE('p',{class:'bib-ruta',text:(e.motivo||e.retiro_motivo||'Sin motivo registrado')+' · Carpeta: '+e.ruta})))):dE('p',{class:'doc-vacio',text:'Nada oculto en esta página.'})));
  docSubir();h.focus();
}
