// =========================================================================================
// PULLEX IA — motor de apariencia. Se carga en <head>, ANTES de pintar, para que la página
// aparezca ya con el tema del usuario (sin parpadeo): lee la última apariencia guardada en este
// navegador (localStorage) y pone los atributos data-* en <html>. Después de ingresar, app.js
// llama a PXA.aplicar() con la apariencia guardada en la cuenta (la fuente de verdad).
// Sin dependencias; todo con try/catch (modo privado, almacenamiento bloqueado, etc.).
// =========================================================================================
(function(){
'use strict';
var OPC={modo:['claro','oscuro','auto'],tema:['justicia','pullex','notario','bogota','caribe','toga','jardin'],
  fuente:['syne','editorial','clasica','moderna'],tamano:['normal','grande'],densidad:['comoda','compacta'],
  radio:['recto','suave','redondo']};
// Por defecto: tema «Justicia × Inteligencia» en oscuro, con Syne + Plus Jakarta Sans (octubre de 2026).
var DEFECTO={modo:'oscuro',tema:'justicia',acento:null,fuente:'syne',tamano:'normal',densidad:'comoda',radio:'suave'};
// Lo que era el valor por defecto hasta octubre de 2026. Quien lo tenga guardado tal cual nunca eligió otra
// apariencia: pasa al tema nuevo. Quien cambió cualquier opción conserva la suya (mismo criterio en app.py).
var ANTERIOR={modo:'claro',tema:'pullex',acento:null,fuente:'editorial',tamano:'normal',densidad:'comoda',radio:'suave'};
var CLAVE='pullex.apariencia.v2', CLAVE_V1='pullex.apariencia.v1';
var RE_COLOR=/^#[0-9a-f]{6}$/i;
var raiz=document.documentElement;
var actual=null, oyente=null;

function normalizar(a){
  var o={},k;a=a&&typeof a==='object'?a:{};
  for(k in OPC)o[k]=OPC[k].indexOf(a[k])>=0?a[k]:DEFECTO[k];
  o.acento=typeof a.acento==='string'&&RE_COLOR.test(a.acento)?a.acento.toLowerCase():null;
  return o;
}

// ---- color (WCAG 2.x) ----------------------------------------------------------------
function rgb(h){h=String(h).trim();if(h[0]!=='#'||h.length!==7)return null;
  return [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)]}
function hex(c){return '#'+c.map(function(x){x=Math.max(0,Math.min(255,Math.round(x)));return (x<16?'0':'')+x.toString(16)}).join('')}
function lum(h){var c=rgb(h).map(function(x){x/=255;return x<=0.03928?x/12.92:Math.pow((x+0.055)/1.055,2.4)});
  return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]}
function contraste(a,b){var x=lum(a),y=lum(b);return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05)}
function mezclar(a,b,t){var x=rgb(a),y=rgb(b);return hex([0,1,2].map(function(i){return x[i]+(y[i]-x[i])*t}))}
// Lleva el color hacia blanco o negro, en pasos, hasta cumplir el contraste pedido contra cada fondo.
function asegurar(c,fondos,minimo,hacia){
  for(var i=0;i<40;i++){
    var ok=fondos.every(function(f){return contraste(c,f)>=minimo});
    if(ok)return c;c=mezclar(c,hacia,0.06);
  }
  return c;
}
// A partir de un acento libre calcula --accent, --accent-ink, --accent-soft y --accent-text
// garantizando AA: texto sobre el botón ≥ 4,5; acento como texto ≥ 4,5 sobre fondo, superficie
// y acento suave; y el botón se distingue del fondo (≥ 3 en oscuro, donde un acento oscuro se perdería).
function derivar(acento,oscuro,bg,surface){
  var a=acento,blanco='#ffffff',negro='#14120f';
  if(oscuro)a=asegurar(a,[bg],3,blanco);
  var ink=contraste(blanco,a)>=contraste(negro,a)?blanco:negro;
  a=asegurar(a,[ink],4.5,ink===blanco?negro:blanco);
  var soft=mezclar(surface,a,oscuro?0.2:0.12);
  var texto=asegurar(a,[surface,bg,soft],4.5,oscuro?blanco:negro);
  return {accent:a,ink:ink,soft:soft,texto:texto};
}

