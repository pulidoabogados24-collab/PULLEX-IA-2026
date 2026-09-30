const params = new URLSearchParams(location.search);
const token = params.get('token') || '';
const $ = id => document.getElementById(id);

if (!token) {
  $('titulo').textContent = 'Enlace incompleto';
  $('desc').textContent = 'Este enlace no trae la información necesaria. Pide uno nuevo desde la app.';
  $('formulario').style.display = 'none';
}

async function enviar(){
  const c1 = $('clave1').value, c2 = $('clave2').value;
  $('msg').className = 'msg';
  if (c1.length < 8) { $('msg').className='msg err'; $('msg').textContent='Mínimo 8 caracteres.'; return; }
  if (c1 !== c2) { $('msg').className='msg err'; $('msg').textContent='Las contraseñas no coinciden.'; return; }
  $('btn').disabled = true; $('btn').textContent = 'Guardando…';
  try{
    const r = await fetch('/api/restablecer-clave', {
      method:'POST', headers:{'content-type':'application/json'},
      body: JSON.stringify({token, clave: c1})
    });
    const d = await r.json().catch(()=>({}));
    if (!r.ok) {
      $('msg').className='msg err'; $('msg').textContent = d.detail || 'No se pudo actualizar.';
      $('btn').disabled = false; $('btn').textContent = 'Guardar nueva contraseña';
      return;
    }
    $('titulo').textContent = 'Contraseña actualizada';
    $('desc').textContent = 'Ya puedes iniciar sesión con tu nueva contraseña.';
    $('formulario').style.display = 'none';
  }catch(e){
    $('msg').className='msg err'; $('msg').textContent = 'Error de conexión. Intenta de nuevo.';
    $('btn').disabled = false; $('btn').textContent = 'Guardar nueva contraseña';
  }
}

// ---------------------------------------------------------------------------------------
// Despachador de eventos (Fase 1b de seguridad). Los botones declaran data-click="funcion"
// en vez de onclick="...": así la política de seguridad (CSP) puede prohibir todo JavaScript
// en línea. Solo se ejecutan funciones de esta lista blanca.
const ACCIONES={enviar};
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

