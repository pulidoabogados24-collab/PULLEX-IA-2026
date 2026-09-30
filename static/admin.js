const $=id=>document.getElementById(id);let TOKEN=null,PLANES={};
async function entrar(){
  $('msg').textContent='';
  try{
    const r=await fetch('/api/login',{method:'POST',headers:{'content-type':'application/json'},
      body:JSON.stringify({email:$('e').value.trim(),clave:$('c').value})});
    const d=await r.json();
    if(!r.ok){$('msg').textContent=d.detail||'No se pudo';return}
    if(!d.perfil.es_admin){$('msg').textContent='Esta cuenta no es de administrador';return}
    TOKEN=d.token;$('login').style.display='none';$('panel').style.display='block';cargar();
  }catch(e){$('msg').textContent='Error de conexión'}
}
async function cargar(){
  const d=await(await fetch('/api/admin/usuarios',{headers:{'Authorization':'Bearer '+TOKEN}})).json();
  PLANES=d.planes;const us=d.usuarios;
  const activos=us.filter(u=>u.activo&&!u.es_admin).length;
  const total=us.filter(u=>!u.es_admin).length;
  const pagos=us.filter(u=>u.plan!=='prueba'&&!u.es_admin).length;
  $('stats').innerHTML=`
    <div class="stat"><div class="n">${total}</div><div class="l">Estudiantes</div></div>
    <div class="stat"><div class="n">${activos}</div><div class="l">Activos</div></div>
    <div class="stat"><div class="n">${pagos}</div><div class="l">Con plan pago</div></div>`;
  cargarNegocio();
  // Filas construidas con DOM + textContent: nombre y correo los escribe el propio estudiante
  // al registrarse, así que NUNCA se interpolan como HTML (evita XSS almacenado que robaría
  // la sesión del administrador). Los botones usan addEventListener, no onclick con texto.
  const tb=$('tb');tb.textContent='';
  us.forEach((u,i)=>{
    const tr=document.createElement('tr');
    const td=()=>tr.appendChild(document.createElement('td'));
    const c1=td();
    c1.appendChild(document.createTextNode(u.nombre||''));
    c1.appendChild(document.createElement('br'));
    const sm=document.createElement('span');sm.style.cssText='color:var(--txt2);font-size:11px';
    sm.textContent=u.email;c1.appendChild(sm);
    if(u.es_admin)c1.appendChild(document.createTextNode(' 👑'));
    const sel=document.createElement('select');sel.className='min';
    Object.keys(PLANES).forEach(k=>{const o=document.createElement('option');o.value=k;
      o.textContent=PLANES[k].nombre;if(u.plan===k)o.selected=true;sel.appendChild(o)});
    td().appendChild(sel);
    td().textContent=u.usadas+'/'+u.limite;
    const pill=document.createElement('span');pill.className='pill '+(u.activo?'on-p':'off-p');
    pill.textContent=u.activo?'Activo':'Inactivo';td().appendChild(pill);
    const acc=td();
    const boton=(txt,sec,fn)=>{const b=document.createElement('button');b.className='bx';
      if(sec)b.style.cssText='background:var(--azul3);color:var(--txt)';b.textContent=txt;
      b.addEventListener('click',fn);acc.appendChild(b);acc.appendChild(document.createTextNode(' '))};
    boton('Activar',false,()=>guardar(u.email,sel.value,true));
    boton('Desactivar',true,()=>guardar(u.email,sel.value,false));
    boton('Reiniciar uso',true,()=>guardar(u.email,sel.value,null,true));
    boton('🔑 Clave',true,()=>resetClave(u.email));
    tb.appendChild(tr);
  });
}
async function cargarNegocio(){
  try{
    const m=await(await fetch('/api/admin/metricas',{headers:{'Authorization':'Bearer '+TOKEN}})).json();
    const cop=n=>'$'+Number(n||0).toLocaleString('es-CO');
    $('negocio').innerHTML=`
      <div class="stat"><div class="n" style="color:var(--ok)">${cop(m.ingreso_mensual_estimado)}</div><div class="l">Ingreso mensual estimado</div></div>
      <div class="stat"><div class="n" style="color:#ff9f43">${cop(m.costo_api_estimado)}</div><div class="l">Costo API estimado</div></div>
      <div class="stat"><div class="n">${cop(m.margen_estimado)}</div><div class="l">Margen estimado</div></div>
      <div class="stat"><div class="n">${m.consultas_totales}</div><div class="l">Consultas usadas</div></div>`;
  }catch(e){$('negocio').innerHTML=''}
}
async function resetClave(email){
  if(!confirm('¿Generar una contraseña temporal para '+email+'?'))return;
  const r=await fetch('/api/admin/reset-clave',{method:'POST',
    headers:{'Authorization':'Bearer '+TOKEN,'content-type':'application/json'},body:JSON.stringify({email})});
  const d=await r.json();
  if(r.ok)prompt('Entrégale esta contraseña temporal al estudiante (la cambia al entrar):',d.temporal);
  else alert('No se pudo');
}
async function guardar(email,plan,activo,reiniciar){
  const body={email,plan};
  if(activo!==null&&activo!==undefined)body.activo=activo;
  if(reiniciar)body.reiniciar=true;
  const r=await fetch('/api/admin/actualizar',{method:'POST',
    headers:{'Authorization':'Bearer '+TOKEN,'content-type':'application/json'},body:JSON.stringify(body)});
  if(r.ok)cargar();else alert('No se pudo actualizar');
}
async function regenBoletin(){
  await fetch('/api/admin/boletin/regenerar',{method:'POST',headers:{'Authorization':'Bearer '+TOKEN}});
  alert('Boletín regenerado');
}

// ---------------------------------------------------------------------------------------
// Despachador de eventos (Fase 1b de seguridad). Los botones declaran data-click="funcion"
// en vez de onclick="...": así la política de seguridad (CSP) puede prohibir todo JavaScript
// en línea. Solo se ejecutan funciones de esta lista blanca.
const ACCIONES={cargar,entrar,regenBoletin};
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
['click','change','input','keydown'].forEach(t=>document.addEventListener(t,ev=>despachar(t,ev)));

