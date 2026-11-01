import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, BookOpen, CheckCircle2, ClipboardList, Copy,
  Download, FileText, FolderOpen, Menu, Mic, MicOff, Pause, Play,
  Plus, Scale, ShieldCheck, XCircle
} from "lucide-react";
import { compareStatement, DEMO_SOURCES, DEMO_TURNS } from "./engine";
import type { FindingResult, Review, SourceFragment } from "./engine";

type View = "audiencia" | "expedientes" | "biblioteca" | "declarantes" | "hallazgos" | "preguntas" | "informes" | "arquitectura";
type CaseFile = { id:string; title:string; radicado:string; delito:string; isDemo:boolean };
type Turn = { id:string; caseId:string; speaker:string; text:string; at:string; origin:"manual"|"simulacion"|"microfono" };
type Finding = FindingResult & { id:string; caseId:string; turnId:string; at:string; review:Review };
type SavedQuestion = { id:string; caseId:string; findingId:string; text:string; at:string };
type SavedData = { cases:CaseFile[]; sources:SourceFragment[]; turns:Turn[]; findings:Finding[]; questions:SavedQuestion[] };
type Recognition = { lang:string; continuous:boolean; interimResults:boolean; onresult:((event:any)=>void)|null; onerror:((event:any)=>void)|null; onend:(()=>void)|null; start:()=>void; stop:()=>void };
type RecognitionConstructor = new ()=>Recognition;
const STORAGE_KEY="pullex-audiencia-live-v1";
const DEMO_CASE:CaseFile={id:"demo",title:"Simulación Boris",radicado:"FICTICIO-2026-0001",delito:"Hurto calificado y agravado",isDemo:true};
const initialData:SavedData={cases:[DEMO_CASE],sources:DEMO_SOURCES,turns:[],findings:[],questions:[]};
const names:Record<View,string>={audiencia:"Audiencia Live",expedientes:"Expedientes",biblioteca:"Biblioteca",declarantes:"Declarantes",hallazgos:"Hallazgos",preguntas:"Preguntas",informes:"Informes",arquitectura:"Arquitectura"};
const navItems:View[]=["audiencia","expedientes","biblioteca","declarantes","hallazgos","preguntas","informes","arquitectura"];
const labels:Record<FindingResult["category"],string>={
  "possible-contradiction":"Posible contradicción",coincides:"Coincide",
  expansion:"Ampliación de versión","not-found":"No consta",inconclusive:"No concluyente"
};
const uid=()=>Math.random().toString(36).slice(2)+Date.now().toString(36);
function safeLoad():SavedData{
  try {
    const raw=localStorage.getItem(STORAGE_KEY);
    if(!raw) return initialData;
    const p=JSON.parse(raw) as SavedData;
    return Array.isArray(p.cases)&&Array.isArray(p.sources)&&Array.isArray(p.turns)&&Array.isArray(p.findings)&&Array.isArray(p.questions) ? p : initialData;
  }catch{return initialData;}
}
function exportFile(name:string, content:string, mime="application/json"){
  const blob=new Blob([content],{type:mime});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download=name;a.click();
  window.setTimeout(()=>URL.revokeObjectURL(url),1000);
}
const timestamp=()=>new Date().toLocaleTimeString("es-CO",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
function TypePill({category}:{category:FindingResult["category"]}){
  return <span className={"type-pill "+category}>{category==="possible-contradiction"?<AlertTriangle size={13}/>:category==="coincides"?<CheckCircle2 size={13}/>:<Activity size={13}/>} {labels[category]}</span>;
}
export default function App(){
  const [data,setData]=useState<SavedData>(safeLoad);
  const [activeId,setActiveId]=useState("demo");
  const [view,setView]=useState<View>("audiencia");
  const [filter,setFilter]=useState("all");
  const [selectedId,setSelectedId]=useState<string|null>(null);
  const [speaker,setSpeaker]=useState("Boris");
  const [input,setInput]=useState("");
  const [newQuote,setNewQuote]=useState("");
  const [newSource,setNewSource]=useState("Declaración cargada manualmente");
  const [newDeclarant,setNewDeclarant]=useState("Boris");
  const [questionDraft,setQuestionDraft]=useState("");
  const [message,setMessage]=useState("");
  const [demoRunning,setDemoRunning]=useState(false);
  const [micOn,setMicOn]=useState(false);
  const [interim,setInterim]=useState("");
  const timer=useRef<number|null>(null);
  const recognition=useRef<Recognition|null>(null);
  useEffect(()=>{try{localStorage.setItem(STORAGE_KEY,JSON.stringify(data));}catch{setMessage("No hay espacio disponible para guardar en este navegador.");}},[data]);
  useEffect(()=>()=>{if(timer.current!==null)window.clearInterval(timer.current);recognition.current?.stop();},[]);
  const activeCase=data.cases.find(c=>c.id===activeId)??DEMO_CASE;
  const docs=useMemo(()=>data.sources.filter(s=>s.caseId===activeId),[data.sources,activeId]);
  const turns=useMemo(()=>data.turns.filter(t=>t.caseId===activeId),[data.turns,activeId]);
  const findings=useMemo(()=>data.findings.filter(f=>f.caseId===activeId).slice().reverse(),[data.findings,activeId]);
  const filtered=findings.filter(f=>filter==="all"||f.category===filter);
  const selected=findings.find(f=>f.id===selectedId)??findings[0]??null;
  const questions=data.questions.filter(q=>q.caseId===activeId);
  useEffect(()=>setQuestionDraft(selected?.suggestedQuestion??""),[selected?.id]);
  const addTurn=(text:string,who=speaker,caseId=activeId,origin:Turn["origin"]="manual")=>{
    const content=text.trim();if(!content)return;
    const t:Turn={id:uid(),caseId,speaker:who,text:content,at:timestamp(),origin};
    const fragment=who==="Defensor"||who==="Juez"||who==="Fiscal"?null:compareStatement(content,who,caseId,data.sources);
    setData(prev=>({
      ...prev,turns:[...prev.turns,t],
      findings:fragment?[...prev.findings,{...fragment,id:uid(),caseId,turnId:t.id,at:t.at,review:"pending"}]:prev.findings,
    }));
  };
  const startDemo=()=>{
    if(timer.current!==null)window.clearInterval(timer.current);
    stopMic();setActiveId("demo");setView("audiencia");setSelectedId(null);setDemoRunning(true);setFilter("all");
    setData(prev=>({...prev,turns:prev.turns.filter(t=>t.caseId!=="demo"),findings:prev.findings.filter(f=>f.caseId!=="demo")}));
    let i=0;
    timer.current=window.setInterval(()=>{
      if(i>=DEMO_TURNS.length){if(timer.current!==null)window.clearInterval(timer.current);timer.current=null;setDemoRunning(false);return;}
      const turn=DEMO_TURNS[i++];
      const id=uid(),at=timestamp();
      setData(prev=>{
        const found=turn.speaker==="Defensor"?null:compareStatement(turn.text,turn.speaker,"demo",prev.sources);
        const next:Turn={id,caseId:"demo",speaker:turn.speaker,text:turn.text,at,origin:"simulacion"};
        return {...prev,turns:[...prev.turns,next],findings:found?[...prev.findings,{...found,id:uid(),caseId:"demo",turnId:id,at,review:"pending"}]:prev.findings};
      });
    },1350);
  };
  const stopDemo=()=>{if(timer.current!==null)window.clearInterval(timer.current);timer.current=null;setDemoRunning(false);};
  const stopMic=()=>{recognition.current?.stop();recognition.current=null;setMicOn(false);setInterim("");};
  const startMic=()=>{
    if(micOn){stopMic();return;}
    const vendor=window as unknown as {SpeechRecognition?:RecognitionConstructor;webkitSpeechRecognition?:RecognitionConstructor};
    const Speech=vendor.SpeechRecognition??vendor.webkitSpeechRecognition;
    if(!Speech){setMessage("Este navegador no ofrece reconocimiento de voz compatible. Puede pegar o escribir la declaración.");return;}
    if(!window.confirm("¿Confirmas que estás autorizado para procesar este audio? El reconocimiento del navegador podría usar servicios de terceros. No uses expedientes reales en este MVP."))return;
    try{
      const rec=new Speech();rec.lang="es-CO";rec.continuous=true;rec.interimResults=true;
      rec.onresult=(event:any)=>{
        let partial="";
        for(let j=event.resultIndex;j<event.results.length;j++){
          const s=event.results[j][0].transcript as string;
          if(event.results[j].isFinal)addTurn(s,speaker,activeId,"microfono");else partial+=s+" ";
        }
        setInterim(partial);
      };
      rec.onerror=(e:any)=>{setMessage("Micrófono: "+String(e.error??"error")+"; revisa permisos y compatibilidad.");stopMic();};
      rec.onend=()=>{setMicOn(false);setInterim("");recognition.current=null;};
      rec.start();recognition.current=rec;setMicOn(true);setMessage("Micrófono activo. Selecciona el declarante correcto; la identificación NO es automática.");
    }catch{setMessage("No fue posible iniciar el reconocimiento de voz.");}
  };
  const createCase=()=>{
    const name=window.prompt("Nombre del nuevo expediente (sin información reservada):","Nuevo expediente ficticio");
    if(!name?.trim())return;
    const id=uid();setData(prev=>({...prev,cases:[...prev.cases,{id,title:name.trim(),radicado:"SIN RADICADO",delito:"Por definir",isDemo:false}]}));
    setActiveId(id);setView("audiencia");setMessage("Expediente local creado. Este MVP no es seguro para datos judiciales reservados.");
  };
  const addSource=()=>{
    const chunks=newQuote.split(/\n+/).map(s=>s.trim()).filter(Boolean);
    if(!chunks.length){setMessage("Escribe una declaración antes de guardarla.");return;}
    const parsed=chunks.map((quote,i):SourceFragment=>({id:uid(),caseId:activeId,declarant:newDeclarant.trim()||"Sin identificar",quote,source:newSource.trim()||"Texto manual",location:"Fragmento "+(i+1)}));
    setData(prev=>({...prev,sources:[...prev.sources,...parsed]}));setNewQuote("");setMessage("Se agregaron "+parsed.length+" fragmentos al expediente local.");
  };
  const addFile=async(file?:File)=>{
    if(!file)return;
    if(!/\.txt$/i.test(file.name)){setMessage("Esta versión solo lee TXT. Para PDF o DOCX se requiere implementar un extractor verificable.");return;}
    if(file.size>750000){setMessage("Límite de esta versión: 750 KB por documento TXT.");return;}
    const text=await file.text();const chunks=text.split(/\n+/).map(x=>x.trim()).filter(Boolean);
    if(!chunks.length){setMessage("El TXT no contiene texto legible.");return;}
    const newItems:SourceFragment[]=chunks.map((quote,i)=>({id:uid(),caseId:activeId,declarant:newDeclarant||"Sin identificar",quote,source:file.name,location:"Línea "+(i+1)}));
    setData(prev=>({...prev,sources:[...prev.sources,...newItems]}));
    setMessage("Documento TXT indexado: "+chunks.length+" líneas.");
  };
  const review=(status:Review)=>{if(!selected)return;setData(prev=>({...prev,findings:prev.findings.map(f=>f.id===selected.id?{...f,review:status}:f)}));};
  const saveQuestion=()=>{
    if(!selected||!questionDraft.trim())return;
    setData(prev=>({...prev,questions:[...prev.questions,{id:uid(),caseId:activeId,findingId:selected.id,text:questionDraft.trim(),at:timestamp()}]}));
    setMessage("Pregunta guardada en el expediente.");
  };
  const exportReport=()=>{
    const report={notice:"Motor local experimental. Hallazgos pendientes de revisión jurídica.",case:activeCase,sources:docs,turns,findings,questions,exportedAt:new Date().toISOString()};
    exportFile("PULLEX_Audiencia_"+activeId+".json",JSON.stringify(report,null,2));
  };
  const navIcon=(v:View)=>{
    const icons={audiencia:<Activity size={17}/>,expedientes:<FolderOpen size={17}/>,biblioteca:<BookOpen size={17}/>,declarantes:<Scale size={17}/>,hallazgos:<AlertTriangle size={17}/>,preguntas:<ClipboardList size={17}/>,informes:<FileText size={17}/>,arquitectura:<ShieldCheck size={17}/>};
    return icons[v];
  };
  const findingList=<div className="stack">
    <div className="filter-row"><select aria-label="Filtrar hallazgos" value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">Todos ({findings.length})</option>{Object.entries(labels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></div>
    {!filtered.length&&<div className="empty">Aún no hay hallazgos. Reproduce la simulación o ingresa una declaración.</div>}
    {filtered.map(f=><button key={f.id} onClick={()=>setSelectedId(f.id)} className={"finding "+(selected?.id===f.id?"active":"")}><div className="finding-top"><TypePill category={f.category}/><small>{f.at}</small></div><strong>{f.topic}</strong><p>{f.reason}</p><small>Revisión: {f.review==="pending"?"pendiente":f.review==="confirmed"?"validado por usuario":"descartado"}</small></button>)}
  </div>;
  const detail=<div className="stack detail">
    {!selected?<div className="empty">Selecciona un hallazgo para contrastar versiones.</div>:<>
      <TypePill category={selected.category}/>
      <h3>{selected.topic}</h3>
      <p>{selected.reason}</p>
      <div className="comparison"><div><span>DECLARACIÓN ACTUAL</span><p>“{selected.currentQuote}”</p></div><div><span>FUENTE ANTERIOR</span><p>{selected.priorQuote?"“"+selected.priorQuote+"”":"No encontrada en el índice del declarante"}</p></div></div>
      <div className="source"><FileText size={17}/><div><strong>{selected.source||"Sin fuente anterior encontrada"}</strong><small>{selected.location||"No aplica"} · Certeza del patrón: {selected.confidence}</small></div></div>
      <label htmlFor="question">Pregunta sugerida para revisión del abogado</label>
      <textarea id="question" rows={3} value={questionDraft} onChange={e=>setQuestionDraft(e.target.value)}/>
      <div className="action-row"><button onClick={saveQuestion}><Plus size={15}/> Guardar pregunta</button><button className="outline" onClick={()=>{void navigator.clipboard?.writeText(questionDraft);setMessage("Pregunta copiada, si el navegador lo permite.");}}><Copy size={15}/> Copiar</button></div>
      <div className="action-row"><button className="outline ok" onClick={()=>review("confirmed")}><CheckCircle2 size={15}/> Validar</button><button className="outline danger" onClick={()=>review("dismissed")}><XCircle size={15}/> Descartar</button></div>
      <small className="warning">La clasificación es experimental: no prueba que una persona esté mintiendo ni determina admisibilidad probatoria.</small>
    </>}
  </div>;
  return <div className="layout">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Scale size={22}/></div><div><b>PULLEX IA</b><small>AUDIENCIA LIVE · by UMBRAL</small></div></div>
      <div className="case-label">EXPEDIENTE ACTIVO</div>
      <select className="case-select" value={activeId} onChange={e=>{stopDemo();setActiveId(e.target.value);setSelectedId(null);}} aria-label="Elegir expediente">{data.cases.map(c=><option value={c.id} key={c.id}>{c.title}</option>)}</select>
      <nav aria-label="Módulos">{navItems.map(v=><button key={v} className={"nav-button "+(view===v?"current":"")} onClick={()=>setView(v)}>{navIcon(v)}{names[v]}</button>)}</nav>
      <div className="sidebar-bottom"><ShieldCheck size={17}/><span>MODO LOCAL EXPERIMENTAL<br/><small>Sin nube ni copia de seguridad</small></span></div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">PULLEX IA / LITIGACIÓN PENAL</div><h1>{names[view]}</h1><p>{activeCase.radicado} · {activeCase.delito}</p></div><div className="header-actions"><span className="status"><i/> Motor local experimental</span><button className="outline" onClick={exportReport}><Download size={16}/> Exportar</button></div></header>
      {message&&<div className="notice" role="status"><span>{message}</span><button onClick={()=>setMessage("")} aria-label="Cerrar notificación">×</button></div>}
      {view==="audiencia"&&<>
        <section className="toolbar"><div><strong>Sesión de audiencia</strong><small>Solo caso ficticio o datos de prueba autorizados</small></div><div className="action-row">
          <button onClick={demoRunning?stopDemo:startDemo}>{demoRunning?<Pause size={16}/>:<Play size={16}/>} {demoRunning?"Detener demostración":"Reproducir demostración"}</button>
          <button className={"outline "+(micOn?"danger":"")} onClick={startMic}>{micOn?<MicOff size={16}/>:<Mic size={16}/>} {micOn?"Detener micrófono":"Iniciar micrófono"}</button>
        </div></section>
        <section className="workspace">
          <div className="panel"><div className="panel-head"><h2>Transcripción en vivo</h2><span>{turns.length} turnos</span></div><div className="scroll stack">
            {!turns.length&&<div className="empty">Inicia la simulación o ingresa una intervención.</div>}
            {turns.map(t=><div className="turn" key={t.id}><div className="turn-meta"><b>{t.speaker}</b><small>{t.at} · {t.origin}</small></div><p>{t.text}</p></div>)}
            {interim&&<div className="turn provisional"><small>Transcripción provisional</small><p>{interim}</p></div>}
          </div><div className="transcript-input"><label htmlFor="speaker">Participante (asignación manual)</label><select id="speaker" value={speaker} onChange={e=>setSpeaker(e.target.value)}><option>Boris</option><option>Defensor</option><option>Fiscal</option><option>Juez</option>{[...new Set(docs.map(s=>s.declarant))].filter(s=>!["Boris","Defensor","Fiscal","Juez"].includes(s)).map(s=><option key={s}>{s}</option>)}</select><textarea rows={3} placeholder="Escribe una declaración; se comparará con los documentos del declarante…" value={input} onChange={e=>setInput(e.target.value)}/><button onClick={()=>{addTurn(input);setInput("");}}>Agregar y analizar</button></div></div>
          <div className="panel"><div className="panel-head"><h2>Alertas inteligentes</h2><span>{findings.length} hallazgos</span></div><div className="scroll">{findingList}</div></div>
          <div className="panel"><div className="panel-head"><h2>Contraste documental</h2><span>Fuente verificable</span></div><div className="scroll">{detail}</div></div>
        </section>
      </>}
      {view==="expedientes"&&<section className="surface"><div className="section-top"><h2>Expedientes locales</h2><button onClick={createCase}><Plus size={16}/> Crear expediente</button></div><p>La información se guarda solo en este navegador y puede perderse. No cargar expedientes reservados.</p><div className="cards">{data.cases.map(c=><button className="case-card" key={c.id} onClick={()=>{setActiveId(c.id);setView("audiencia");}}><FolderOpen/><strong>{c.title}</strong><small>{c.radicado}</small><p>{c.delito}</p></button>)}</div></section>}
      {view==="biblioteca"&&<section className="surface"><h2>Biblioteca documental</h2><p>Fragmentos del expediente actual. Solo texto pegado y TXT en este MVP; PDF/OCR requieren integración adicional.</p><div className="form-grid"><div><label>Declarante</label><input value={newDeclarant} onChange={e=>setNewDeclarant(e.target.value)}/><label>Fuente / nombre del documento</label><input value={newSource} onChange={e=>setNewSource(e.target.value)}/><label>Declaración anterior — una frase por línea</label><textarea rows={6} value={newQuote} onChange={e=>setNewQuote(e.target.value)}/><div className="action-row"><button onClick={addSource}><Plus size={16}/> Añadir declaración</button><label className="file-label">Subir TXT<input type="file" accept=".txt,text/plain" onChange={e=>void addFile(e.target.files?.[0])}/></label></div></div><div><h3>{docs.length} fragmentos indexados</h3><div className="stack">{docs.map(d=><div className="source-card" key={d.id}><strong>{d.declarant}</strong><small>{d.source} · {d.location}</small><p>“{d.quote}”</p></div>)}</div></div></div></section>}
      {view==="declarantes"&&<section className="surface"><h2>Declarantes del expediente</h2><p>Identificación manual; el navegador no distingue automáticamente a los hablantes.</p><div className="cards">{[...new Set([...docs.map(d=>d.declarant),...turns.map(t=>t.speaker)])].map(w=><div className="case-card" key={w}><Scale/><strong>{w}</strong><small>{docs.filter(d=>d.declarant===w).length} fragmentos anteriores</small></div>)}</div></section>}
      {view==="hallazgos"&&<section className="surface"><h2>Hallazgos y revisión humana</h2><div className="form-grid"><div>{findingList}</div><div>{detail}</div></div></section>}
      {view==="preguntas"&&<section className="surface"><h2>Preguntas guardadas</h2><p>Preguntas para revisión jurídica, no guiones obligatorios.</p><div className="stack">{questions.length===0&&<p className="empty">Selecciona un hallazgo y guarda una pregunta.</p>}{questions.map(q=><div className="source-card" key={q.id}><small>{q.at}</small><p>{q.text}</p><button className="outline" onClick={()=>void navigator.clipboard?.writeText(q.text)}><Copy size={15}/> Copiar</button></div>)}</div></section>}
      {view==="informes"&&<section className="surface"><h2>Informe de audiencia</h2><p>Generado a partir de datos locales. No es un acta oficial.</p><div className="stats"><div><b>{turns.length}</b><span>Intervenciones</span></div><div><b>{findings.length}</b><span>Hallazgos</span></div><div><b>{findings.filter(f=>f.review==="confirmed").length}</b><span>Validados</span></div><div><b>{questions.length}</b><span>Preguntas</span></div></div><div className="action-row"><button onClick={exportReport}><Download size={16}/> Descargar informe JSON</button><button className="outline" onClick={()=>window.print()}><FileText size={16}/> Imprimir / guardar PDF</button></div><div className="stack">{findings.map(f=><div className="source-card" key={f.id}><TypePill category={f.category}/><p>{f.currentQuote}</p><small>Anterior: {f.priorQuote||"No encontrada"} · Estado: {f.review}</small></div>)}</div></section>}
      {view==="arquitectura"&&<section className="surface"><h2>Arquitectura modular</h2><p>React / TypeScript · captura con autorización · comparación local explicable · trazabilidad de fuentes · revisión humana</p><div className="architecture"><div>Micrófono / texto manual</div><span>↓</span><div>Transcripción final + hablante asignado</div><span>↓</span><div>Recuperación de fragmentos del mismo expediente y declarante</div><span>↓</span><div>Motor experimental de contraste</div><span>↓</span><div>Alertas con citas exactas → revisión → informe</div></div><h3>Límites de seguridad</h3><p>No hay servidor, autenticación, cifrado de localStorage, RLS, OCR ni IA semántica. El reconocimiento de voz depende del navegador y puede usar servicios de terceros. Solo apto para simulaciones.</p><h3>Producción futura</h3><p>API autenticada, PostgreSQL con RLS, almacenamiento privado, STT y diarización autorizados, controles de retención, auditoría y validación jurídica antes de usar expedientes reales.</p></section>}
      <footer>© PULLEX IA by UMBRAL · Módulo experimental · No usar con información judicial reservada</footer>
    </main>
  </div>;
}
