// Si el CDN falla o su contenido no coincide con la huella (integrity), las librerías no
// cargan: la app sigue funcionando y muestra las respuestas como texto plano seguro.
const LIBS_OK=typeof marked!=='undefined'&&typeof DOMPurify!=='undefined';
if(LIBS_OK)marked.setOptions({breaks:true});
const $=id=>document.getElementById(id);
let TOKEN=null, PERFIL=null, CONV=null, ESTADO=null, ADJ=[], WEB=true, enviando=false;
function auth(){return {'Authorization':'Bearer '+TOKEN}}
// Si el intérprete de markdown falla con un texto, se muestra como texto plano seguro: la respuesta no se pierde y
// el envío no queda a medias por un error de pintado.
function md(t){if(LIBS_OK){try{return DOMPurify.sanitize(marked.parse(t||''))}catch(e){}}return esc(t).replace(/\n/g,'<br>')}
function esc(t){return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')}
// Aviso breve. Entra y sale con su propia animación (static/movimiento.css); se retira por tiempo, nunca esperando a
// un «animationend» que podría no llegar. Un aviso nuevo reemplaza al anterior en vez de encimarse.
function toast(m){document.querySelectorAll('.toast').forEach(x=>x.remove());
  const t=document.createElement('div');t.className='toast';t.setAttribute('role','status');t.textContent=m;
  document.body.appendChild(t);
  // Tiempo para leerlo: 1,5 s para verlo más 60 ms por carácter (unos 16 caracteres por segundo), entre 2,6 y 10 s.
  // Los avisos de error del servidor pasan de 100 caracteres: con el tope anterior de 6 s no alcanzaban a leerse.
  const visible=Math.min(10000,Math.max(2600,1500+String(m||'').length*60));
  setTimeout(()=>{t.classList.add('sale');setTimeout(()=>t.remove(),180)},visible)}
// Estado de trabajo REAL de la app, a la vista del CSS (static/movimiento.css): 'ingreso' | 'espera' | 'fuentes' |
// 'escribe', o nada. Solo se enciende desde los puntos donde de verdad se espera al servidor o llega el stream.
function trabajo(e){const r=document.documentElement;if(e){if(r.getAttribute('data-trabajo')!==e)r.setAttribute('data-trabajo',e)}else r.removeAttribute('data-trabajo')}

let modoActual='ingresar';
function modoAuth(m){modoActual=m;
  $('t-ing').classList.toggle('on',m==='ingresar');$('t-reg').classList.toggle('on',m==='registrar');
  $('f-reg').classList.toggle('hidden',m!=='registrar');
  $('a-olvido').classList.toggle('hidden',m!=='ingresar');
  $('a-btn').textContent=m==='registrar'?'Crear cuenta':'Ingresar';$('a-msg').textContent=''}
function abrirRecuperar(){$('m-recuperar').classList.remove('hidden');$('rec-msg').className='msg-e';$('rec-msg').textContent='';
  $('rec-email').value=$('a-email').value||'';}
function cerrarRecuperar(){$('m-recuperar').classList.add('hidden')}
async function enviarRecuperar(){
  const email=$('rec-email').value.trim();
  if(!email){$('rec-msg').className='msg-e';$('rec-msg').textContent='Escribe tu correo.';return}
  $('rec-btn').disabled=true;$('rec-btn').textContent='Enviando…';
  try{
    await fetch('/api/recuperar-clave',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({email})});
    $('rec-msg').className='msg-e';$('rec-msg').style.color='var(--ok)';
    $('rec-msg').textContent='Si ese correo tiene una cuenta, te llegará un enlace en unos minutos. Revisa también spam.';
  }catch(e){
    $('rec-msg').className='msg-e';$('rec-msg').style.color='';
    $('rec-msg').textContent='Error de conexión. Intenta de nuevo.';
  }
  $('rec-btn').disabled=false;$('rec-btn').textContent='Enviar enlace';
}
async function enviarAuth(){
  const b=$('a-btn');if(b.disabled)return;
  const email=$('a-email').value.trim(), clave=$('a-clave').value;$('a-msg').textContent='';
  const url=modoActual==='registrar'?'/api/registro':'/api/login';
  const cuerpo=modoActual==='registrar'?{nombre:$('r-nombre').value,email,clave}:{email,clave};
  // Mientras el servidor responde, el botón lo dice y no admite otro clic.
  b.disabled=true;b.setAttribute('aria-busy','true');
  b.textContent=modoActual==='registrar'?'Creando tu cuenta…':'Ingresando…';trabajo('ingreso');
  let d=null;
  try{
    const r=await fetch(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(cuerpo)});
    d=await r.json();
    if(!r.ok){$('a-msg').textContent=d.detail||'No se pudo';d=null}
  }catch(e){$('a-msg').textContent='Error de conexión';d=null}
  // El rótulo sale del modo que está a la vista AHORA: si la persona cambió de pestaña mientras se esperaba, el botón
  // no puede quedar diciendo «Ingresar» en el formulario de crear cuenta.
  b.disabled=false;b.removeAttribute('aria-busy');b.textContent=modoActual==='registrar'?'Crear cuenta':'Ingresar';trabajo(null);
  if(d){TOKEN=d.token;PERFIL=d.perfil;iniciar()}
}
const CAPACIDADES=[
  {ic:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',t:'Investigación normativa',
   d:'Identifica normas aplicables y contrasta líneas jurisprudenciales.',
   p:'Necesito investigar qué normas y jurisprudencia aplican a mi caso. Pregúntame primero de qué se trata.'},
  {ic:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6"/>',
   t:'Documentos y flujos',d:'Escritos de todas las áreas, flujos de varios pasos y un asistente que investiga, analiza y redacta.',
   ir:'documentos'},
  {ic:'<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
   t:'Análisis de casos',d:'Hechos, pretensiones, riesgos y estrategia.',
   p:'Quiero que analices mi caso. Pregúntame los hechos, qué pretendo lograr, y evalúa riesgos y estrategia.'},
  {ic:'<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>',
   t:'Cálculos jurídicos',d:'Liquidaciones laborales, términos procesales e intereses.',
   p:'Ayúdame con un cálculo jurídico (liquidación laboral, término procesal o intereses). Pregúntame los datos.'},
];
async function iniciar(){
  $('auth').classList.add('hidden');$('app').classList.remove('hidden');
  try{ESTADO=await(await fetch('/api/estado',{headers:auth()})).json();PERFIL=ESTADO.perfil;}catch(e){}
  apIniciar();aplicarPerfil();
  $('modo').value=PERFIL.preferencias.modo||'auto';
  WEB=PERFIL.preferencias.web!==false;pintarWeb();cargarBoletin(false);elegirCamino(PERFIL.preferencias.camino||'aprender');
}
function iniciales(n){return (n||'').trim().split(/\s+/).filter(Boolean).slice(0,2).map(x=>x[0]).join('').toUpperCase()||'·'}
function saludoHora(){const h=new Date().getHours();return h<5?'Buenas noches':h<12?'Buenos días':h<19?'Buenas tardes':'Buenas noches'}
function aplicarPerfil(){
  $('h-nombre').textContent=(PERFIL.nombre||'estudiante').trim().split(/\s+/)[0];
  $('h-saludo').textContent=saludoHora();$('pv-saludo').textContent=saludoHora()+'.';
  try{const f=new Date().toLocaleDateString('es-CO',{weekday:'long',day:'numeric',month:'long'});$('h-fecha').textContent=f.charAt(0).toUpperCase()+f.slice(1)}catch(e){}
  ['h-iniciales','cf-iniciales','pv-iniciales'].forEach(id=>{$(id).textContent=iniciales(PERFIL.nombre)});
  $('c-plan').textContent=PERFIL.plan_nombre;$('c-rest').textContent=PERFIL.restantes;
  $('cf-nombre').textContent=PERFIL.nombre;$('cf-email').textContent=PERFIL.email;
  $('cf-plan').textContent=PERFIL.plan_nombre;$('cf-uso').textContent=PERFIL.usadas+' / '+PERFIL.limite;
  $('cf-modo').value=PERFIL.preferencias.modo||'auto';
  if($('cf-escritura'))$('cf-escritura').value=PERFIL.preferencias.escritura||'auto';
  $('cf-web').classList.toggle('on',PERFIL.preferencias.web!==false);
  sincronizarSwTema();
  $('cf-memoria').value=PERFIL.preferencias.memoria||'';
  $('banner-verif').classList.toggle('hidden',PERFIL.email_verificado!==false);
  pintarAreas();pintarPlanes();
}
function pintarAreas(){
  const cont=$('areas');cont.innerHTML='';const sel=PERFIL.preferencias.areas||[];
  (ESTADO.areas||[]).forEach(a=>{const el=document.createElement('div');
    el.className='area'+(sel.includes(a)?' on':'');el.textContent=a;
    el.onclick=()=>{el.classList.toggle('on');guardarPrefs()};cont.appendChild(el)});
}
function pintarPlanes(){
  // Acceso por plan (static/planes.js): candados en la navegación y tabla comparativa.
  if(typeof pintarTablaPlanes==='function'){pintarCandados();pintarTablaPlanes();return}
  const p=ESTADO.planes||{};const c=$('planes');c.innerHTML='';
  ['basico','pro','premium'].forEach(k=>{if(!p[k])return;const el=document.createElement('div');el.className='fila';
    el.innerHTML=`<div><div class="t">${p[k].nombre}</div><div class="d">${p[k].limite} consultas/mes</div></div>
      <div class="t" style="color:var(--accent-text);font-weight:650;font-variant-numeric:tabular-nums">$${p[k].precio.toLocaleString('es-CO')}</div>`;c.appendChild(el)});
}
let TURNO_VER=0;   // sube en cada cambio de sección; verNav() lo usa para no aplicar un cambio que ya quedó viejo
function ver(v){const nav=v==='perfiles'?'config':v;   // Perfiles se abre desde Ajustes y no tiene botón propio en la barra
  TURNO_VER++;
  // Función que el plan no incluye: se marca su pestaña y se muestra la pantalla de mejora (planes.js).
  const bloq=typeof vistaBloqueada==='function'&&vistaBloqueada(v);
  ['inicio','modular','mapa','chat','documentos','herramientas','config'].forEach(x=>{
  $('v-'+x).classList.toggle('on',x===v&&!bloq);$('n-'+x).classList.toggle('on',x===nav);
  if(x===nav)$('n-'+x).setAttribute('aria-current','page');else $('n-'+x).removeAttribute('aria-current')});
  const vp=$('v-perfiles');if(vp)vp.classList.toggle('on',v==='perfiles'&&!bloq);
  pintarUbicacion(v,nav);
  if($('v-mejora'))$('v-mejora').classList.toggle('on',!!bloq);
  const m=document.querySelector('main');if(m)m.scrollTop=0;
  if(bloq){cerrarHistorial();pintarMejora(VISTA_FUNCION[v]);return}
  if(v==='chat')cargarConvs();else cerrarHistorial();
  if(v==='modular')mlInit();
  if(v==='mapa')mapaInit();
  if(v==='documentos'&&typeof docInit==='function')docInit();
  if(v==='herramientas'&&typeof herrInit==='function')herrInit();
  if(v==='perfiles'&&typeof perInit==='function')perInit();
  if(v==='inicio')cargarProgresoInicio();}

// Miga «Espacio de trabajo / <sección>» (escritorio) y menú «Más» de la barra inferior (móvil): el nombre sale
// del propio botón de la sección, para no repetir la lista en otro sitio.
const NAV_MAS=['mapa','herramientas','config'];
function pintarUbicacion(v,nav){
  const b=$('n-'+nav),m=$('miga-seccion');
  if(m&&b){const t=b.querySelector('.l-largo')||b.querySelector('span');m.textContent=v==='perfiles'?'Ajustes · Perfiles':(t?t.textContent:'')}
  const mas=$('n-mas');if(mas)mas.classList.toggle('on',NAV_MAS.includes(nav));
  cerrarMas();
}
function toggleMas(){const c=$('nav-mas'),b=$('n-mas');if(!c||!b)return;
  const abierto=c.classList.toggle('abierto');b.setAttribute('aria-expanded',String(abierto));
  if(abierto){const p=c.querySelector('button');if(p)p.focus()}}
function cerrarMas(){const c=$('nav-mas'),b=$('n-mas');if(!c||!b||!c.classList.contains('abierto'))return false;
  c.classList.remove('abierto');b.setAttribute('aria-expanded','false');return true}
document.addEventListener('click',ev=>{if(!ev.target.closest('#n-mas,#nav-mas'))cerrarMas()});
document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&cerrarMas())$('n-mas').focus()});

async function cargarBoletin(forzar){
  if(forzar)$('boletin').innerHTML='<div class="skel" style="width:90%"></div><div class="skel" style="width:75%"></div>';
  try{
    const admin=forzar&&PERFIL.es_admin;
    const d=await(await fetch(admin?'/api/admin/boletin/regenerar':'/api/boletin',
      {method:admin?'POST':'GET',headers:auth()})).json();
    $('boletin').innerHTML=md(d.contenido);$('b-fecha').textContent=d.fecha?('· '+d.fecha):'';
  }catch(e){$('boletin').textContent='No se pudo cargar el boletín.'}
}

function pintarWeb(){$('chip-web').classList.toggle('on',WEB);$('chip-web').setAttribute('aria-pressed',String(WEB))}
function toggleWeb(){WEB=!WEB;pintarWeb()}
function autoAlto(t){t.style.height='auto';t.style.height=Math.min(t.scrollHeight,150)+'px'}
function teclas(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();enviar()}}
function sug(b){const s=b.querySelector('span');$('txt').value=s?s.textContent:b.textContent;autoAlto($('txt'));$('txt').focus()}
// La conversación se crea en el servidor al enviar el primer mensaje (no al abrir el chat),
// para que el historial no se llene de consultas vacías.
async function nuevaConv(){
  try{const d=await(await fetch('/api/conversaciones',{method:'POST',headers:auth()})).json();
    CONV=d.id;}catch(e){}
}

