// =========================================================================================
// PULLEX IA — movimiento. Complemento de static/movimiento.css; se carga ANTES de app.js.
//
// Qué hace este archivo (y solo esto):
//   · Portada: parte el titular en palabras, mide en qué línea cayó cada una y deja que el CSS lo descubra por
//     líneas; hace que las cuatro características esperen a entrar en pantalla (IntersectionObserver).
//   · Retrato de la Justicia: paralaje mínimo con el puntero (solo ratón), escrito en --px / --py.
//   · Tarjetas: posición del puntero en --mx / --my para el borde de luz (solo ratón).
//   · Barra lateral: crea el indicador activo y lo coloca sobre el destino actual.
//   · Cambio de sección: View Transitions API si existe (MV.transicion); si no, el cambio es directo.
//   · Cifras de progreso: MV.contar() las lleva hasta su valor REAL; el valor final siempre es el que dio el servidor.
//     El saldo de consultas de la cabecera no rueda: siempre muestra el número real y solo da un salto al cambiar.
//   · Consultar: marca la escena de entrada como vista para que no se repita en cada visita.
//
// Qué NO hace: no inventa estados. «Esperando», «consultando fuentes» y «escribiendo» los pone app.js con los
// eventos reales del envío y del stream (data-trabajo en <html>); aquí no hay temporizadores que finjan trabajo.
//
// Si este archivo no carga, la app funciona igual: nada queda oculto esperando a JavaScript (los estados de
// partida viven dentro de las animaciones CSS) y app.js comprueba window.MV antes de usarlo.
// Sin dependencias y sin JavaScript en línea (CSP). Todo con try/catch donde un navegador viejo podría fallar.
// =========================================================================================
(function(){
'use strict';
var raiz=document.documentElement;
function mq(q){try{return window.matchMedia(q)}catch(e){return null}}
var mqMenos=mq('(prefers-reduced-motion: reduce)'),mqRaton=mq('(hover:hover) and (pointer:fine)'),mqLateral=mq('(min-width:1040px)');
// Movimiento reducido = lo pide el sistema O lo eligió la persona en Ajustes → Apariencia.
function reducido(){return !!(mqMenos&&mqMenos.matches)||raiz.getAttribute('data-movimiento')==='reducido'}
function alCuadro(fn){return (window.requestAnimationFrame||function(f){return setTimeout(f,16)})(fn)}

// ----------------------------------------------------------------- titular por líneas --
// Envuelve cada palabra en <span class="pal"> sin tocar el texto (los lectores de pantalla leen lo mismo).
function partir(el){
  var pals=[];
  (function andar(nodo){
    Array.prototype.slice.call(nodo.childNodes).forEach(function(h){
      if(h.nodeType===1){andar(h);return}
      if(h.nodeType!==3||!h.nodeValue.trim())return;
      var frag=document.createDocumentFragment();
      h.nodeValue.split(/(\s+)/).forEach(function(t){
        if(!t)return;
        if(/^\s+$/.test(t)){frag.appendChild(document.createTextNode(' '));return}
        var s=document.createElement('span');s.className='pal';s.textContent=t;frag.appendChild(s);pals.push(s)});
      nodo.replaceChild(frag,h);
    });
  })(el);
  // Un signo pegado a un elemento («<em>más criterio</em>.») no debe poder saltar solo a otra línea.
  pals.forEach(function(p){var a=p.previousSibling;
    if(a&&a.nodeType===1&&!a.classList.contains('pal')){var w=document.createElement('span');w.style.whiteSpace='nowrap';
      a.parentNode.insertBefore(w,a);w.appendChild(a);w.appendChild(p)}});
  return pals;
}
function numerarLineas(pals){
  var tops=[];
  pals.forEach(function(p){var t=Math.round(p.getBoundingClientRect().top);p.__t=t;if(tops.indexOf(t)<0)tops.push(t)});
  tops.sort(function(a,b){return a-b});
  pals.forEach(function(p){p.style.setProperty('--l',tops.indexOf(p.__t))});
  return tops.length;
}
function porLineas(el){
  if(!el||el.classList.contains('mv-lineas')||reducido())return;
  el.classList.add('mv-prep');                      // oculto un instante (con salvavidas en CSS) mientras llega la fuente
  var hecho=false;
  function hacer(){if(hecho)return;hecho=true;
    try{numerarLineas(partir(el))}catch(e){}
    el.classList.remove('mv-prep');el.classList.add('mv-lineas')}
  var tope=setTimeout(hacer,180);
  try{var familia=getComputedStyle(el).fontFamily.split(',')[0];
    document.fonts.load('600 32px '+familia).then(function(){clearTimeout(tope);alCuadro(hacer)},hacer)}
  catch(e){clearTimeout(tope);hacer()}
}

// ------------------------------------------------------------------------- portada --
function portada(){
  var auth=document.getElementById('auth');if(!auth||reducido())return;
  porLineas(auth.querySelector('.auth-intro h1'));
  var items=auth.querySelectorAll('.auth-ben li');
  if(!items.length||!('IntersectionObserver' in window))return;
  var t0=Date.now();
  var io=new IntersectionObserver(function(entradas){
    var k=0,base=Date.now()-t0<500?5:0;             // las que ya se ven al cargar esperan a que termine el titular
    entradas.forEach(function(e){if(!e.isIntersecting)return;var li=e.target;
      li.style.setProperty('--i',base+k++);li.classList.remove('mv-espera');li.classList.add('mv-entro');io.unobserve(li)});
  },{threshold:.1});
  Array.prototype.forEach.call(items,function(li){li.classList.add('mv-espera');io.observe(li)});
}

// ------------------------------------------------------------ paralaje del retrato --
function paralaje(){
  if(!mqRaton||!mqRaton.matches)return;
  [['auth','.auth-retrato'],['chat-lay','.retrato-chat']].forEach(function(par){
    var zona=document.getElementById(par[0]),r=zona&&zona.querySelector(par[1]);if(!r)return;
    var pend=false,x=0,y=0;
    function soltar(){r.style.setProperty('--px','0');r.style.setProperty('--py','0')}
    zona.addEventListener('pointermove',function(ev){
      if(ev.pointerType&&ev.pointerType!=='mouse')return;
      if(reducido()){if(r.classList.contains('mv-par')){r.classList.remove('mv-par');soltar()}return}
      x=ev.clientX;y=ev.clientY;if(pend)return;pend=true;
      alCuadro(function(){pend=false;
        var c=r.getBoundingClientRect();if(!c.width)return;                    // retrato oculto (franja o conversación abierta)
        var px=Math.max(-1,Math.min(1,(x-(c.left+c.width/2))/(window.innerWidth/2)));
        var py=Math.max(-1,Math.min(1,(y-(c.top+c.height/2))/(window.innerHeight/2)));
        if(!r.classList.contains('mv-par'))r.classList.add('mv-par');
        r.style.setProperty('--px',px.toFixed(3));r.style.setProperty('--py',py.toFixed(3))});
    },{passive:true});
    zona.addEventListener('pointerleave',soltar);
  });
}

// ----------------------------------------------------- borde de luz de las tarjetas --
function luzTarjetas(){
  if(!mqRaton||!mqRaton.matches)return;
  raiz.classList.add('mv-puntero');
  var pend=false,ult=null;
  document.addEventListener('pointermove',function(ev){
    ult=ev;if(pend)return;pend=true;
    alCuadro(function(){pend=false;
      var t=ult.target&&ult.target.closest&&ult.target.closest('.sugs button,.captarj,.tcard');if(!t)return;
      var c=t.getBoundingClientRect();
      t.style.setProperty('--mx',Math.round(ult.clientX-c.left)+'px');t.style.setProperty('--my',Math.round(ult.clientY-c.top)+'px')});
  },{passive:true});
}

// --------------------------------------------------- indicador de la barra lateral --
function indicador(){
  var nav=document.querySelector('#app nav'),app=document.getElementById('app');
  if(!nav||!app||!('MutationObserver' in window))return;
  var ind=document.createElement('span');ind.className='nav-ind oculto';ind.setAttribute('aria-hidden','true');
  nav.insertBefore(ind,nav.firstChild);nav.classList.add('mv-nav');
  function colocar(){
    if(mqLateral&&!mqLateral.matches)return;
    var b=nav.querySelector('button.on:not(#n-mas)');
    if(!b||b.offsetParent===null){if(!ind.classList.contains('oculto'))ind.classList.add('oculto');return}
    ind.style.setProperty('--ind-y',b.offsetTop+'px');
    if(ind.classList.contains('oculto'))ind.classList.remove('oculto');
    // La primera colocación no se anima: la transición se habilita dos cuadros después.
    if(!nav.classList.contains('mv-listo'))alCuadro(function(){alCuadro(function(){nav.classList.add('mv-listo')})});
  }
  var obs=new MutationObserver(function(rs){for(var i=0;i<rs.length;i++){var t=rs[i].target;if(t!==ind&&t!==nav){colocar();return}}});
  obs.observe(nav,{attributes:true,attributeFilter:['class'],subtree:true});
  obs.observe(app,{attributes:true,attributeFilter:['class']});
  if(mqLateral){var f=function(){colocar()};mqLateral.addEventListener?mqLateral.addEventListener('change',f):mqLateral.addListener(f)}
  // «Ajustes» va pegado al pie de la barra: si cambia el alto de la ventana, cambia su sitio.
  var pend=false;window.addEventListener('resize',function(){if(pend)return;pend=true;alCuadro(function(){pend=false;colocar()})});
  colocar();
}

// -------------------------------------------------------- transición entre secciones --
var vtEnCurso=false;
function transicion(cambiar){
  if(vtEnCurso||reducido()||typeof document.startViewTransition!=='function'){cambiar();return}
  var hecho=false;function uno(){if(!hecho){hecho=true;cambiar()}}
  function fin(){vtEnCurso=false;raiz.classList.remove('mv-vt')}
  raiz.classList.add('mv-vt');vtEnCurso=true;
  try{var t=document.startViewTransition(uno);t.finished.then(fin,fin);if(t.ready&&t.ready.catch)t.ready.catch(function(){})}
  catch(e){fin();uno()}
}

// ---------------------------------------------------------------------------- cifras --
// Lleva el número visible de «el» hasta «n» (el valor real). opc: {desde, sufijo}. Si el elemento no está a la
// vista, conserva el valor real y cuenta cuando entra. Con movimiento reducido escribe el valor y termina.
var cuentas=typeof WeakMap==='function'?new WeakMap():null;
function escribir(el,v,suf){var t=String(v)+(suf||'');var st=cuentas&&cuentas.get(el);if(st)st.escrito=t;el.textContent=t}
function contar(el,n,opc){
  opc=opc||{};var suf=opc.sufijo||'';n=Number(n);
  if(!el)return;
  var st=cuentas&&cuentas.get(el);if(st&&st.raf)(window.cancelAnimationFrame||clearTimeout)(st.raf);
  st={real:n,escrito:null,raf:0};if(cuentas)cuentas.set(el,st);
  var desde=typeof opc.desde==='number'?opc.desde:0;
  if(!cuentas||reducido()||!isFinite(n)||n===desde||n!==Math.round(n)){escribir(el,isFinite(n)?n:'—',suf);return}
  function animar(){
    var dur=Math.max(420,Math.min(900,360+Math.abs(n-desde)*9)),t0=null;
    escribir(el,desde,suf);
    (function paso(){st.raf=alCuadro(function(t){
      if(cuentas.get(el)!==st)return;                                         // llegó un valor más nuevo
      if(t0===null)t0=t;var p=Math.min(1,(t-t0)/dur),e=1-Math.pow(1-p,3);     // frena al llegar
      escribir(el,Math.round(desde+(n-desde)*e),suf);
      if(p<1)paso();else st.raf=0})})();
  }
  var c=el.getBoundingClientRect(),alaVista=c.width>0&&c.bottom>0&&c.top<(window.innerHeight||0);
  if(alaVista||!('IntersectionObserver' in window)){animar();return}
  escribir(el,n,suf);
  var io=new IntersectionObserver(function(es){if(es.some(function(e){return e.isIntersecting})){io.disconnect();if(cuentas.get(el)===st)animar()}});
  io.observe(el);
}
// Contador de consultas de la cabecera: el número SIEMPRE es el real (es el saldo del plan); cuando cambia, da un
// pequeño salto para que se note que se gastó una consulta. No se hace rodar la cifra: mostraría valores intermedios.
function vigilarConsultas(){
  var el=document.getElementById('c-rest');if(!el||!('MutationObserver' in window))return;
  var antes=null;
  new MutationObserver(function(){
    var txt=el.textContent.trim();if(txt===antes)return;
    var primera=antes===null||!/^\d+$/.test(antes);antes=txt;
    if(primera||!/^\d+$/.test(txt)||reducido())return;                          // al ingresar no hay nada que señalar
    el.classList.remove('mv-tic');void el.offsetWidth;el.classList.add('mv-tic');
  }).observe(el,{childList:true,characterData:true,subtree:true});
}

// ------------------------------------------- Consultar: la escena se ve una sola vez --
function escenaConsultar(){
  var lay=document.getElementById('chat-lay'),vista=document.getElementById('v-chat'),sugs=document.getElementById('sugs');
  if(!lay||!vista||!sugs||!('MutationObserver' in window))return;
  var obs,temporizador=0;
  function revisar(){
    if(temporizador||sugs.offsetParent===null)return;                          // aún no se ve el estado inicial
    temporizador=setTimeout(function(){lay.classList.add('mv-visto');if(obs)obs.disconnect()},1500);
  }
  obs=new MutationObserver(revisar);
  obs.observe(vista,{attributes:true,attributeFilter:['class']});
  obs.observe(sugs,{attributes:true,attributeFilter:['class']});
  var app=document.getElementById('app');if(app)obs.observe(app,{attributes:true,attributeFilter:['class']});
  revisar();
}

window.MV={reducido:reducido,transicion:transicion,contar:contar,porLineas:porLineas};
function arrancar(fn){try{fn()}catch(e){}}
[portada,paralaje,luzTarjetas,indicador,vigilarConsultas,escenaConsultar].forEach(arrancar);
})();