function esquemaDe(modo){
  if(modo==='auto'){try{return window.matchMedia('(prefers-color-scheme: dark)').matches?'oscuro':'claro'}catch(e){return 'claro'}}
  return modo==='oscuro'?'oscuro':'claro';
}
function leerToken(n){return getComputedStyle(raiz).getPropertyValue(n).trim()}
var VARS_ACENTO=['--accent','--accent-ink','--accent-soft','--accent-text'];

function aplicar(a){
  a=normalizar(a);actual=a;
  var esq=esquemaDe(a.modo);
  raiz.setAttribute('data-tema',a.tema);raiz.setAttribute('data-esquema',esq);
  raiz.setAttribute('data-fuente',a.fuente);raiz.setAttribute('data-tamano',a.tamano);
  raiz.setAttribute('data-densidad',a.densidad);raiz.setAttribute('data-radio',a.radio);
  VARS_ACENTO.forEach(function(v){raiz.style.removeProperty(v)});
  if(a.acento){
    var bg=leerToken('--bg')||'#101115',sf=leerToken('--surface')||'#17191e';
    if(rgb(bg)&&rgb(sf)){var d=derivar(a.acento,esq==='oscuro',bg,sf);
      raiz.style.setProperty('--accent',d.accent);raiz.style.setProperty('--accent-ink',d.ink);
      raiz.style.setProperty('--accent-soft',d.soft);raiz.style.setProperty('--accent-text',d.texto);}
  }
  // Compatibilidad: código viejo (y pruebas) miran body.claro / body.oscuro.
  if(document.body){document.body.classList.toggle('claro',esq==='claro');document.body.classList.toggle('oscuro',esq==='oscuro')}
  var meta=document.querySelector('meta[name=theme-color]');
  if(meta){var c=leerToken('--bg');if(c)meta.setAttribute('content',c)}
  // "Automático" sigue al sistema también si cambia con la página abierta.
  try{
    var mq=window.matchMedia('(prefers-color-scheme: dark)');
    if(a.modo==='auto'&&!oyente){oyente=function(){if(actual&&actual.modo==='auto')aplicar(actual)};
      mq.addEventListener?mq.addEventListener('change',oyente):mq.addListener(oyente)}
  }catch(e){}
  return a;
}
function esAnterior(a){for(var k in ANTERIOR)if(a[k]!==ANTERIOR[k])return false;return true}
function leerLocal(){
  try{var t=localStorage.getItem(CLAVE);if(t)return normalizar(JSON.parse(t));
    // Navegador que guardó su apariencia con la versión anterior: se conserva solo si era una elección propia.
    var v=localStorage.getItem(CLAVE_V1);if(!v)return null;
    var crudo=JSON.parse(v),a=normalizar(crudo),k;
    for(k in ANTERIOR)if(k!=='acento'&&OPC[k].indexOf(crudo&&crudo[k])<0)a[k]=ANTERIOR[k];
    return esAnterior(a)?null:a;
  }catch(e){return null}}
function guardarLocal(a){try{localStorage.setItem(CLAVE,JSON.stringify(normalizar(a)))}catch(e){}}
function borrarLocal(){try{localStorage.removeItem(CLAVE);localStorage.removeItem(CLAVE_V1)}catch(e){}}

window.PXA={OPC:OPC,DEFECTO:DEFECTO,normalizar:normalizar,aplicar:aplicar,leerLocal:leerLocal,guardarLocal:guardarLocal,
  borrarLocal:borrarLocal,derivar:derivar,contraste:contraste,actual:function(){return actual||normalizar(DEFECTO)}};
aplicar(leerLocal()||DEFECTO);
// body todavía no existe en <head>: sincroniza las clases de compatibilidad apenas exista.
if(!document.body)document.addEventListener('DOMContentLoaded',function(){aplicar(actual)});
})();