// ------------------------------------------------------------ historial de consultas --
let CONVS=[], CARGA_CONV=0;
const ICO_BORRAR='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6M10 11v6M14 11v6"/></svg>';
function esEscritorio(){return window.matchMedia('(min-width:760px)').matches}
function toggleHistorial(){$('chat-lay').classList.toggle('hist-abierto')}
function cerrarHistorial(){$('chat-lay').classList.remove('hist-abierto')}
async function cargarConvs(){
  const l=$('convs-lista');
  if(!l.children.length){for(let i=0;i<4;i++){const k=el('div','skel');k.style.cssText='height:12px;margin:12px 10px;width:'+(80-i*12)+'%';l.appendChild(k)}}
  try{CONVS=await api('/api/conversaciones');pintarConvs()}catch(e){if(l.querySelector('.skel'))l.textContent=''}
}
function pintarConvs(){
  const l=$('convs-lista');l.textContent='';
  if(!CONVS.length){const v=document.createElement('div');v.className='convs-vacio';
    const b=document.createElement('b');b.textContent='Aún no tienes consultas guardadas';v.appendChild(b);
    v.appendChild(document.createTextNode('Cuando escribas tu primera consulta, aparecerá aquí para que la retomes cuando quieras.'));
    l.appendChild(v);return}
  CONVS.forEach(c=>{
    const f=document.createElement('div');f.className='conv'+(c.id===CONV?' on':'');
    const t=document.createElement('button');t.className='conv-t';t.type='button';
    t.textContent=c.titulo||'Consulta';t.title=c.titulo||'';
    if(c.id===CONV)t.setAttribute('aria-current','true');
    t.addEventListener('click',()=>abrirConv(c.id));
    const x=document.createElement('button');x.className='conv-x';x.type='button';
    x.title='Borrar consulta';x.setAttribute('aria-label','Borrar consulta');x.innerHTML=ICO_BORRAR;
    x.addEventListener('click',()=>confirmarBorrado(c));
    f.appendChild(t);f.appendChild(x);l.appendChild(f);
  });
}
function confirmarBorrado(c){
  if(enviando&&c.id===CONV){toast('Espera a que termine la respuesta para borrar esta consulta.');return}
  pintarConvs(); // cierra cualquier otra confirmación abierta
  const destino=[...$('convs-lista').children][CONVS.indexOf(c)];if(!destino)return;
  const k=document.createElement('div');k.className='conv-conf';
  const p=document.createElement('p');p.textContent='¿Borrar «'+(c.titulo||'Consulta')+'»? No se puede deshacer.';
  const acc=document.createElement('div');
  const no=document.createElement('button');no.type='button';no.className='bsec';no.textContent='Cancelar';
  no.addEventListener('click',pintarConvs);
  const si=document.createElement('button');si.type='button';si.className='borrar';si.textContent='Borrar';
  si.addEventListener('click',()=>borrarConv(c.id,si));
  acc.appendChild(no);acc.appendChild(si);k.appendChild(p);k.appendChild(acc);
  destino.replaceWith(k);si.focus();
}
async function borrarConv(id,boton){
  if(boton){boton.disabled=true;boton.textContent='Borrando…'}
  try{
    const r=await fetch('/api/conversaciones/'+id,{method:'DELETE',headers:auth()});
    if(!r.ok&&r.status!==404)throw new Error();
    CONVS=CONVS.filter(c=>c.id!==id);
    if(id===CONV)nuevaConsulta();else pintarConvs();
    toast('Consulta borrada');
  }catch(e){toast('No se pudo borrar. Intenta de nuevo.');pintarConvs()}
}
function nuevaConsulta(){
  if(enviando){toast('Espera a que termine la respuesta actual.');return false}
  CARGA_CONV++;CONV=null;$('hilo').innerHTML='';$('sugs').classList.remove('hidden');
  pintarConvs();cerrarHistorial();
  if(esEscritorio()&&$('v-chat').classList.contains('on'))$('txt').focus();
  return true;
}
async function abrirConv(id){
  if(id===CONV&&$('hilo').children.length){cerrarHistorial();return}
  if(enviando){toast('Espera a que termine la respuesta actual.');return}
  const turno=++CARGA_CONV;CONV=id;pintarConvs();cerrarHistorial();
  $('sugs').classList.add('hidden');
  $('hilo').innerHTML='<div class="skel" style="width:70%;margin-top:20px"></div><div class="skel" style="width:88%"></div><div class="skel" style="width:60%"></div>';
  try{
    const msgs=await api('/api/conversaciones/'+id+'/mensajes');
    if(turno!==CARGA_CONV)return; // el usuario ya abrió otra
    $('hilo').innerHTML='';
    msgs.forEach(m=>{const b=burbuja(m.rol==='user'?'user':'ia',m.contenido);
      if(m.rol!=='user'&&(m.contenido||'').trim())accionesResp(b,m.contenido,m.fuentes,{id:m.id,incompleta:!!m.incompleta,motivo:'',cid:id})});
    if(!msgs.length)$('sugs').classList.remove('hidden');
  }catch(e){
    if(turno!==CARGA_CONV)return;
    toast('No se pudo abrir esa consulta.');CONV=null;$('hilo').innerHTML='';$('sugs').classList.remove('hidden');cargarConvs();
  }
}
function tomarArchivos(ev){
  [...ev.target.files].forEach(f=>{
    if(f.size>7*1024*1024){toast('“'+f.name+'” supera 7 MB');return}
    const r=new FileReader();
    r.onload=()=>{ADJ.push({nombre:f.name,tipo:f.type.startsWith('image/')?'image':'document',
      media_type:f.type||'application/pdf',datos:r.result.split(',')[1]});pintarAdj();};
    r.readAsDataURL(f);
  });ev.target.value='';
}
function icoAdj(tipo){return tipo==='image'
  ?'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:3px"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5L5 21"/></svg>'
  :'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:3px"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>'}
function pintarAdj(){const c=$('adjfila');c.innerHTML='';
  ADJ.forEach((a,i)=>{const e=document.createElement('div');e.className='ch';
    e.innerHTML=icoAdj(a.tipo)+esc(a.nombre)+' <button type="button" class="adj-x" aria-label="Quitar adjunto"><svg class="i xs" aria-hidden="true"><use href="#i-x"/></svg></button>';
    e.querySelector('.adj-x').setAttribute('aria-label','Quitar '+a.nombre);
    e.querySelector('.adj-x').onclick=()=>{ADJ.splice(i,1);pintarAdj()};c.appendChild(e)});}
// vivo=true: mensaje que nace ahora (lleva .nueva y su entrada propia); los del historial se pintan sin coreografía.
function burbuja(rol,texto,adj,vivo){
  const b=document.createElement('div');b.className='b '+(rol==='user'?'user':'ia')+(vivo?' nueva':'');
  b.innerHTML=`<div class="av" aria-hidden="true">${rol==='user'?'Tú':'P'}</div><div class="bd">${rol==='user'?'':'<p class="quien"><b>PULLEX IA</b><span aria-hidden="true"> / Justicia × Inteligencia</span></p>'}<div class="md"></div></div>`;
  b.querySelector('.md').innerHTML=rol==='user'?esc(texto).replace(/\n/g,'<br>'):md(texto);
  if(adj&&adj.length){const d=document.createElement('div');d.className='adj';
    adj.forEach(a=>{const s=document.createElement('span');s.className='ch';
      s.innerHTML=icoAdj(a.tipo)+esc(a.nombre);d.appendChild(s)});
    b.querySelector('.bd').appendChild(d);}
  $('hilo').appendChild(b);scroll();return b;
}
function scroll(){const h=$('hist');h.scrollTop=h.scrollHeight}
// ¿La persona está leyendo el final? Si subió a releer, el texto que va llegando no la arrastra hacia abajo.
function alFinal(){const h=$('hist');return h.scrollHeight-h.scrollTop-h.clientHeight<96}

// Solo para pintar mientras llega el texto: una negrita a medio escribir («**Cuándo proc») se vería como asteriscos
// crudos y después saltaría a negrita. Se cierra de forma provisional; el texto guardado y el pintado final no cambian.
function mdParcial(t){
  t=t.replace(/(^|\s)\*$/,'$1');                                    // llegó solo el primer asterisco de una apertura
  const i=t.lastIndexOf('\n\n'),cola=i<0?t:t.slice(i);
  if(((cola.match(/\*\*/g)||[]).length%2)===0)return t;
  return /\*\*\s*$/.test(t)?t.replace(/\*\*\s*$/,''):t.replace(/\s+$/,'')+'**';
}
// Lee el stream SSE del chat y lo pinta en la burbuja ``bIA``. Lo usan «enviar» (respuesta nueva) y «continuarResp»
// (completar una respuesta que quedó incompleta; ``base`` es el texto que ya estaba escrito).
// Devuelve {buffer,fuentes,id,completo,incompleta,motivo,fin}. ``fin`` es false si el stream se cortó sin que el servidor
// avisara que terminó: en ese caso NUNCA se da por completa la respuesta.
async function transmitir(cuerpo,bIA,base){
  const cont=bIA.querySelector('.md');cont.classList.add('cursor');
  const res={buffer:base||'',fuentes:[],id:null,completo:false,incompleta:false,motivo:'',fin:false,estado:200,error:''};
  let raf=null,alto=0;
  // El markdown a medio llegar puede encoger un instante (una tabla o una lista que aún no cierra): el bloque nunca
  // baja de la altura que ya alcanzó, así lo que hay debajo no brinca. Y solo se sigue el final si ya se estaba ahí.
  const pinta=html=>{const sigue=alFinal();cont.innerHTML=html;cont.classList.add('cursor');
    alto=Math.max(alto,cont.offsetHeight);cont.style.minHeight=alto+'px';if(sigue)scroll()};
  const render=()=>{pinta(md(mdParcial(res.buffer)));raf=null};
  // Estado a la vista: sale de lo que de verdad está pasando (petición enviada, evento «busqueda», texto llegando).
  const quien=bIA.querySelector('.quien');let rotulo=null;
  const estado=(clave,txt)=>{trabajo(clave);if(!quien)return;
    if(!rotulo){rotulo=el('span','estado-ia');rotulo.setAttribute('role','status');quien.appendChild(rotulo)}
    if(rotulo.textContent!==txt)rotulo.textContent=txt};
  estado('espera','Esperando la respuesta…');
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{...auth(),'content-type':'application/json'},body:JSON.stringify(cuerpo)});
    if(!r.ok){const d=await r.json().catch(()=>({}));res.estado=r.status;res.error=(typeof d.detail==='string'&&d.detail)||'No se pudo procesar.';
      cont.classList.remove('cursor');if(rotulo)rotulo.remove();trabajo(null);return res}
    const rd=r.body.getReader(),dec=new TextDecoder();let resto='';
    while(true){const {value,done}=await rd.read();if(done)break;
      resto+=dec.decode(value,{stream:true});const lineas=resto.split('\n\n');resto=lineas.pop();
      for(const l of lineas){if(!l.startsWith('data: '))continue; // los comentarios «: latido» se ignoran
        let ev;try{ev=JSON.parse(l.slice(6))}catch(e){continue}
        if(ev.tipo==='texto'){res.buffer+=ev.texto;estado('escribe','Escribiendo…');if(!raf)raf=requestAnimationFrame(render)}
        else if(ev.tipo==='busqueda'){estado('fuentes','Buscando en fuentes…')}   // el aviso va en el rótulo de estado, no dentro del texto
        else if(ev.tipo==='continuando'){bIA.classList.add('continuando');estado('escribe','Completando la respuesta…')}
        else if(ev.tipo==='reparando'){bIA.classList.add('reparando');estado('escribe','Revisando que no falte nada…')}
        else if(ev.tipo==='restantes'){PERFIL.restantes=ev.restantes;$('c-rest').textContent=ev.restantes}
        else if(ev.tipo==='fuentes'){res.fuentes=Array.isArray(ev.fuentes)?ev.fuentes:[]}
        else if(ev.tipo==='pulido'&&typeof ev.texto==='string'){res.buffer=ev.texto;if(!raf)raf=requestAnimationFrame(render)}
        else if(ev.tipo==='incompleta'){res.incompleta=true;res.motivo=ev.motivo||'';if(ev.mensaje_id)res.id=ev.mensaje_id}
        else if(ev.tipo==='fin'){res.fin=true;res.completo=!!ev.completo;if(ev.mensaje_id)res.id=ev.mensaje_id;if(!ev.completo)res.incompleta=true}
      }
    }
  }catch(e){res.error='conexion'}
  if(raf)cancelAnimationFrame(raf);
  bIA.classList.remove('continuando','reparando');
  if(rotulo)rotulo.remove();trabajo(null);
  const sigue=alFinal();
  cont.classList.remove('cursor');cont.innerHTML=md(res.buffer);cont.style.minHeight='';
  if(sigue)scroll();
  return res;
}
// Si el stream se cortó sin «fin», el servidor guarda lo generado como incompleto: se busca ese mensaje para poder continuarlo.
async function recuperarIncompleta(cid){
  try{await new Promise(r=>setTimeout(r,1200));
    const msgs=await api('/api/conversaciones/'+cid+'/mensajes');const u=msgs[msgs.length-1];
    if(u&&u.rol!=='user'&&u.incompleta)return {id:u.id,texto:u.contenido||''};
  }catch(e){}
  return null;
}
// Remata una burbuja de respuesta: acciones, aviso «Continuar» si quedó cortada y valoración.
function cerrarResp(bIA,res,cid){
  const tieneTexto=(res.buffer||'').trim().length>0;
  if(!res.fin&&tieneTexto){res.incompleta=true;if(!res.motivo)res.motivo='interrumpida'}
  const sigue=alFinal();
  if(tieneTexto)accionesResp(bIA,res.buffer,res.fuentes,{id:res.id,incompleta:res.incompleta,motivo:res.motivo,cid});
  if(sigue)scroll();
}
// Envío en curso: el botón lo muestra (aro en vez de flecha) y lo dice a los lectores de pantalla.
function ocupado(si){enviando=si;const b=$('env');b.disabled=si;b.classList.toggle('ocupado',si);
  b.setAttribute('aria-label',si?'Enviando…':'Enviar');b.title=si?'Esperando la respuesta':'Enviar';
  if(si){b.setAttribute('aria-busy','true');trabajo('espera')}else{b.removeAttribute('aria-busy');trabajo(null)}}
// opc.titulo (opcional): título para el historial, p. ej. el que pone el Document Studio.
// El estado «ocupado» se suelta SIEMPRE, también si algo falla al pintar: de lo contrario el botón de enviar quedaría
// girando y el chat no admitiría otro mensaje hasta recargar la página.
async function enviar(opc){
  const texto=$('txt').value.trim();
  if((!texto&&!ADJ.length)||enviando)return;
  if(PERFIL.restantes<=0){toast('Se agotaron tus consultas. Actualiza tu plan.');ver('config');return}
  ocupado(true);
  let suelto=false;const soltar=()=>{if(!suelto){suelto=true;ocupado(false)}};   // este envío suelta una sola vez, y solo lo suyo
  let cid=null;
  try{
    if(!CONV)await nuevaConv();
    cid=CONV;
    $('sugs').classList.add('hidden');
    const adjEnvio=ADJ.slice();
    burbuja('user',texto,adjEnvio,true);$('txt').value='';autoAlto($('txt'));ADJ=[];pintarAdj();
    const bIA=burbuja('ia','',null,true);
    const res=await transmitir({conversacion:cid,mensaje:texto,web:WEB,modo:$('modo').value,estilo:$('estilo').value,adjuntos:adjEnvio},bIA,'');
    if(res.estado!==200){
      bIA.querySelector('.md').innerHTML=md('**Aviso:** '+res.error);
      soltar();if(res.estado===402||res.estado===403)ver('config');return}
    if(res.error==='conexion'&&!res.fin){
      const rec=await recuperarIncompleta(cid);
      if(rec&&rec.texto.length>=res.buffer.length){res.buffer=rec.texto;res.id=rec.id}
      if(!res.buffer.trim()){
        // No llegó nada ni quedó nada guardado: es solo un aviso. No es una respuesta: no lleva «Copiar» ni
        // «Continuar» (no hay de dónde continuar) y no se suma como consulta usada.
        bIA.querySelector('.md').innerHTML=md('**Aviso:** se interrumpió la conexión. Intenta de nuevo.');
        soltar();cargarConvs();return}
      bIA.querySelector('.md').innerHTML=md(res.buffer);   // lo recuperado tiene que verse, no solo guardarse
    }
    cerrarResp(bIA,res,cid);
  }finally{soltar()}
  PERFIL.usadas++;$('cf-uso').textContent=PERFIL.usadas+' / '+PERFIL.limite;
  // El servidor titula la conversación con el primer mensaje; se refresca la lista para verla.
  if(opc&&opc.titulo&&cid){try{await api('/api/conversaciones/'+cid+'/titulo',{body:{titulo:opc.titulo}})}catch(e){}}
  cargarConvs();
}
// «Continuar»: el servidor retoma la respuesta guardada y la completa; no gasta una consulta.
async function continuarResp(bIA,meta,textoActual){
  if(enviando)return;
  ocupado(true);
  let suelto=false;const soltar=()=>{if(!suelto){suelto=true;ocupado(false)}};   // este envío suelta una sola vez, y solo lo suyo
  try{
    quitarAcciones(bIA);
    const res=await transmitir({conversacion:meta.cid,continuar:true,web:WEB},bIA,textoActual);
    if(res.estado===400){ // ya no había nada por continuar (se completó en otra pestaña, por ejemplo): se recarga lo guardado
      soltar();toast('Esa respuesta ya estaba completa. Se recarga la conversación.');
      const c=meta.cid;CONV=null;await abrirConv(c);return}
    if(res.estado!==200){
      toast(res.error);soltar();
      accionesResp(bIA,textoActual,[],{id:meta.id,incompleta:true,motivo:meta.motivo,cid:meta.cid});return}
    if(res.error==='conexion'&&!res.fin){
      const rec=await recuperarIncompleta(meta.cid);
      if(rec&&rec.texto.length>=res.buffer.length){res.buffer=rec.texto;res.id=rec.id;bIA.querySelector('.md').innerHTML=md(res.buffer)}}
    if(!res.id)res.id=meta.id;
    cerrarResp(bIA,res,meta.cid);
  }finally{soltar()}
}
function quitarAcciones(b){b.querySelectorAll('.acc,.aviso-inc,.valorar,.nota-ia,.fuentes,.fichas,.fichas-t').forEach(n=>n.remove())}
function accionesResp(b,texto,fuentes,meta){
  const a=document.createElement('div');a.className='acc';
  a.innerHTML='<button type="button"><svg class="i xs" aria-hidden="true"><use href="#i-copiar"/></svg>Copiar</button><button type="button"><svg class="i xs" aria-hidden="true"><use href="#i-instalar"/></svg>Descargar</button><button type="button"><svg class="i xs" aria-hidden="true"><use href="#i-imprimir"/></svg>PDF</button><button type="button" class="b-estilo"><svg class="i xs" aria-hidden="true"><use href="#i-escrito"/></svg>Revisar estilo</button>';
  const [c,d,p,r]=a.querySelectorAll('button');
  r.onclick=()=>revisarEstilo(texto,b.querySelector('.bd'),r);
  c.onclick=()=>{navigator.clipboard.writeText(texto);toast('Copiado')};
  d.onclick=()=>descargar('pullex-respuesta.txt',texto);
  p.onclick=imprimirPDF;
  b.querySelector('.bd').appendChild(a);
  // "Confianza" y "Fuentes" las escribe el propio modelo: se rotulan como autoevaluación
  // para que nadie las lea como una verificación hecha por PULLEX (hallazgo AI-2).
  if(/\*\*\s*Confianza/i.test(texto)){const n=document.createElement('p');n.className='nota-ia';
    n.textContent='La confianza y las fuentes de arriba las indica la IA sobre su propia respuesta; PULLEX todavía no las verifica automáticamente. Confírmalas en la fuente oficial antes de citarlas en un escrito.';
    b.querySelector('.bd').appendChild(n);}
  pintarFuentes(b,fuentes,{fichas:true});
  if(meta&&meta.incompleta)avisoIncompleta(b,texto,meta);
  if(meta&&meta.id)panelValorar(b,meta);
}
// Respuesta cortada: se dice con claridad y se ofrece «Continuar». Nunca se presenta como terminada.
const MOTIVO_INC={limite:'La respuesta llegó al límite de longitud.',interrumpida:'La conexión se interrumpió mientras se escribía.',
  pausa:'La respuesta se pausó antes de terminar.',contexto:'La conversación es demasiado larga para seguir.',rechazo:'La IA no pudo completar esta respuesta.'};
function avisoIncompleta(b,texto,meta){
  const d=el('div','aviso-inc');d.setAttribute('role','status');
  d.appendChild(el('p',null,'Esta respuesta quedó incompleta. '+(MOTIVO_INC[meta.motivo]||'No llegó a terminar.')+' Puedes pedir que la complete desde donde se cortó.'));
  const bt=el('button','btn-continuar','Continuar');bt.type='button';
  bt.addEventListener('click',()=>continuarResp(b,meta,texto));
  d.appendChild(bt);
  b.querySelector('.bd').appendChild(d);
}
// Pulgar arriba / abajo con motivos de una lista cerrada (POST /api/feedback). No se guarda texto libre.
const MOTIVOS_FB=[['incompleta','Quedó incompleta'],['no_respondio','No respondió lo que pedí'],['error_juridico','Tiene un error jurídico'],['muy_larga','Es demasiado larga'],['otro','Otro motivo']];
function panelValorar(b,meta){
  const w=el('div','valorar');w.setAttribute('role','group');w.setAttribute('aria-label','¿Te sirvió esta respuesta?');
  const bu=el('button','vl-btn');bu.innerHTML=icoUse('pulgar','s');bu.type='button';bu.title='Me sirvió';bu.setAttribute('aria-label','La respuesta me sirvió');bu.setAttribute('aria-pressed','false');
  const bd=el('button','vl-btn');bd.innerHTML=icoUse('pulgar-abajo','s');bd.type='button';bd.title='Tuvo problemas';bd.setAttribute('aria-label','La respuesta tuvo problemas');bd.setAttribute('aria-pressed','false');
  const estado=el('span','vl-estado');estado.setAttribute('aria-live','polite');
  const caja=el('div','vl-motivos hidden');
  const sel=new Set();
  const chips=MOTIVOS_FB.map(([k,t])=>{const c=el('button','vl-chip',t);c.type='button';c.setAttribute('aria-pressed','false');
    c.addEventListener('click',()=>{if(sel.has(k)){sel.delete(k);c.setAttribute('aria-pressed','false')}else{sel.add(k);c.setAttribute('aria-pressed','true')}});
    caja.appendChild(c);return c});
  const enviarFb=el('button','vl-enviar','Enviar');enviarFb.type='button';caja.appendChild(enviarFb);
  async function mandar(valor){
    try{await api('/api/feedback',{body:{mensaje:meta.id,valor,motivos:valor==='abajo'?[...sel]:[]}});
      bu.setAttribute('aria-pressed',valor==='arriba'?'true':'false');bd.setAttribute('aria-pressed',valor==='abajo'?'true':'false');
      estado.textContent='Gracias por tu opinión.';caja.classList.add('hidden');
    }catch(e){estado.textContent=e.message||'No se pudo enviar tu opinión.'}
  }
  bu.addEventListener('click',()=>mandar('arriba'));
  bd.addEventListener('click',()=>{caja.classList.toggle('hidden');estado.textContent='';
    if(!caja.classList.contains('hidden'))chips[0].focus()});
  enviarFb.addEventListener('click',()=>mandar('abajo'));
  w.append(bu,bd,estado,caja);
  b.querySelector('.bd').appendChild(w);
}
// ---- Revisar estilo: rasgos típicos del texto generado por IA (POST /api/estilo/revisar, no gasta consultas).
// Lo usan el chat y la vista de documentos (documentos.js). Todo se pinta con textContent.
async function revisarEstilo(texto,destino,boton){
  if(!destino||!(texto||'').trim())return;
  if(boton)boton.disabled=true;
  try{
    const r=await fetch('/api/estilo/revisar',{method:'POST',headers:{...auth(),'content-type':'application/json'},body:JSON.stringify({texto})});
    const d=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'No se pudo revisar el estilo.');
    pintarEstilo(destino,d);
  }catch(e){toast(e.message||'No se pudo revisar el estilo.')}
  if(boton)boton.disabled=false;
}
// Pinta una revisión de estilo ya calculada (la de /api/estilo/revisar o la que acompaña una evaluación del Taller).
function pintarEstilo(destino,d,opc){
  const previo=destino.querySelector(':scope > .estilo-rev');if(previo)previo.remove();
  const box=el('section','estilo-rev');box.setAttribute('aria-label','Revisión de estilo');box.setAttribute('tabindex','-1');
  box.appendChild(el('h4',null,'Revisión de estilo'));box.appendChild(el('p',null,d.valoracion||''));
  const rasgos=Array.isArray(d.rasgos)?d.rasgos:[];
  if(rasgos.length){const ul=el('ul');
    rasgos.forEach(x=>{const li=el('li');li.appendChild(el('b',null,(x.nombre||x.id)+(x.veces>1?' ('+x.veces+')':'')));
      li.appendChild(document.createTextNode('. '+(x.explicacion||'')+' '+(x.sugerencia||'')));
      if(Array.isArray(x.ejemplos)&&x.ejemplos.length)li.appendChild(el('span','er-ej','Ejemplo: «'+x.ejemplos[0]+'»'));
      ul.appendChild(li)});
    box.appendChild(ul)}
  box.appendChild(el('p','er-nota',d.nota||'Es una ayuda de estilo, no una prueba de que un texto lo escribió una IA.'));
  destino.appendChild(box);
  if(!(opc&&opc.sinFoco)){box.focus({preventScroll:true});box.scrollIntoView({behavior:'smooth',block:'nearest'})}
  return box;
}
// ---- Fuentes consultadas: corpus propio [F#] y páginas oficiales citadas por la búsqueda web.
// Todo con textContent (nada de innerHTML con datos del servidor) y el estado escrito en el chip,
// no solo por color.
const CHIP_FUENTE={VIGENTE_VERIFICADA:['vigente','Corpus · vigente'],PENDIENTE_VERIFICAR:['verificar','Corpus · verificar vigencia'],
  DESACTUALIZADA:['verificar','Corpus · desactualizada'],DEROGADA:['derogada','Corpus · derogada']};
function chipFuente(f){
  if(f.origen==='web')return f.oficial?['web','Oficial · web']:['verificar','Web · no oficial'];
  return CHIP_FUENTE[f.estado_vigencia]||CHIP_FUENTE.PENDIENTE_VERIFICAR;
}
function urlSegura(u){return typeof u==='string'&&/^https?:\/\//i.test(u)?u:null}
function tituloFuente(f){
  const url=urlSegura(f.url);
  if(url){const a=el('a','ftit',f.titulo||url);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a}
  return el('span','ftit',f.titulo||'Documento del corpus');
}
// opc.fichas: además del bloque plegable, las fuentes CITADAS se muestran como fichas a la vista (con su estado de
// vigencia escrito). En una respuesta recién llegada se despliegan una a una (static/movimiento.css, .b.nueva).
// En pantallas angostas las fichas van una debajo de otra: se muestran menos y el resto queda en la lista.
function maxFichas(){try{return window.matchMedia('(max-width:560px)').matches?2:4}catch(e){return 4}}
function pintarFuentes(b,fuentes,opc){
  if(!Array.isArray(fuentes)||!fuentes.length)return;
  const lista=fuentes.slice().sort((x,y)=>(y.citado?1:0)-(x.citado?1:0));
  const d=el('details','fuentes');
  const citadas=opc&&opc.fichas?lista.filter(f=>f.citado):[];
  if(citadas.length){const MAX_FICHAS=maxFichas();
    const rot=citadas.length===1?'Fuente citada en esta respuesta':'Fuentes citadas en esta respuesta';
    const tt=el('p','fichas-t',rot);tt.setAttribute('aria-hidden','true');b.querySelector('.bd').appendChild(tt);
    const fs=el('ul','fichas');fs.setAttribute('aria-label',rot);
    citadas.slice(0,MAX_FICHAS).forEach((f,i)=>{
      const li=el('li','ficha');li.style.setProperty('--i',i);const [cls,txt]=chipFuente(f);
      li.appendChild(el('span','fchip '+cls,txt));li.appendChild(tituloFuente(f));
      const m=[];if(f.ref)m.push('['+f.ref+']');if(f.ubicacion)m.push(f.ubicacion);
      if(m.length)li.appendChild(el('span','fmeta',m.join(' · ')));
      fs.appendChild(li)});
    if(citadas.length>MAX_FICHAS){const li=el('li');li.style.setProperty('--i',MAX_FICHAS);
      li.appendChild(boton('y '+(citadas.length-MAX_FICHAS)+' más en la lista','fichas-mas',()=>{d.open=true;d.querySelector('summary').focus()}));
      fs.appendChild(li)}
    b.querySelector('.bd').appendChild(fs);
  }
  const s=el('summary',null,'Fuentes consultadas ('+lista.length+')');s.insertAdjacentHTML('afterbegin',icoUse('fuentes','s'));d.appendChild(s);
  const ul=el('ul','fuentes-lista');
  lista.forEach((f,i)=>{
    const li=el('li','fuente');li.style.setProperty('--i',Math.min(i,8));const [cls,txt]=chipFuente(f);
    li.appendChild(el('span','fchip '+cls,txt));
    const url=urlSegura(f.url);
    li.appendChild(tituloFuente(f));
    const meta=[];
    if(f.ref)meta.push('['+f.ref+']');
    if(f.origen==='corpus'&&f.tipo)meta.push(f.tipo);
    if(f.ubicacion)meta.push(f.ubicacion);
    if(f.fecha_archivo)meta.push('archivo del '+f.fecha_archivo);
    if(f.origen==='web'&&url){try{meta.push(new URL(url).hostname.replace(/^www\./,''))}catch(e){}}
    meta.push(f.citado?'citada en la respuesta':'consultada, no citada');
    li.appendChild(el('span','fmeta',meta.join(' · ')));
    ul.appendChild(li);
  });
  d.appendChild(ul);
  if(lista.some(f=>f.origen==='corpus'&&f.estado_vigencia!=='VIGENTE_VERIFICADA'))
    d.appendChild(el('p','fnota','«Verificar vigencia»: ese documento del corpus no ha sido confirmado en la fuente oficial en los últimos 12 meses. Confírmalo antes de citarlo.'));
  b.querySelector('.bd').appendChild(d);
}
function descargar(n,t){const bl=new Blob([t],{type:'text/plain;charset=utf-8'});
  const u=URL.createObjectURL(bl);const a=document.createElement('a');a.href=u;a.download=n;a.click();URL.revokeObjectURL(u)}
function imprimirPDF(){window.print()}
function exportarExcel(){
  const tablas=$('hilo').querySelectorAll('.b.ia table');
  if(!tablas.length){toast('No hay tablas para exportar. Pide una liquidación o un cuadro.');return}
  const t=tablas[tablas.length-1];let csv=[];
  t.querySelectorAll('tr').forEach(tr=>{csv.push([...tr.querySelectorAll('th,td')]
    .map(x=>'"'+x.textContent.replace(/"/g,'""')+'"').join(','))});
  const bl=new Blob(['﻿'+csv.join('\n')],{type:'text/csv;charset=utf-8'});
  const u=URL.createObjectURL(bl);const a=document.createElement('a');a.href=u;a.download='pullex-liquidacion.csv';a.click();
  URL.revokeObjectURL(u);toast('Descargado (ábrelo en Excel)');
}

async function guardarPrefs(){
  // El tema ya no viaja aquí: lo maneja la apariencia (apCambiar), que distingue claro/oscuro/automático.
  const areas=[...document.querySelectorAll('#areas .area.on')].map(e=>e.textContent);
  const body={areas,modo:$('cf-modo').value,web:$('cf-web').classList.contains('on')};
  if($('cf-escritura'))body.escritura=$('cf-escritura').value;
  try{const d=await(await fetch('/api/preferencias',{method:'POST',
    headers:{...auth(),'content-type':'application/json'},body:JSON.stringify(body)})).json();
    PERFIL.preferencias={...PERFIL.preferencias,...d.preferencias};$('modo').value=d.preferencias.modo;
    WEB=d.preferencias.web;pintarWeb();}catch(e){}
}
async function guardarMemoria(){
  try{await fetch('/api/preferencias',{method:'POST',headers:{...auth(),'content-type':'application/json'},
    body:JSON.stringify({memoria:$('cf-memoria').value})});
    PERFIL.preferencias.memoria=$('cf-memoria').value;toast('Memoria guardada');}catch(e){}
}
function togglePref(el){el.classList.toggle('on');guardarPrefs()}
function toggleTema(el){el.classList.toggle('on');apCambiar({modo:el.classList.contains('on')?'claro':'oscuro'})}
// Compatibilidad: cambia claro/oscuro sin guardar (lo usan pruebas y código anterior).
function aplicarTema(t){AP.datos={...(AP.datos||PXA.actual()),modo:t==='claro'?'claro':'oscuro'};PXA.aplicar(AP.datos);apRefrescar()}
function sincronizarSwTema(){const s=$('cf-tema');if(s)s.classList.toggle('on',document.documentElement.getAttribute('data-esquema')!=='oscuro')}

const ICONOS_TOOL={
  tutela:'<path d="M12 3v18M7 21h10M12 3l-6 3M12 3l6 3M6 6l-3 6a3 3 0 0 0 6 0L6 6zM18 6l-3 6a3 3 0 0 0 6 0l-3-6z"/>',
  peticion:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h6M9 9h1"/>',
  liquidacion:'<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9 9.5c0-1 1-1.5 3-1.5s3 .8 3 2-1.2 1.7-3 2-3 .8-3 2 1.2 2 3 2 3-.5 3-1.5"/>',
  sentencia:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M9 13h6M9 17h4"/>',
  termino:'<rect x="3" y="4" width="18" height="18" rx="2.5"/><path d="M16 2v4M8 2v4M3 10h18M12 14v4l3 2"/>',
  demanda:'<path d="M12 2l8 4v5c0 5-3.4 8.7-8 10-4.6-1.3-8-5-8-10V6z"/>',
  empresa:'<path d="M3 21h18M6 21V8l6-4 6 4v13M10 21v-5h4v5M9 12h.01M15 12h.01M9 8h.01M15 8h.01"/>',
  marca:'<circle cx="12" cy="12" r="9"/><path d="M9 8v8M9 12h3.5a2 2 0 1 0 0-4H9M9 12h4a2 2 0 1 1 0 4H9"/>',
  reporte:'<path d="M3 17l6-6 4 4 8-8M21 7v6h-6"/>',
  alimentos:'<circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M2 21c0-3.9 2.7-6 6-6s6 2.1 6 6M14 21c0-2.8 1.8-5 4-5s4 2.2 4 5"/>',
};
function icoTool(nombre,size=18){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${ICONOS_TOOL[nombre]}</svg>`}
const HERRAMIENTAS=[
  {i:'tutela',t:'Redactar tutela',p:'Ayúdame a redactar una acción de tutela. Pregúntame primero, uno por uno, los datos que necesitas (mis datos, la entidad accionada, el derecho fundamental vulnerado y los hechos) y luego arma el escrito completo.'},
  {i:'peticion',t:'Derecho de petición',p:'Ayúdame a redactar un derecho de petición. Pregúntame a qué entidad va dirigido, qué solicito y los hechos, y luego redacta el escrito formal.'},
  {i:'liquidacion',t:'Liquidación laboral',p:'Calcula una liquidación laboral (cesantías, intereses, prima, vacaciones e indemnización si aplica). Pregúntame el salario, las fechas de inicio y fin, el tipo de contrato y si hubo auxilio de transporte. Muestra el resultado en una TABLA.'},
  {i:'sentencia',t:'Entender una sentencia',p:'Te voy a pasar una sentencia (o la adjunto). Explícamela en palabras simples: qué decidió, por qué, y la regla que fija. No uses tecnicismos sin explicarlos.'},
  {i:'termino',t:'Calcular un término',p:'Ayúdame a calcular un término procesal. Pregúntame de qué actuación se trata, la fecha de inicio y si son días hábiles o calendario, y adviérteme sobre suspensiones o vacancias.'},
  {i:'demanda',t:'Contestar una demanda',p:'Me demandaron y necesito contestar. Pregúntame los datos del proceso y los hechos, y ayúdame con el pronunciamiento sobre los hechos y las excepciones de mérito.'},
  {i:'empresa',t:'Crear una empresa (SAS)',p:'Quiero constituir una SAS en Colombia. Explícame el paso a paso y ayúdame con lo que necesito (objeto social, capital, trámite en Cámara de Comercio).'},
  {i:'marca',t:'Registrar una marca',p:'Quiero registrar una marca ante la SIC. Explícame el proceso, la clasificación de Niza y la búsqueda de antecedentes, y guíame paso a paso.'},
  {i:'reporte',t:'Reporte en centrales de riesgo',p:'Tengo un problema con un reporte en Datacrédito/centrales de riesgo. Explícame mis derechos (habeas data) y ayúdame a redactar el reclamo.'},
  {i:'alimentos',t:'Cuota de alimentos',p:'Necesito orientación sobre una cuota de alimentos para un menor. Pregúntame los datos y explícame las opciones y a dónde acudir.'},
];
function abrirTools(){
  const g=$('tools-grid');g.innerHTML='';
  HERRAMIENTAS.forEach(h=>{const b=document.createElement('button');b.type='button';
    b.className='tool';
    b.innerHTML=`<span class="ti">${icoTool(h.i)}</span>`;b.appendChild(document.createTextNode(h.t));
    b.onclick=()=>{if(h.i==='tutela'||h.i==='peticion'){cerrarTools();abrirEscrito(h.i)}else usarTool(h.p)};g.appendChild(b);});
  $('m-tools').classList.remove('hidden');
}
function cerrarTools(){$('m-tools').classList.add('hidden')}
function usarTool(p,estilo){$('estilo').value=estilo||'directo';cerrarTools();ver('chat');
  // Cada herramienta es un asunto nuevo: se abre en una consulta nueva (la anterior queda en el historial).
  if($('hilo').children.length&&!enviando)nuevaConsulta();
  $('txt').value=p;autoAlto($('txt'));$('txt').focus();
  toast('Ajusta los datos si quieres y presiona enviar')}

// -------------------------------------------------------------------- Document Studio --
// Formulario guiado que arma una solicitud estructurada y la envía al chat como una consulta
// nueva. Los datos del usuario solo se tratan como texto (textContent / value), nunca como HTML.
const ESCRITO_ENCABEZADO='SOLICITUD DE REDACCIÓN';
const ESCRITOS={
  tutela:{nombre:'Acción de tutela',campos:[
    {id:'nombre',l:'Nombre de quien presenta la tutela',req:1,ph:'Nombre completo',auto:'name'},
    {id:'ident',l:'Identificación',ph:'Tipo y número de documento'},
    {id:'ciudad',l:'Ciudad',req:1,ph:'Ej.: Bogotá',auto:'address-level2'},
    {id:'contra',l:'¿Contra quién? (entidad o particular)',req:1,ph:'Ej.: mi EPS, un fondo de pensiones, la alcaldía'},
    {id:'derechos',l:'Derecho(s) que consideras vulnerado(s)',req:1,ancho:1,ph:'Ej.: salud, vida digna, petición, debido proceso'},
    {id:'hechos',l:'Hechos: qué pasó y cuándo',req:1,ancho:1,filas:5,ph:'Cuenta en orden lo ocurrido, con fechas aunque sean aproximadas.'},
    {id:'previas',l:'Actuaciones previas',ancho:1,filas:3,ph:'¿Ya le pediste algo a la entidad? ¿Cuándo y qué te respondió?'},
    {id:'pide',l:'¿Qué le pides al juez?',req:1,ancho:1,filas:3,ph:'Ej.: que ordene a la EPS entregar el medicamento formulado.'},
    {id:'urgente',l:'¿Hay un perjuicio urgente?',opciones:['No lo sé','Sí','No']},
    {id:'urgencia',l:'Si es urgente, ¿por qué?',ph:'Ej.: riesgo para la salud o la vida'},
  ]},
  peticion:{nombre:'Derecho de petición',campos:[
    {id:'nombre',l:'Nombre de quien hace la petición',req:1,ph:'Nombre completo',auto:'name'},
    {id:'ident',l:'Identificación',ph:'Tipo y número de documento'},
    {id:'entidad',l:'Entidad o persona a la que va dirigida',req:1,ancho:1,ph:'Ej.: la alcaldía de tu municipio, tu EPS, una empresa'},
    {id:'solicita',l:'¿Qué solicitas?',req:1,ancho:1,filas:3,ph:'Ej.: copia de mi historia laboral; que corrijan un dato.'},
    {id:'hechos',l:'Hechos y fundamento',req:1,ancho:1,filas:4,ph:'¿Por qué lo pides? Cuenta lo ocurrido en orden.'},
    {id:'medio',l:'¿Dónde quieres recibir la respuesta?',req:1,ancho:1,ph:'Correo electrónico o dirección física',auto:'email'},
  ]},
};
let ES_TIPO='tutela';
function esCampo(tipo,id){return $('es-'+tipo+'-'+id)}
function construirEscrito(){
  const cont=$('es-campos');if(cont.children.length)return;
  Object.entries(ESCRITOS).forEach(([tipo,def])=>{
    const g=document.createElement('div');g.className='es-grid';g.id='es-grupo-'+tipo;
    def.campos.forEach(c=>{
      const w=document.createElement('div');w.className='es-campo'+(c.ancho?' ancho':'');
      const lb=document.createElement('label');const idc='es-'+tipo+'-'+c.id;lb.htmlFor=idc;
      lb.appendChild(document.createTextNode(c.l));
      const m=document.createElement('span');
      if(c.req){m.className='req';m.textContent='*';m.setAttribute('aria-hidden','true')}
      else if(!c.opciones){m.className='opc-t';m.textContent=' (opcional)'}
      lb.appendChild(m);w.appendChild(lb);
      let el;
      if(c.opciones){el=document.createElement('select');
        c.opciones.forEach(o=>{const op=document.createElement('option');op.textContent=o;el.appendChild(op)})}
      else if(c.filas){el=document.createElement('textarea');el.rows=c.filas}
      else{el=document.createElement('input');el.type='text'}
      el.id=idc;el.className='inp';if(c.ph)el.placeholder=c.ph;if(c.auto)el.autocomplete=c.auto;
      if(c.req){el.required=true;el.setAttribute('aria-required','true')}
      el.maxLength=c.filas?4000:300;
      el.addEventListener('input',()=>esLimpiarError(el));
      w.appendChild(el);g.appendChild(w);
    });
    cont.appendChild(g);
  });
}
function esLimpiarError(el){el.classList.remove('error');el.removeAttribute('aria-invalid');
  const e=el.parentNode.querySelector('.err');if(e)e.remove()}
function escritoTipo(t){
  ES_TIPO=ESCRITOS[t]?t:'tutela';
  Object.keys(ESCRITOS).forEach(k=>{$('es-tipo-'+k).classList.toggle('on',k===ES_TIPO);
    $('es-tipo-'+k).setAttribute('aria-pressed',String(k===ES_TIPO));
    $('es-grupo-'+k).classList.toggle('hidden',k!==ES_TIPO)});
  $('es-msg').textContent='';
}
function abrirEscrito(tipo){
  construirEscrito();escritoTipo(typeof tipo==='string'?tipo:ES_TIPO);
  $('m-escrito').classList.remove('hidden');$('m-escrito').querySelector('.card').scrollTop=0;
  if(esEscritorio())esCampo(ES_TIPO,'nombre').focus();
}
function cerrarEscrito(){$('m-escrito').classList.add('hidden')}
function valoresEscrito(tipo){const v={};ESCRITOS[tipo].campos.forEach(c=>{v[c.id]=esCampo(tipo,c.id).value.trim()});return v}
function validarEscrito(tipo){
  let primero=null;
  ESCRITOS[tipo].campos.forEach(c=>{const el=esCampo(tipo,c.id);esLimpiarError(el);
    if(c.req&&!el.value.trim()){el.classList.add('error');el.setAttribute('aria-invalid','true');
      const e=document.createElement('div');e.className='err';e.textContent='Este dato es obligatorio.';el.after(e);
      if(!primero)primero=el}});
  return primero;
}
function textoEscrito(tipo,v){
  const falta=t=>v[t]||'[no indicado]';
  const cierre=['',
    '- Marca entre corchetes [ ] todo dato que falte o que yo deba completar (por ejemplo, [número de cédula] o [dirección para notificaciones]).',
    '- No inventes números de sentencias, radicados, fechas ni datos de las partes. Si mencionas jurisprudencia de la que no tengas certeza, indícalo para que la verifique.',
    '- Al final, advierte que se debe verificar la vigencia de las normas citadas en la fuente oficial (SUIN-Juriscol o Secretaría del Senado) antes de presentar el escrito.'];
  if(tipo==='tutela')return [
    ESCRITO_ENCABEZADO+' — ACCIÓN DE TUTELA','',
    'Redacta el borrador completo de una acción de tutela con estos datos:','',
    'ACCIONANTE','- Nombre: '+falta('nombre'),'- Identificación: '+falta('ident'),'- Ciudad: '+falta('ciudad'),'',
    'ACCIONADO (entidad o particular)',falta('contra'),'',
    'DERECHOS FUNDAMENTALES QUE CONSIDERO VULNERADOS',falta('derechos'),'',
    'HECHOS',falta('hechos'),'',
    'ACTUACIONES PREVIAS',v.previas||'No indicadas.','',
    'LO QUE PIDO AL JUEZ',falta('pide'),'',
    'PERJUICIO URGENTE',(v.urgente||'No lo sé')+(v.urgencia?' — '+v.urgencia:''),'',
    'INSTRUCCIONES PARA EL BORRADOR',
    '- Usa la estructura procesal colombiana: juez competente (juez de la República, reparto) en la ciudad indicada; identificación de las partes; hechos numerados; derechos fundamentales vulnerados; fundamentos de derecho (artículo 86 de la Constitución Política y Decreto 2591 de 1991, y otras normas solo si son pertinentes); procedencia (legitimación en la causa por activa y por pasiva, subsidiariedad e inmediatez); pretensiones; pruebas y anexos; juramento de no haber presentado otra acción de tutela por los mismos hechos y derechos; notificaciones; firma.',
    '- Si hay un perjuicio urgente, incluye la solicitud de medida provisional prevista en el Decreto 2591 de 1991 y sustenta por qué no da espera.',
    ...cierre].join('\n');
  return [
    ESCRITO_ENCABEZADO+' — DERECHO DE PETICIÓN','',
    'Redacta el borrador completo de un derecho de petición con estos datos:','',
    'PETICIONARIO','- Nombre: '+falta('nombre'),'- Identificación: '+falta('ident'),'',
    'DESTINATARIO',falta('entidad'),'',
    'LO QUE SOLICITO',falta('solicita'),'',
    'HECHOS Y FUNDAMENTO',falta('hechos'),'',
    'MEDIO PARA RECIBIR LA RESPUESTA',falta('medio'),'',
    'INSTRUCCIONES PARA EL BORRADOR',
    '- Usa la estructura formal colombiana: ciudad y fecha; destinatario; referencia; identificación del peticionario; hechos numerados; peticiones concretas y numeradas; fundamentos de derecho (artículo 23 de la Constitución Política y Ley 1755 de 2015); anexos; dirección para notificaciones; firma.',
    '- Indica el término legal que tiene la entidad para responder según el tipo de petición, advirtiendo que ese término debe verificarse.',
    ...cierre].join('\n');
}
function enviarEscrito(){
  if(enviando){toast('Espera a que termine la respuesta actual.');return}
  const tipo=ES_TIPO;const malo=validarEscrito(tipo);
  if(malo){$('es-msg').textContent='Completa los campos marcados para poder redactar el borrador.';malo.focus();return}
  if(PERFIL.restantes<=0){cerrarEscrito();toast('Se agotaron tus consultas. Actualiza tu plan.');ver('config');return}
  const v=valoresEscrito(tipo);
  const titulo=tipo==='tutela'?'Tutela contra '+v.contra:'Petición a '+v.entidad;
  cerrarEscrito();$('estilo').value='directo';ver('chat');
  if(!nuevaConsulta())return;
  $('txt').value=textoEscrito(tipo,v);
  ESCRITOS[tipo].campos.forEach(c=>{const el=esCampo(tipo,c.id);el.value=c.opciones?c.opciones[0]:''});
  enviar({titulo});
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('m-escrito').classList.contains('hidden'))cerrarEscrito()});
function abrirClave(){$('m-clave').classList.remove('hidden');$('k-msg').textContent=''}
function cerrarClave(){$('m-clave').classList.add('hidden');$('k-act').value='';$('k-new').value=''}
async function guardarClave(){
  const r=await fetch('/api/cambiar-clave',{method:'POST',headers:{...auth(),'content-type':'application/json'},
    body:JSON.stringify({actual:$('k-act').value,nueva:$('k-new').value})});
  const d=await r.json();if(!r.ok){$('k-msg').textContent=d.detail||'No se pudo';return}
  if(d.token)TOKEN=d.token; // las demás sesiones quedaron cerradas; esta sigue con token nuevo
  cerrarClave();toast('Contraseña actualizada. Se cerró la sesión en tus otros dispositivos.');
}
async function cerrarSesiones(){
  if(!confirm('Se cerrará tu sesión en todos los dispositivos, incluido este. ¿Continuar?'))return;
  try{await fetch('/api/cerrar-sesiones',{method:'POST',headers:auth()})}catch(e){}
  salir();
}
async function reenviarVerificacion(){
  const b=$('btn-reenviar-verif');const t0=b.textContent;b.disabled=true;b.textContent='Enviando…';
  try{
    const r=await fetch('/api/reenviar-verificacion',{method:'POST',headers:auth()});
    const d=await r.json().catch(()=>({}));
    toast(r.ok?(d.mensaje||'Te enviamos un correo de verificación'):(d.detail||'No se pudo enviar. Intenta más tarde.'));
  }catch(e){toast('Error de conexión')}
  b.disabled=false;b.textContent=t0;
}
function salir(){TOKEN=null;PERFIL=null;CONV=null;Object.values(AP.urls).forEach(u=>{if(u&&u.startsWith('blob:'))URL.revokeObjectURL(u)});location.reload()}
if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{})}

// -------------------------------------------------------- instalar como app --
let DEFERRED_INSTALL=null;
const esStandalone=()=>window.matchMedia('(display-mode: standalone)').matches||window.navigator.standalone===true;
const esIOS=()=>/iphone|ipad|ipod/i.test(navigator.userAgent)&&!window.MSStream;
function mostrarBotonInstalar(){
  if(esStandalone())return; // ya está instalada, no mostrar nada
  $('btn-instalar-ic').classList.remove('hidden');
  $('btn-instalar-hero').classList.remove('hidden');
}
window.addEventListener('beforeinstallprompt',(e)=>{
  e.preventDefault();DEFERRED_INSTALL=e;mostrarBotonInstalar();
});
window.addEventListener('appinstalled',()=>{
  DEFERRED_INSTALL=null;$('btn-instalar-ic').classList.add('hidden');$('btn-instalar-hero').classList.add('hidden');
  toast('PULLEX IA instalada');
});
async function instalarApp(){
  if(DEFERRED_INSTALL){
    DEFERRED_INSTALL.prompt();
    const r=await DEFERRED_INSTALL.userChoice;
    if(r.outcome==='accepted')toast('Instalando…');
    DEFERRED_INSTALL=null;
    return;
  }
  if(esIOS()){
    toast('En Safari: toca Compartir (□↑) y luego "Agregar a pantalla de inicio"');
    return;
  }
  toast('Busca "Instalar app" en el menú de tu navegador');
}
// Android/Chrome dispara beforeinstallprompt de forma asíncrona; en iOS nunca llega,
// así que mostramos el botón igual (con instrucciones manuales) salvo que ya esté instalada.
if(esIOS()&&!esStandalone())mostrarBotonInstalar();
function abrirSelectorArchivo(){document.getElementById('file').click()}

// =========================================================================================
// PULLEX Academia — dos caminos en el inicio y Laboratorio de casos
// =========================================================================================
const APRENDER=[
  {ic:'<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
   t:'Resolver un caso',d:'Un caso tipo examen: respondes tú y PULLEX te evalúa con rúbrica.',ir:'modular'},
  {ic:'<path d="M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2z"/><path d="M22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z"/>',
   t:'Enséñame un tema',d:'Explicación por capas, con ejemplo, norma y el error más común.',
   p:'Quiero aprender este tema: ',estilo:'ensename'},
  {ic:'<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
   t:'Resuélvelo conmigo',d:'Tutor socrático: te guía con preguntas hasta que llegas a la respuesta.',
   p:'Quiero resolver este caso paso a paso contigo: ',estilo:'conmigo'},
  {ic:'<path d="M12 3l9 4.5-9 4.5-9-4.5z"/><path d="M6 10v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5"/>',
   t:'Examíname',d:'Simulacro oral: una pregunta a la vez, exige fundamento y cambia los hechos.',
   p:'Examíname sobre: ',estilo:'examiname'},
];
let CAMINO='aprender';
function elegirCamino(c){
  CAMINO=c==='trabajar'?'trabajar':'aprender';
  $('cam-aprender').classList.toggle('on',CAMINO==='aprender');
  $('cam-trabajar').classList.toggle('on',CAMINO==='trabajar');
  pintarCapacidades();cargarProgresoInicio();
  if(PERFIL&&PERFIL.preferencias.camino!==CAMINO){PERFIL.preferencias.camino=CAMINO;
    fetch('/api/preferencias',{method:'POST',headers:{...auth(),'content-type':'application/json'},
      body:JSON.stringify({camino:CAMINO})}).catch(()=>{});}
}
function pintarCapacidades(){
  const g=$('capgrid');g.innerHTML='';
  (CAMINO==='trabajar'?CAPACIDADES:APRENDER).forEach(c=>{
    const b=document.createElement('button');b.className='captarj';
    b.innerHTML=`<div class="ci"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${c.ic}</svg></div>`;
    const t=document.createElement('b');t.textContent=c.t;const d=document.createElement('span');d.textContent=c.d;
    b.appendChild(t);b.appendChild(d);
    const bloq=c.ir&&typeof vistaBloqueada==='function'&&vistaBloqueada(c.ir);
    if(bloq){const tg=el('span','plan-tag');tg.appendChild(plIcono('candado'));
      tg.appendChild(document.createTextNode('Plan '+plNombre(plRequerido(VISTA_FUNCION[c.ir]))));b.appendChild(tg);
      b.setAttribute('aria-label',c.t+'. Incluido en el plan '+plNombre(plRequerido(VISTA_FUNCION[c.ir])))}
    const ir=el('span','ir',bloq?'Ver el plan':'Empezar');ir.insertAdjacentHTML('beforeend','<svg class="i xs" aria-hidden="true"><use href="#i-flecha"/></svg>');b.appendChild(ir);
    b.addEventListener('click',()=>{if(c.ir)ver(c.ir);else if(c.abrir==='escrito')abrirEscrito();else usarTool(c.p,c.estilo||'directo')});
    g.appendChild(b);
  });
}
async function cargarProgresoInicio(){
  const el=$('progreso-inicio');
  cargarTablero();
  if(CAMINO!=='aprender'||(typeof tieneFuncion==='function'&&!tieneFuncion('academia'))){el.classList.add('hidden');return}
  try{
    const p=await api('/api/modular/progreso');
    if(!p.resueltos){el.classList.add('hidden');return}
    el.textContent='';
    // suf: la cifra llega contando hasta su valor real (static/movimiento.js); el texto final es el del servidor.
    const cifras=[];
    const item=(txt,val,cls,suf)=>{const s=document.createElement('span');s.appendChild(document.createTextNode(txt+' '));
      const b=document.createElement('b');b.textContent=val+(suf||'');if(cls)b.className=cls;s.appendChild(b);el.appendChild(s);
      if(typeof val==='number')cifras.push([b,val,suf||''])};
    item('Modulares resueltos',p.resueltos);
    item('Promedio',p.promedio,null,'/100');
    if(p.a_reforzar&&p.a_reforzar.length)item('Refuerza',p.a_reforzar[0],'ref');
    el.classList.remove('hidden');
    if(window.MV&&MV.contar)cifras.forEach(([b,val,suf])=>MV.contar(b,val,{sufijo:suf}));
  }catch(e){el.classList.add('hidden')}
}

async function api(url,opts){
  const o=opts||{};const h={...auth()};if(o.body)h['content-type']='application/json';
  const r=await fetch(url,{method:o.body?'POST':'GET',headers:h,body:o.body?JSON.stringify(o.body):undefined});
  const d=await r.json().catch(()=>({}));
  if(r.status===403&&typeof planInsuficiente==='function'&&planInsuficiente(d))throw new Error(d.detail);
  if(!r.ok)throw new Error(d.detail||'No se pudo completar la solicitud.');
  if(typeof d.restantes==='number'&&PERFIL){PERFIL.restantes=d.restantes;$('c-rest').textContent=d.restantes;
    PERFIL.usadas=PERFIL.limite-d.restantes;$('cf-uso').textContent=PERFIL.usadas+' / '+PERFIL.limite}
  return d;
}

// ------------------------------------------------------------------------ Laboratorio de casos --
const ML={opciones:null,area:null,nivel:'basico',caso:null,pistas:0,evaluado:false,confirmarSol:false};
async function mlInit(){
  if(!ML.opciones){
    try{ML.opciones=await api('/api/modular/opciones')}catch(e){toast(e.message);return}
    ML.area=ML.opciones.areas[0];
    const hacer=(cont,items,clave,actual)=>{cont.textContent='';items.forEach(it=>{
      const b=document.createElement('button');b.type='button';b.textContent=it.nombre||it;
      const val=it.id||it;if(val===ML[clave])b.classList.add('on');
      b.addEventListener('click',()=>{ML[clave]=val;[...cont.children].forEach(x=>x.classList.toggle('on',x===b))});
      cont.appendChild(b)})};
    hacer($('ml-areas'),ML.opciones.areas,'area');
    hacer($('ml-niveles'),ML.opciones.niveles,'nivel');
  }
  mlProgreso();
}
function mlOcupado(boton,texto){const t=boton.textContent;boton.disabled=true;boton.textContent=texto;
  return ()=>{boton.disabled=false;boton.textContent=t}}
async function mlGenerar(variacionDe){
  const b=variacionDe?null:$('ml-generar');const listo=b?mlOcupado(b,'Generando caso…'):null;
  if(variacionDe)toast('Preparando la variación del caso…');
  try{
    const c=await api('/api/modular/caso',{body:variacionDe?{variacion_de:variacionDe}:{area:ML.area,nivel:ML.nivel}});
    mlMostrarCaso(c);
  }catch(e){toast(e.message)}
  if(listo)listo();
}
// Caso de repaso centrado en un concepto del mapa o del banco de errores.
async function practicarConcepto(id,nombre,boton){
  ver('modular');await mlInit();
  const orig=boton?boton.textContent:'';if(boton){boton.disabled=true;boton.textContent='Generando…'}
  toast('Preparando un caso para repasar «'+nombre+'»…');
  const g=$('ml-generar');const listo=mlOcupado(g,'Generando caso…');
  try{mlMostrarCaso(await api('/api/modular/caso',{body:{concepto_id:id}}))}catch(e){toast(e.message)}
  listo();if(boton){boton.disabled=false;boton.textContent=orig}
}
async function mlAbrirCaso(id){
  ver('modular');await mlInit();
  try{mlMostrarCaso(await api('/api/modular/caso/'+encodeURIComponent(id)))}catch(e){toast(e.message)}
}
function explicarConcepto(nombre){
  usarTool('Explícame el concepto «'+nombre+'» con un ejemplo sencillo y el error más común al aplicarlo en un caso.','ensename')}
function examinarConcepto(nombre){usarTool('Examíname sobre el concepto «'+nombre+'».','examiname')}
function mlMostrarCaso(c){
  ML.caso=c;ML.pistas=0;ML.evaluado=false;ML.confirmarSol=false;
  const nombreNivel=(ML.opciones&&ML.opciones.niveles.find(n=>n.id===c.nivel)||{}).nombre||c.nivel;
  const meta=$('ml-meta');meta.textContent='';
  [[c.area,'tag oro'],[nombreNivel,'tag'],[c.padre_id?'Variación':'Caso nuevo','tag']]
   .concat(c.foco?[['Repaso: '+c.foco,'tag oro']]:[]).forEach(([t,k])=>{
    const s=document.createElement('span');s.className=k;s.textContent=t;meta.appendChild(s)});
  $('ml-cambio').classList.toggle('hidden',!c.cambio);$('ml-cambio').textContent=c.cambio||'';
  $('ml-titulo').textContent=c.titulo;
  $('ml-enunciado').innerHTML=md(c.enunciado);
  $('ml-pregunta').textContent=c.pregunta;
  $('ml-pistas').textContent='';$('ml-resp').value='';mlContar();
  $('ml-btn-pista').disabled=false;$('ml-btn-pista').textContent=c.n_pistas?'Necesito una pista':'Explícame el concepto';
  $('ml-btn-sol').textContent='Ver solución';
  ['ml-eval','ml-sol'].forEach(id=>$(id).classList.add('hidden'));
  $('ml-caso').classList.remove('hidden');
  $('ml-caso').scrollIntoView({behavior:'smooth',block:'start'});
}
function mlContar(){const n=($('ml-resp').value.trim().match(/\S+/g)||[]).length;
  $('ml-cuenta').textContent=n+(n===1?' palabra':' palabras')}
async function mlPista(){
  if(!ML.caso)return;
  if(ML.pistas>=(ML.caso.n_pistas||0))return mlExplicame();
  try{
    const p=await api('/api/modular/pista',{body:{caso_id:ML.caso.id,n:ML.pistas}});
    const d=document.createElement('div');d.className='pista';
    const b=document.createElement('b');b.textContent='Pista '+(p.n+1)+': ';d.appendChild(b);
    d.appendChild(document.createTextNode(p.pista));$('ml-pistas').appendChild(d);
    ML.pistas++;
    if(!p.quedan){$('ml-btn-pista').textContent='Explícame el concepto'}
  }catch(e){toast(e.message)}
}
// Tercer escalón de ayuda (después de las pistas y antes de la solución): una explicación del
// concepto en el chat, sin resolver el caso.
async function mlExplicame(){
  try{
    const d=await api('/api/modular/conceptos?caso_id='+ML.caso.id);
    if(!d.conceptos.length){toast('Este caso no tiene conceptos registrados.');return}
    usarTool('Estoy resolviendo un caso de práctica y no quiero que me des la respuesta. Explícame '+
      (d.conceptos.length>1?'estos conceptos: ':'este concepto: ')+d.conceptos.join(', ')+
      '. Usa un ejemplo distinto a mi caso.','ensename');
  }catch(e){toast(e.message)}
}
async function mlEvaluar(){
  if(!ML.caso)return;
  const resp=$('ml-resp').value.trim();
  if(resp.length<40){toast('Escribe una respuesta más completa antes de evaluarla.');$('ml-resp').focus();return}
  const listo=mlOcupado($('ml-btn-eval'),'Evaluando…');
  try{const ev=await api('/api/modular/evaluar',{body:{caso_id:ML.caso.id,respuesta:resp}});
    ML.evaluado=true;mlMostrarEval(ev);mlProgreso();}catch(e){toast(e.message)}
  listo();
}
function mlLista(titulo,clase,items){
  const box=document.createElement('div');box.className='ev-box '+clase;
  const h=document.createElement('h4');h.textContent=titulo;box.appendChild(h);
  const ul=document.createElement('ul');
  (items&&items.length?items:['—']).forEach(t=>{const li=document.createElement('li');li.textContent=t;ul.appendChild(li)});
  box.appendChild(ul);return box;
}
function mlMostrarEval(ev){
  const p=$('ml-eval');p.textContent='';
  const h=document.createElement('h3');h.textContent='Tu evaluación';p.appendChild(h);
  const cab=document.createElement('div');cab.className='ev-cab';
  const tot=document.createElement('div');tot.className='ev-total';tot.textContent=ev.total;
  const sm=document.createElement('small');sm.textContent=' / 100';tot.appendChild(sm);cab.appendChild(tot);
  const com=document.createElement('div');com.className='ev-com';com.textContent=ev.comentario||'';cab.appendChild(com);
  p.appendChild(cab);
  const rub=document.createElement('div');rub.className='rub';
  ev.rubrica.forEach(r=>{const f=document.createElement('div');f.className='r';
    const n=document.createElement('span');n.textContent=r.nombre;
    const bar=document.createElement('div');bar.className='bar';const i=document.createElement('i');
    const pct=Math.round(100*r.puntaje/r.max);i.style.width=pct+'%';if(pct<60)i.className='bajo';bar.appendChild(i);
    const v=document.createElement('span');v.className='n';v.textContent=r.puntaje+'/'+r.max;
    f.appendChild(n);f.appendChild(bar);f.appendChild(v);rub.appendChild(f)});
  p.appendChild(rub);
  const g=document.createElement('div');g.className='ev-grid';
  g.appendChild(mlLista('Lo que identificaste','bien',ev.identificaste));
  g.appendChild(mlLista('Lo que omitiste','falta',ev.omitiste));
  g.appendChild(mlLista('Norma o institución que faltó','norma',ev.norma_faltante));
  g.appendChild(mlLista('Cómo mejorar','mejora',ev.como_mejorar));
  p.appendChild(g);
  if(ev.contraargumento){const c=document.createElement('div');c.className='ev-contra';
    const b=document.createElement('b');b.textContent='Argumento contrario que no consideraste: ';
    c.appendChild(b);c.appendChild(document.createTextNode(ev.contraargumento));p.appendChild(c)}
  if(ev.conocimiento&&ev.conocimiento.length){
    const box=document.createElement('div');box.className='aprendido';
    const h4=document.createElement('h4');h4.textContent='Tu mapa se actualizó';box.appendChild(h4);
    const ul=document.createElement('ul');
    const txt={fallo:'lo confundiste: vuelve a aparecer en tus repasos mañana',acierto:'bien aplicado: el próximo repaso se aleja',visto:'registrado en tu mapa'};
    ev.conocimiento.forEach(c=>{const li=document.createElement('li');const b=document.createElement('b');b.textContent=c.nombre;
      li.appendChild(b);li.appendChild(document.createTextNode(' — '+(txt[c.resultado]||'')));ul.appendChild(li)});
    box.appendChild(ul);
    const ir=document.createElement('button');ir.type='button';ir.textContent='Ver mi mapa';ir.addEventListener('click',()=>ver('mapa'));
    box.appendChild(ir);p.appendChild(box)}
  const acc=document.createElement('div');acc.className='ml-acc';
  [['Ver solución','bsec','mlSolucion'],['¿Qué cambia si…? (variación)','bsec','mlVariacion'],['Nuevo caso','bpri','mlNuevo']]
    .forEach(([t,k,f])=>{const b=document.createElement('button');b.className=k;b.textContent=t;b.dataset.click=f;acc.appendChild(b)});
  p.appendChild(acc);
  const nota=document.createElement('p');nota.className='nota-ia';
  nota.textContent='Evaluación orientativa generada por IA para practicar. No reemplaza la calificación de un docente.';
  p.appendChild(nota);
  p.classList.remove('hidden');p.scrollIntoView({behavior:'smooth',block:'start'});
}
async function mlSolucion(){
  if(!ML.caso)return;
  if(!ML.evaluado&&!ML.confirmarSol){ML.confirmarSol=true;
    $('ml-btn-sol').textContent='¿Seguro? Aún no la has intentado · Ver de todas formas';return}
  try{
    const s=await api('/api/modular/solucion?caso_id='+ML.caso.id);
    const p=$('ml-sol');p.textContent='';
    const h=document.createElement('h3');h.textContent='Solución de referencia';p.appendChild(h);
    const bloque=(t,txt)=>{if(!txt)return;const l=document.createElement('div');l.className='lb2';l.textContent=t;p.appendChild(l);
      const d=document.createElement('div');d.className='md';d.innerHTML=md(txt);p.appendChild(d)};
    bloque('Problema jurídico',s.problema_juridico);
    if(s.normas&&s.normas.length){const l=document.createElement('div');l.className='lb2';l.textContent='Marco normativo';p.appendChild(l);
      const c=document.createElement('div');c.className='sol-norma';
      s.normas.forEach(n=>{const d=document.createElement('div');const b=document.createElement('b');b.textContent=(n.norma||'')+': ';
        d.appendChild(b);d.appendChild(document.createTextNode(n.para_que||''));c.appendChild(d)});p.appendChild(c)}
    bloque('Análisis',s.analisis);bloque('Argumento contrario',s.contraargumento);bloque('Conclusión',s.conclusion);
    if(s.errores_comunes&&s.errores_comunes.length)p.appendChild(mlLista('Errores comunes en este caso','falta',s.errores_comunes));
    const nota=document.createElement('p');nota.className='nota-ia';
    nota.textContent='Solución generada por IA. Verifica la vigencia de cada norma en la fuente oficial antes de estudiarla como definitiva.';
    p.appendChild(nota);
    p.classList.remove('hidden');p.scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){toast(e.message)}
}
function mlVariacion(){if(ML.caso)mlGenerar(ML.caso.id)}
function mlNuevo(){['ml-caso','ml-eval','ml-sol'].forEach(id=>$(id).classList.add('hidden'));ML.caso=null;
  $('ml-config').scrollIntoView({behavior:'smooth',block:'start'})}
async function mlProgreso(){
  let p;try{p=await api('/api/modular/progreso')}catch(e){return}
  const c=$('ml-prog-cuerpo');if(!p.resueltos)return;
  c.className='';c.textContent='';
  const g=document.createElement('div');g.className='prog-grid';
  const varias=p.por_area.length>1;
  const cifras=[];
  [[p.resueltos,'casos evaluados'],[p.promedio+'/100','promedio general',p.promedio],
   [varias?p.por_area[0].area:(p.ultimos.length?p.ultimos[p.ultimos.length-1]+'/100':'—'),
    varias?'área con menor promedio':'último caso']].forEach(([v,t,num])=>{
    const d=document.createElement('div');d.className='prog-n';const b=document.createElement('b');b.textContent=v;
    if(typeof v==='number')cifras.push([b,v,'']);else if(typeof num==='number')cifras.push([b,num,'/100']);
    const s=document.createElement('span');s.textContent=t;d.appendChild(b);d.appendChild(s);g.appendChild(d)});
  c.appendChild(g);
  if(window.MV&&MV.contar)cifras.forEach(([b,v,suf])=>MV.contar(b,v,{sufijo:suf}));
  const rub=document.createElement('div');rub.className='rub';
  p.por_area.forEach(a=>{const f=document.createElement('div');f.className='r';
    const n=document.createElement('span');n.textContent=a.area+' ('+a.intentos+')';
    const bar=document.createElement('div');bar.className='bar';const i=document.createElement('i');i.style.width=a.promedio+'%';
    if(a.promedio<60)i.className='bajo';bar.appendChild(i);
    const v=document.createElement('span');v.className='n';v.textContent=a.promedio;
    f.appendChild(n);f.appendChild(bar);f.appendChild(v);rub.appendChild(f)});
  c.appendChild(rub);
  if(p.a_reforzar&&p.a_reforzar.length){const l=document.createElement('div');l.className='lb2';l.textContent='Conceptos para reforzar';c.appendChild(l);
    const o=document.createElement('div');o.className='opc';
    p.a_reforzar.forEach(t=>{const b=document.createElement('button');b.type='button';b.textContent=t;
      b.addEventListener('click',()=>usarTool('Quiero entender bien este concepto porque me equivoco con él: '+t,'ensename'));o.appendChild(b)});
    c.appendChild(o)}
}

// ------------------------------------------------------------------ Academia: tablero --
const NOMBRE_EST={dominado:'Dominado',en_progreso:'En progreso',debil:'Débil',sin_evaluar:'Sin evaluar'};
const NOMBRE_NIVEL={basico:'Básico',intermedio:'Intermedio',avanzado:'Avanzado',experto:'Experto'};
function el(tag,cls,txt){const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e}
function estadoChip(est){return el('span','est '+est,NOMBRE_EST[est]||est)}
function boton(txt,cls,fn){const b=el('button',cls,txt);b.type='button';b.addEventListener('click',()=>fn(b));return b}
async function cargarTablero(){
  const t=$('tablero');
  if(CAMINO!=='aprender'){t.classList.add('hidden');return}
  if(typeof tieneFuncion==='function'&&!tieneFuncion('academia')){ // sin Academia: una invitación, sin llamar a la API
    t.textContent='';const c=el('div','tcard mejora-tc');const k=el('div','k');k.appendChild(plIcono('candado'));
    k.appendChild(document.createTextNode(' Laboratorio de casos · plan '+plNombre(plRequerido('academia'))));c.appendChild(k);
    c.appendChild(el('div','v','Practica casos tipo examen y deja que PULLEX te evalúe'));
    c.appendChild(el('div','s','Rúbrica, mapa de lo que dominas y repasos espaciados. Mientras tanto, «Enséñame», «Resuélvelo conmigo» y «Examíname» funcionan en Consultar.'));
    c.appendChild(boton('Conocer el plan '+plNombre(plRequerido('academia')),'bsec',()=>ver('modular')));
    t.appendChild(c);t.classList.remove('hidden');return}
  if(!t.children.length){ // esqueleto mientras llega el tablero (clase distinta de .tcard a propósito)
    for(let i=0;i<2;i++){const c=el('div','tcard-esq panel');c.style.cssText='margin:0;padding:16px 18px';
      [40,85,60].forEach(w=>{const k=el('div','skel');k.style.width=w+'%';c.appendChild(k)});t.appendChild(c)}
    t.classList.remove('hidden')}
  let r;try{r=await api('/api/academia/resumen')}catch(e){t.textContent='';t.classList.add('hidden');return}
  t.textContent='';
  const card=(k,v,sub,acc,cls)=>{const c=el('div','tcard'+(cls?' '+cls:''));c.appendChild(el('div','k',k));
    c.appendChild(el('div','v',v));if(sub)c.appendChild(el('div','s',sub));if(acc)c.appendChild(acc);t.appendChild(c)};
  const rec=r.caso_recomendado;
  if(rec){
    const v=rec.concepto?rec.concepto+' · '+rec.area:rec.area;
    card('Caso recomendado',v,rec.motivo+' Nivel sugerido: '+(NOMBRE_NIVEL[rec.nivel]||rec.nivel)+'.',
      boton('Practicar ahora','bpri',b=>rec.concepto_id?practicarConcepto(rec.concepto_id,rec.concepto,b)
        :(ver('modular'),mlInit().then(()=>mlElegir(rec.area,rec.nivel)))),'rec')}
  if(r.continuar)card('Continuar estudiando',r.continuar.titulo,r.continuar.area+' · caso sin responder',
    boton('Retomar caso','bsec',()=>mlAbrirCaso(r.continuar.caso_id)));
  if(r.proximo_repaso&&(r.n_repasos_hoy>1||!rec||rec.concepto_id!==r.proximo_repaso.id)){const pr=r.proximo_repaso;
    card('Próximo repaso',pr.nombre,pr.area+' · '+(r.n_repasos_hoy>1?r.n_repasos_hoy+' conceptos para hoy':'toca '+pr.proximo_texto),
      boton('Ver repasos','bsec',()=>ver('mapa')))}
  if(r.tema_debil&&(!rec||rec.concepto_id!==r.tema_debil.id))card('Tema débil',r.tema_debil.nombre,
    'Lo has confundido '+r.tema_debil.fallos+(r.tema_debil.fallos===1?' vez':' veces')+'.',
    boton('Explícamelo','bsec',()=>explicarConcepto(r.tema_debil.nombre)));
  if(r.ultimo_modular)card('Último caso',r.ultimo_modular.titulo,r.ultimo_modular.area+' · '+r.ultimo_modular.puntaje+'/100',
    boton('Mi mapa','bsec',()=>ver('mapa')));
  t.classList.toggle('hidden',!t.children.length);
}
function mlElegir(area,nivel){
  [['area',area,'ml-areas'],['nivel',nivel,'ml-niveles']].forEach(([k,v,id])=>{if(!v)return;ML[k]=v;
    const items=k==='area'?ML.opciones.areas:ML.opciones.niveles.map(n=>n.id);
    [...$(id).children].forEach((b,i)=>b.classList.toggle('on',items[i]===v))});
  $('ml-config').scrollIntoView({behavior:'smooth',block:'start'});
  toast('Elegí '+area+(nivel?' · '+(NOMBRE_NIVEL[nivel]||nivel):'')+'. Pulsa «Generar caso».');
}

// ------------------------------------------------------------------ Academia: Mi mapa --
const MAPA={datos:null,area:null,sel:null};
async function mapaInit(){
  let d,err,res;
  const rs=$('mapa-res');
  if(!rs.children.length){rs.setAttribute('aria-busy','true');      // primera carga: cuatro casillas en esqueleto
    for(let i=0;i<4;i++){const c=el('div','esq');c.appendChild(el('span','skel'));c.appendChild(el('span','skel'));rs.appendChild(c)}}
  try{[d,err,res]=await Promise.all([api('/api/academia/mapa'),api('/api/academia/errores'),api('/api/academia/resumen')])}
  catch(e){rs.removeAttribute('aria-busy');rs.querySelectorAll('.esq').forEach(x=>x.remove());toast(e.message);return}
  MAPA.datos=d;
  rs.removeAttribute('aria-busy');rs.textContent='';
  ['dominado','en_progreso','debil','sin_evaluar'].forEach(k=>{const c=el('div');const b=el('b',null,d.resumen[k]);c.appendChild(b);
    c.appendChild(estadoChip(k));rs.appendChild(c);
    if(window.MV&&MV.contar&&typeof d.resumen[k]==='number')MV.contar(b,d.resumen[k])});
  pintarRepasos(res);pintarErrores(err.errores);
  if(!MAPA.area){const deb=d.areas.find(a=>a.resumen.debil);MAPA.area=(deb||d.areas[0]).area}
  const ar=$('mapa-areas');ar.textContent='';
  d.areas.forEach(a=>{const b=boton(a.area+(a.resumen.debil?' · '+a.resumen.debil+(a.resumen.debil===1?' débil':' débiles'):''),'',()=>{MAPA.area=a.area;MAPA.sel=null;pintarAreaMapa()});
    b.setAttribute('role','tab');ar.appendChild(b)});
  pintarAreaMapa();
}
function filaConcepto(c,extra,acciones){
  const f=el('div','rep');const t=el('div','t');t.appendChild(el('b',null,c.nombre));
  t.appendChild(el('span',null,extra));f.appendChild(t);
  const a=el('div','racc');acciones.forEach(x=>a.appendChild(x));f.appendChild(a);return f;
}
function pintarRepasos(r){
  const c=$('mapa-hoy-cuerpo');
  if(!r.proximo_repaso){c.className='vacio';return}
  c.className='rep-lista';c.textContent='';
  const lista=r.repasos_hoy.length?r.repasos_hoy:[r.proximo_repaso];
  if(!r.repasos_hoy.length)c.appendChild(el('div','vacio','Nada pendiente para hoy. Tu próximo repaso:'));
  lista.forEach(x=>c.appendChild(filaConcepto(x,x.area+' · '+(x.proximo_texto==='hoy'?'toca hoy':'toca '+x.proximo_texto),
    [estadoChip(x.estado),boton('Practicar','bpri',b=>practicarConcepto(x.id,x.nombre,b))])));
}
function pintarErrores(lista){
  const c=$('mapa-err-cuerpo');
  if(!lista.length){c.className='vacio';return}
  c.className='rep-lista';c.textContent='';
  lista.forEach(e=>{
    const extra=e.area+' · lo confundiste '+e.frecuencia+(e.frecuencia===1?' vez':' veces')+(e.resuelto?' · superado':'');
    const sev=el('span','sev '+e.severidad,e.resuelto?'superado':'severidad '+e.severidad);
    const f=filaConcepto(e,extra,[sev,estadoChip(e.estado),
      boton('Explícamelo','bsec',()=>explicarConcepto(e.nombre)),
      boton('Practicar','bpri',b=>practicarConcepto(e.id,e.nombre,b))]);
    if(e.resuelto)f.classList.add('superado');c.appendChild(f)});
}
function pintarAreaMapa(){
  const a=MAPA.datos.areas.find(x=>x.area===MAPA.area);
  [...$('mapa-areas').children].forEach((b,i)=>{const on=MAPA.datos.areas[i].area===a.area;b.classList.toggle('on',on);b.setAttribute('aria-selected',on)});
  const info=$('mapa-area-info');info.textContent='';
  const partes=[['Dominados',a.resumen.dominado],['En progreso',a.resumen.en_progreso],['Débiles',a.resumen.debil]];
  partes.forEach(([t,n],i)=>{info.appendChild(document.createTextNode((i?' · ':'')+t+': '));info.appendChild(el('b',null,n))});
  info.appendChild(document.createTextNode(a.promedio!=null?' · Promedio en casos: ':' · Aún sin casos resueltos en esta área'));
  if(a.promedio!=null){info.appendChild(el('b',null,a.promedio+'/100'))}
  info.appendChild(document.createTextNode(' · Nivel sugerido: '));info.appendChild(el('b',null,NOMBRE_NIVEL[a.nivel_recomendado]));
  const cont=$('mapa-temas');cont.textContent='';
  a.temas.forEach(t=>{
    const s=el('div','tema');s.appendChild(el('h4',null,t.tema));
    const g=el('div','nodos');
    t.conceptos.forEach(c=>{
      const n=el('button','nodo '+c.estado);n.type='button';n.setAttribute('aria-expanded',MAPA.sel===c.id);
      n.appendChild(el('span',null,c.nombre));n.appendChild(estadoChip(c.estado));
      n.addEventListener('click',()=>{MAPA.sel=MAPA.sel===c.id?null:c.id;pintarAreaMapa()});
      if(MAPA.sel===c.id)n.classList.add('sel');
      g.appendChild(n);
      if(MAPA.sel===c.id){
        const d=el('div','nodo-det');d.appendChild(el('b',null,c.nombre));d.appendChild(el('p',null,c.desc));
        const hist=c.aciertos||c.fallos?'Aciertos: '+c.aciertos+' · Errores: '+c.fallos+(c.proximo_texto?' · Próximo repaso: '+c.proximo_texto:''):'Aún no lo has practicado.';
        d.appendChild(el('p',null,hist));
        const acc=el('div','racc');
        if(a.practicable)acc.appendChild(boton('Practicar este concepto','bpri',b=>practicarConcepto(c.id,c.nombre,b)));
        acc.appendChild(boton('Explícamelo','bsec',()=>explicarConcepto(c.nombre)));
        acc.appendChild(boton('Examíname','bsec',()=>examinarConcepto(c.nombre)));
        d.appendChild(acc);g.appendChild(d);
      }
    });
    s.appendChild(g);cont.appendChild(s);
  });
}

// ------------------------------------------------------------- Apariencia (por usuario) --
// El motor de color y los atributos de <html> están en static/apariencia.js (PXA), que corre antes de
// pintar. Aquí: los controles de Ajustes → Apariencia, el guardado en la cuenta (con espera corta para
// no enviar una petición por cada clic) y las imágenes (fondo del Inicio, foto de perfil, logo).
const TEMAS_AP=[
  {id:'justicia',n:'Justicia × Inteligencia',d:'Grafito, lima y cian',c:['#f3f5f8','#101115','#101115'],o:['#101115','#f4f6f9','#d9ff68']},
  {id:'pullex',n:'PULLEX',d:'Papel, tinta y bermellón',c:['#f7f5f0','#1b1a17','#b33a16'],o:['#141311','#eeebe4','#ee7a4f']},
  {id:'notario',n:'Notario',d:'Marfil y tinta',c:['#fbf8f1','#1a1d24','#22385e'],o:['#101218','#ece8df','#a9bee3']},
  {id:'bogota',n:'Bogotá',d:'Gris piedra y pizarra',c:['#efefec','#1c1f22','#2d5876'],o:['#151718','#e8eaeb','#8db7d6']},
  {id:'caribe',n:'Caribe',d:'Arena y turquesa',c:['#f8f3e8','#1d2321','#0a7570'],o:['#0f1716','#eaf1ee','#3cc7bd']},
  {id:'toga',n:'Toga',d:'Negro y vino',c:['#f5f4f2','#121212','#7b1e34'],o:['#0a0a0a','#f0edee','#d96f87']},
  {id:'jardin',n:'Jardín',d:'Verde salvia',c:['#f2f4ef','#1a1f1b','#43654e'],o:['#121613','#e9eee9','#9bc4a5']}];
const ACENTOS_AP=[['Bermellón','#b33a16'],['Tinta','#22385e'],['Cobalto','#2f54c9'],['Turquesa','#0a7570'],
  ['Salvia','#43654e'],['Vino','#7b1e34'],['Ocre','#93600c'],['Grafito','#3d3c39']];
const FUENTES_AP=[['syne','Futurista','Syne + Plus Jakarta','var(--syne)'],['editorial','Editorial','Fraunces + Inter','var(--serif-editorial)'],
  ['clasica','Clásica','Source Serif','var(--serif-lectura)'],['moderna','Moderna','Inter','var(--sans)']];
const IMGS_AP={fondo:['Fondo del Inicio','Una foto tuya, de tu ciudad o de tu oficina. Se ajusta a 1600 px.',350],
  avatar:['Foto de perfil','Se recorta en cuadrado de 256 px.',120],logo:['Logo propio','Reemplaza el monograma en la cabecera. PNG con fondo transparente queda mejor.',120]};
const AP={datos:null,pend:{},timer:null,urls:{fondo:null,avatar:null,logo:null},hecho:false};

function apIniciar(){
  const a=(PERFIL&&PERFIL.preferencias&&PERFIL.preferencias.apariencia)||{};
  // «Movimiento» aún no viaja a la cuenta (el servidor no tiene ese campo): se conserva la elección de este navegador.
  const local=PXA.leerLocal();
  AP.datos=PXA.normalizar({...a,movimiento:a.movimiento||(local&&local.movimiento)});PXA.aplicar(AP.datos);PXA.guardarLocal(AP.datos);
  construirApariencia();apRefrescar();cargarImagenesAp();
}
function apEstado(t,ok){const e=$('ap-estado');if(!e)return;e.textContent=t||'';e.classList.toggle('ok',!!ok)}
// Aplica en vivo, guarda en este navegador (para pintar rápido la próxima vez) y en la cuenta.
function apCambiar(c){
  AP.datos={...(AP.datos||PXA.actual()),...c};PXA.aplicar(AP.datos);PXA.guardarLocal(AP.datos);apRefrescar();
  // «Movimiento» se guarda solo en este navegador; no se anuncia como guardado en la cuenta porque no lo está.
  const {movimiento,...deCuenta}=c;
  if(!Object.keys(deCuenta).length){if(!Object.keys(AP.pend).length)apEstado('Guardado en este navegador',true);return}
  Object.assign(AP.pend,deCuenta);clearTimeout(AP.timer);apEstado('Guardando…');AP.timer=setTimeout(apGuardar,450);
}
async function apGuardar(){
  const pend=AP.pend;AP.pend={};if(!Object.keys(pend).length)return;
  try{const d=await api('/api/preferencias',{body:{apariencia:pend}});
    PERFIL.preferencias={...PERFIL.preferencias,...d.preferencias};apEstado('Guardado en tu cuenta',true)}
  catch(e){apEstado('No se pudo guardar');toast(e.message)}
}
function boton2(cls,fn){const b=el('button',cls);b.type='button';b.addEventListener('click',()=>fn(b));return b}
function icoUse(id,cls){return '<svg class="i '+(cls||'s')+'" aria-hidden="true"><use href="#i-'+id+'"/></svg>'}
function construirApariencia(){
  const c=$('ap-controles');if(!c||AP.hecho)return;AP.hecho=true;c.textContent='';
  const titulo=t=>c.appendChild(el('div','lb2',t));
  const seg=(clave,ops)=>{const g=el('div','seg');g.setAttribute('role','radiogroup');g.dataset.clave=clave;
    ops.forEach(([v,t,ic])=>{const b=boton2('',()=>apCambiar({[clave]:v}));b.dataset.v=v;b.setAttribute('role','radio');
      if(ic)b.innerHTML=icoUse(ic,'xs');b.appendChild(document.createTextNode(t));g.appendChild(b)});return g};
  titulo('Modo');
  c.appendChild(seg('modo',[['claro','Claro','sol'],['oscuro','Oscuro','luna'],['auto','Automático','auto']]));
  titulo('Tema');
  const tg=el('div','temas');tg.id='ap-temas';
  TEMAS_AP.forEach(t=>{const b=boton2('tema-op',()=>apCambiar({tema:t.id,acento:null}));b.dataset.v=t.id;
    const m=el('span','mues');m.innerHTML='<i class="l1"></i><i class="l2"></i><i class="pt"></i>';b.appendChild(m);
    const n=el('span','nom',t.n);n.appendChild(el('span',null,t.d));b.appendChild(n);tg.appendChild(b)});
  c.appendChild(tg);
  titulo('Color de acento');
  const ac=el('div','acentos');ac.id='ap-acentos';
  const delTema=boton2('acento-tema',()=>apCambiar({acento:null}));delTema.textContent='El del tema';delTema.dataset.v='';ac.appendChild(delTema);
  ACENTOS_AP.forEach(([n,h])=>{const b=boton2('acento-op',()=>apCambiar({acento:h}));b.dataset.v=h;b.title=n;
    b.setAttribute('aria-label','Acento '+n);b.style.background=h;ac.appendChild(b)});
  const lib=el('label','acento-libre');lib.title='Elige cualquier color: PULLEX ajusta el contraste para que se lea bien';
  lib.appendChild(document.createTextNode('Otro'));
  const inp=document.createElement('input');inp.type='color';inp.id='ap-color';inp.value='#b33a16';inp.setAttribute('aria-label','Color de acento libre');
  inp.addEventListener('input',()=>apCambiar({acento:inp.value.toLowerCase()}));lib.appendChild(inp);ac.appendChild(lib);
  c.appendChild(ac);
  titulo('Tipografía');
  const fg=el('div','fuentes-op');fg.id='ap-fuentes';
  FUENTES_AP.forEach(([v,n,d,f])=>{const b=boton2('fuente-op',()=>apCambiar({fuente:v}));b.dataset.v=v;
    const aa=el('span','aa','Aa');aa.style.fontFamily=f;aa.style.fontWeight=v==='moderna'?'650':v==='syne'?'600':'560';b.appendChild(aa);
    b.appendChild(el('span','n',n+' · '+d));fg.appendChild(b)});
  c.appendChild(fg);
  const g3=el('div','ap-grid3');
  [['Tamaño del texto','tamano',[['normal','Normal'],['grande','Grande']]],
   ['Densidad','densidad',[['comoda','Cómoda'],['compacta','Compacta']]],
   ['Esquinas','radio',[['recto','Rectas'],['suave','Suaves'],['redondo','Redondas']]],
   ['Movimiento','movimiento',[['completo','Completo'],['reducido','Reducido']]]].forEach(([t,k,ops])=>{
    const w=el('div');w.appendChild(el('div','lb2',t));w.appendChild(seg(k,ops));g3.appendChild(w)});
  c.appendChild(g3);
  const nm=el('p','vacio');nm.id='ap-mov-nota';nm.style.cssText='font-size:.8rem;margin:10px 0 0';c.appendChild(nm);
  titulo('Imágenes');
  Object.entries(IMGS_AP).forEach(([tipo,[n,d]])=>{
    const f=el('div','img-fila');
    const mini=el('span','mini'+(tipo==='avatar'?' red':tipo==='logo'?' logo':''));mini.id='ap-mini-'+tipo;
    mini.innerHTML=icoUse('imagen','s');f.appendChild(mini);
    const tx=el('div','tx');tx.appendChild(el('b',null,n));tx.appendChild(el('span',null,d));f.appendChild(tx);
    const bt=el('div','bt');
    const file=document.createElement('input');file.type='file';file.accept='image/png,image/jpeg,image/webp';file.className='hidden';
    file.id='ap-file-'+tipo;file.addEventListener('change',()=>apSubir(tipo,file));
    const sub=boton2('bsec',()=>file.click());sub.id='ap-subir-'+tipo;sub.innerHTML=icoUse('subir','xs');sub.appendChild(document.createTextNode('Subir'));
    const qui=boton2('bghost',()=>apQuitar(tipo));qui.id='ap-quitar-'+tipo;qui.textContent='Quitar';
    bt.appendChild(file);bt.appendChild(sub);bt.appendChild(qui);f.appendChild(bt);c.appendChild(f)});
  const pie=el('div','ap-pie');
  pie.appendChild(boton2('bsec',apRestablecer)).textContent='Restablecer apariencia';
  pie.appendChild(el('p',null,'Los colores se ajustan solos para que el texto siempre se lea bien (contraste AA).'));
  c.appendChild(pie);
}
// Marca la opción activa de cada control y pinta las muestras de tema según el modo actual.
function apRefrescar(){
  sincronizarSwTema();
  const a=AP.datos||PXA.actual();const c=$('ap-controles');if(!c||!AP.hecho)return;
  const oscuro=document.documentElement.getAttribute('data-esquema')==='oscuro';
  c.querySelectorAll('.seg').forEach(g=>{[...g.children].forEach(b=>{const on=a[g.dataset.clave]===b.dataset.v;
    b.classList.toggle('on',on);b.setAttribute('aria-checked',String(on))})});
  $('ap-temas').querySelectorAll('.tema-op').forEach((b,i)=>{const t=TEMAS_AP[i],k=oscuro?t.o:t.c;
    b.classList.toggle('on',a.tema===t.id);b.setAttribute('aria-pressed',String(a.tema===t.id));
    const m=b.querySelector('.mues');m.style.background=k[0];
    m.querySelector('.l1').style.background=k[1];m.querySelector('.l2').style.background=k[1];m.querySelector('.pt').style.background=k[2]});
  let libre=!!a.acento;
  $('ap-acentos').querySelectorAll('.acento-op,.acento-tema').forEach(b=>{const on=(b.dataset.v||null)===a.acento;
    if(on&&a.acento)libre=false;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on))});
  const lib=$('ap-acentos').querySelector('.acento-libre');lib.classList.toggle('on',libre);
  if(a.acento&&$('ap-color').value!==a.acento)$('ap-color').value=a.acento;
  $('ap-fuentes').querySelectorAll('.fuente-op').forEach(b=>{const on=b.dataset.v===a.fuente;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on))});
  const nm=$('ap-mov-nota');
  if(nm){let sis=false;try{sis=window.matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){}
    nm.textContent=sis?'Tu sistema pide menos movimiento y PULLEX lo respeta: las animaciones están apagadas aunque aquí diga «Completo».'
      :a.movimiento==='reducido'?'Movimiento reducido: sin entradas animadas, sin paralaje y sin transiciones entre secciones. Esta opción se guarda en este navegador.'
      :'Movimiento completo. Si te marea o te distrae, elige «Reducido»: todo aparece ya en su sitio. Esta opción se guarda en este navegador.'}
}

// ---- imágenes: se ajustan en el navegador (canvas) y viajan como data URL JPEG/PNG; el servidor
// vuelve a validar tipo real, peso y dimensiones. Se muestran como blob: (o data:) — CSP img-src lo permite.
function bytesDataUrl(u){const b=(u.split(',')[1]||'');return Math.floor(b.length*3/4)}
function cargarImagen(file){return new Promise((ok,mal)=>{const u=URL.createObjectURL(file);const im=new Image();
  im.onload=()=>{ok(im);URL.revokeObjectURL(u)};
  im.onerror=()=>{URL.revokeObjectURL(u);mal(new Error('No pudimos leer esa imagen. Prueba con un JPG o PNG.'))};im.src=u})}
async function procesarImagen(file,tipo){
  if(!/^image\/(png|jpeg|webp)$/i.test(file.type||''))throw new Error('Usa una imagen JPG, PNG o WebP.');
  if(file.size>20*1024*1024)throw new Error('La imagen es muy grande (máximo 20 MB).');
  const im=await cargarImagen(file),W=im.naturalWidth,H=im.naturalHeight;
  if(!W||!H)throw new Error('No pudimos leer esa imagen.');
  const tope=IMGS_AP[tipo][2]*1024,c=document.createElement('canvas'),x=c.getContext('2d');
  const pintar=(w,h,sx,sy,sw,sh,fondo)=>{c.width=w;c.height=h;x.clearRect(0,0,w,h);
    if(fondo){x.fillStyle=fondo;x.fillRect(0,0,w,h)}x.imageSmoothingQuality='high';x.drawImage(im,sx,sy,sw,sh,0,0,w,h)};
  const jpeg=calidades=>{for(const q of calidades){const u=c.toDataURL('image/jpeg',q);if(bytesDataUrl(u)<=tope)return u}return null};
  if(tipo==='avatar'){const l=Math.min(W,H);pintar(256,256,(W-l)/2,(H-l)/2,l,l,'#ffffff');
    const u=jpeg([.86,.76,.66]);if(u)return u;throw new Error('No pudimos reducir la foto lo suficiente.')}
  if(tipo==='logo'){const e=Math.min(1,512/W,128/H);const w=Math.max(1,Math.round(W*e)),h=Math.max(1,Math.round(H*e));
    pintar(w,h,0,0,W,H,null);const u=c.toDataURL('image/png');if(bytesDataUrl(u)<=tope)return u;
    pintar(w,h,0,0,W,H,'#ffffff');const j=jpeg([.9,.8]);if(j)return j;throw new Error('El logo pesa demasiado. Prueba con uno más sencillo.')}
  let lado=1600;
  for(let i=0;i<6;i++){const e=Math.min(1,lado/Math.max(W,H));pintar(Math.round(W*e),Math.round(H*e),0,0,W,H,'#ffffff');
    const u=jpeg([.8,.72,.64,.56]);if(u)return u;lado=Math.round(lado*.82)}
  throw new Error('No pudimos reducir la imagen lo suficiente. Prueba con otra.');
}
function ponerImagen(tipo,url){const v=AP.urls[tipo];if(v&&v!==url&&v.startsWith('blob:'))URL.revokeObjectURL(v);AP.urls[tipo]=url;pintarImagenes()}
function pintarImagenes(){
  const {fondo,avatar,logo}=AP.urls;
  ['hero','pv-hero'].forEach(id=>{const h=$(id);if(!h)return;h.classList.toggle('con-fondo',!!fondo);
    if(fondo)h.style.setProperty('--fondo-inicio','url("'+fondo+'")');else h.style.removeProperty('--fondo-inicio')});
  [['h-avatar-img','h-iniciales'],['cf-avatar-img','cf-iniciales'],['pv-avatar-img','pv-iniciales']].forEach(([i,t])=>{
    const im=$(i);if(avatar)im.src=avatar;else im.removeAttribute('src');im.classList.toggle('hidden',!avatar);$(t).classList.toggle('hidden',!!avatar)});
  document.querySelector('.h-logo').classList.toggle('con-logo',!!logo);
  [['h-logo-img','h-mono'],['pv-logo','pv-mono']].forEach(([i,m])=>{
    const im=$(i);if(logo)im.src=logo;else im.removeAttribute('src');im.classList.toggle('hidden',!logo);$(m).classList.toggle('hidden',!!logo)});
  Object.keys(IMGS_AP).forEach(tipo=>{const m=$('ap-mini-'+tipo);if(!m)return;const u=AP.urls[tipo];
    if(u){m.textContent='';const im=document.createElement('img');im.alt='';im.src=u;m.appendChild(im)}else m.innerHTML=icoUse('imagen','s');
    $('ap-quitar-'+tipo).classList.toggle('hidden',!u);
    const s=$('ap-subir-'+tipo);s.lastChild.textContent=u?'Cambiar':'Subir'});
}
async function cargarImagenesAp(){
  const v=(PERFIL.preferencias.apariencia&&PERFIL.preferencias.apariencia.imagenes)||{};
  pintarImagenes();
  await Promise.all(Object.keys(IMGS_AP).map(async tipo=>{
    if(!v[tipo]){ponerImagen(tipo,null);return}
    try{const r=await fetch('/api/apariencia/imagen/'+tipo,{headers:auth()});
      if(r.ok)ponerImagen(tipo,URL.createObjectURL(await r.blob()))}catch(e){}
  }));
}
async function apSubir(tipo,input){
  const f=input.files&&input.files[0];input.value='';if(!f)return;
  const b=$('ap-subir-'+tipo);b.disabled=true;apEstado('Ajustando la imagen…');
  try{const url=await procesarImagen(f,tipo);
    const d=await api('/api/preferencias',{body:{apariencia:{[tipo]:url}}});
    PERFIL.preferencias={...PERFIL.preferencias,...d.preferencias};ponerImagen(tipo,url);
    apEstado('Imagen guardada en tu cuenta',true);
    if(tipo==='fondo')toast('Listo: así se verá tu Inicio.');
  }catch(e){apEstado('');toast(e.message||'No se pudo usar esa imagen.')}
  b.disabled=false;
}
async function apQuitar(tipo){
  try{const d=await api('/api/preferencias',{body:{apariencia:{[tipo]:null}}});
    PERFIL.preferencias={...PERFIL.preferencias,...d.preferencias};ponerImagen(tipo,null);apEstado('Imagen quitada',true)}
  catch(e){toast(e.message)}
}
async function apRestablecer(){
  if(!confirm('¿Volver a la apariencia original de PULLEX? También se quitan tu fondo, tu foto y tu logo.'))return;
  clearTimeout(AP.timer);AP.pend={};
  AP.datos={...PXA.DEFECTO};PXA.aplicar(AP.datos);PXA.guardarLocal(AP.datos);apRefrescar();
  try{const d=await api('/api/preferencias',{body:{apariencia:{...PXA.DEFECTO,fondo:null,avatar:null,logo:null}}});
    PERFIL.preferencias={...PERFIL.preferencias,...d.preferencias};
    Object.keys(IMGS_AP).forEach(t=>ponerImagen(t,null));apEstado('Apariencia restablecida',true)}
  catch(e){toast(e.message)}
}

// ---------------------------------------------------------------------------------------
// Despachador de eventos (Fase 1b de seguridad). Los botones declaran data-click="funcion"
// en vez de onclick="...": así la política de seguridad (CSP) puede prohibir todo JavaScript
// en línea. Solo se ejecutan funciones de esta lista blanca.
const ACCIONES={toggleMas,abrirClave,abrirEscrito,abrirRecuperar,abrirSelectorArchivo,abrirTools,autoAlto,cargarBoletin,cerrarClave,cerrarEscrito,cerrarRecuperar,cerrarSesiones,cerrarTools,elegirCamino,enviar,enviarAuth,enviarEscrito,enviarRecuperar,escritoTipo,exportarExcel,guardarClave,guardarMemoria,guardarPrefs,imprimirPDF,instalarApp,mlContar,mlEvaluar,mlGenerar,mlNuevo,mlPista,mlSolucion,mlVariacion,modoAuth,nuevaConsulta,reenviarVerificacion,salir,sug,teclas,toggleHistorial,togglePref,toggleTema,toggleWeb,tomarArchivos,ver};
function despachar(tipo,ev){
  const el=ev.target.closest&&ev.target.closest('[data-'+tipo+']');if(!el)return;
  const fn=ACCIONES[el.dataset[tipo]];if(!fn)return;
  const T=tipo[0].toUpperCase()+tipo.slice(1);
  if(('prevenir'+T) in el.dataset)ev.preventDefault();
  const pasa=el.dataset['pasa'+T];
  if(pasa==='this')return fn(el);
  if(pasa==='event')return fn(ev);
  if(('arg'+T) in el.dataset){const a=el.dataset['arg'+T];return fn(a==='true'?true:a==='false'?false:a)}
  return fn();
}
// Los clics de navegación pasan por la transición entre secciones (static/movimiento.js) cuando el navegador la
// tiene. Las llamadas internas a ver() siguen siendo inmediatas: hay código que necesita la vista ya cambiada en la
// línea siguiente (enfocar el cuadro de texto, desplazar hasta un panel).
// La transición aplica el cambio un cuadro después del clic. Si entre tanto hubo otra navegación (otro clic o un
// ver() interno), esa es la que vale: el cambio viejo se descarta en vez de pisarla.
function verNav(v){const actual=$('v-'+v);
  if(window.MV&&MV.transicion&&!(actual&&actual.classList.contains('on'))){
    const turno=TURNO_VER;MV.transicion(()=>{if(turno===TURNO_VER)ver(v)})}
  else ver(v)}
ACCIONES.ver=verNav;
['click','change','input','keydown'].forEach(t=>document.addEventListener(t,ev=>despachar(t,ev)));

