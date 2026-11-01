/**
 * Motor determinista experimental. Nunca decide credibilidad, no usa IA remota.
 * Las fuentes se restringen por expediente y por declarante.
 */
export type Category = "possible-contradiction" | "coincides" | "expansion" | "not-found" | "inconclusive";
export type Review = "pending" | "confirmed" | "dismissed";
export interface SourceFragment {
  id: string;
  caseId: string;
  declarant: string;
  quote: string;
  source: string;
  location?: string;
}
export interface FindingResult {
  category: Category;
  currentQuote: string;
  priorQuote: string | null;
  sourceId: string | null;
  source: string | null;
  location: string | null;
  reason: string;
  confidence: "alta" | "media" | "baja";
  suggestedQuestion: string;
  topic: string;
}

export function normalize(text: string): string {
  return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9: ]+/g, " ").replace(/\s+/g, " ").trim();
}
const numbers: Record<string, number> = {una:1,uno:1,dos:2,tres:3,cuatro:4,cinco:5,seis:6,siete:7,ocho:8,nueve:9,diez:10,once:11,doce:12,trece:13,catorce:14,quince:15,dieciseis:16,diecisiete:17,dieciocho:18,diecinueve:19,veinte:20,veintiuna:21,veintiuno:21,veintidos:22,veintitres:23};
export function getHour(text: string): number | null {
  const s = normalize(text);
  const match = s.match(/(?:a|sobre|hacia|eran|alrededor de) las?\s+(una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|veinte|veintiuna|veintiuno|veintidos|veintitres|\d{1,2})(?::\d\d)?(?:\s+de la\s+(noche|tarde|manana))?/);
  if (!match) return null;
  let h = numbers[match[1]] ?? Number(match[1]);
  if (h > 23 || h < 0 || Number.isNaN(h)) return null;
  const period = match[2] || (s.match(/\b(p\s*m|a\s*m)\b/)?.[1] === "p m" ? "tarde" : "");
  if ((period === "tarde" || period === "noche") && h < 12) h += 12;
  if (period === "manana" && h === 12) h = 0;
  return h;
}
function topic(text: string): string {
  const s = normalize(text);
  if (/lleg|arrib|ingres|entr[eo]/.test(s)) return "hora de llegada";
  if (/chaqueta|camisa|pantalon|vestid|prenda/.test(s)) return "prenda de vestir";
  if (/corr|huy|escap|salio|salieron|motocicleta|moto/.test(s)) return "huida";
  return "general";
}
const colors = ["negra","negro","blanca","blanco","roja","rojo","azul","verde","amarilla","amarillo","gris"];
function getColor(text: string) {
  const tokens = normalize(text).split(" ");
  const found = tokens.find(t=>colors.includes(t));
  return found ? found.replace(/a$/, "o") : null;
}
function significance(a: string, b: string): number {
  const sa = new Set(normalize(a).split(" ").filter(t=>t.length>3));
  const sb = new Set(normalize(b).split(" ").filter(t=>t.length>3));
  let shared=0;
  for(const v of sa) if(sb.has(v)) shared++;
  return shared / Math.max(1,Math.min(sa.size,sb.size));
}
export function compareStatement(
  currentQuote: string, declarant: string, caseId: string, sources: SourceFragment[],
): FindingResult | null {
  if (!currentQuote.trim()) return null;
  const candidates = sources.filter(s=>s.caseId===caseId && normalize(s.declarant)===normalize(declarant) && s.quote.trim());
  const make = (category: Category, reason: string, target: SourceFragment | null, confidence: FindingResult["confidence"], question: string):FindingResult => ({
    category, currentQuote, priorQuote: target?.quote ?? null, sourceId: target?.id ?? null,
    source: target?.source ?? null, location: target?.location ?? null, reason, confidence,
    suggestedQuestion: question, topic: topic(currentQuote)
  });
  if (!candidates.length) return make("not-found","No hay manifestaciones anteriores indexadas de este declarante en este expediente. No permite inferir falsedad.",null,"baja","¿Podría precisar esta afirmación?");
  const currentTopic=topic(currentQuote);
  const scored = candidates.map(src=>({
    src, score: (topic(src.quote)===currentTopic ? 4 : 0) + significance(currentQuote,src.quote)
  })).sort((a,b)=>b.score-a.score);
  const best=scored[0];
  if (best.score < 3.5) return make("not-found","No se encontró un fragmento anterior sobre el mismo asunto; la ausencia no demuestra contradicción.",null,"baja","¿Puede explicar con más detalle lo sucedido?");
  const prior=best.src;
  const olderHour=getHour(prior.quote), newerHour=getHour(currentQuote);
  if (currentTopic==="hora de llegada" && olderHour!==null && newerHour!==null) {
    const difference=Math.abs(olderHour-newerHour);
    if(difference >= 1) return make("possible-contradiction","Se identificaron horarios diferentes ("+olderHour+":00 y "+newerHour+":00) para una llegada aparentemente relacionada. Verificar lugar, fecha y aproximaciones.",prior,"media","¿Recuerda qué hora indicó en su declaración anterior?");
    return make("coincides","Los horarios mencionados son compatibles; verificar contexto y precisiones.",prior,"media","¿Ratifica el horario que señaló anteriormente?");
  }
  if(currentTopic==="prenda de vestir") {
    const c1=getColor(currentQuote), c2=getColor(prior.quote);
    if(c1 && c2 && c1!==c2) return make("possible-contradiction","Se describen colores diferentes para una prenda aparentemente relacionada. Verificar si se habla de la misma persona y prenda.",prior,"media","¿Qué color tenía exactamente la prenda que observó?");
    if(c1 && c1===c2) return make("coincides","Se repite de forma compatible la descripción del color de la prenda.",prior,"media","¿Ratifica la descripción de la prenda?");
  }
  if(currentTopic==="huida"){
    const now=normalize(currentQuote), before=normalize(prior.quote);
    const newVehicle=/motocicleta|moto/.test(now) && !/motocicleta|moto/.test(before);
    if(newVehicle) return make("expansion","Se añade una motocicleta que no aparece en el fragmento anterior; es ampliación, no contradicción por sí sola.",prior,"media","¿Puede precisar cuándo y cómo observó la motocicleta?");
    if(significance(currentQuote,prior.quote)>0.3) return make("coincides","Ambas expresiones son compatibles respecto de la huida.",prior,"media","¿Ratifica lo afirmado sobre la huida?");
  }
  if(significance(currentQuote,prior.quote)>0.65) return make("coincides","Los fragmentos son textualmente similares. La equivalencia plena requiere revisión contextual.",prior,"baja","¿Ratifica su manifestación anterior?");
  return make("inconclusive","El motor local no puede determinar la relación entre los fragmentos con suficiente seguridad.",prior,"baja","¿Podría aclarar su declaración?");
}
export const DEMO_SOURCES: SourceFragment[] = [
  {id:"src-time",caseId:"demo",declarant:"Boris",source:"Entrevista Boris — 12 de marzo (ficticia)",location:"Pág. 4, párrafo 2",quote:"Llegué aproximadamente a las nueve de la noche"},
  {id:"src-clothes",caseId:"demo",declarant:"Boris",source:"Entrevista Boris — 12 de marzo (ficticia)",location:"Pág. 5, párrafo 1",quote:"Vi que el agresor llevaba una chaqueta negra"},
  {id:"src-flight",caseId:"demo",declarant:"Boris",source:"Entrevista Boris — 12 de marzo (ficticia)",location:"Pág. 5, párrafo 3",quote:"Observé que una persona salió corriendo"},
];
export const DEMO_TURNS = [
  {speaker:"Defensor",text:"Señor Boris, ¿a qué hora llegó al establecimiento?"},
  {speaker:"Boris",text:"Yo llegué al establecimiento sobre las once de la noche"},
  {speaker:"Boris",text:"El agresor tenía una chaqueta negra"},
  {speaker:"Boris",text:"La persona salió corriendo y después se subió a una motocicleta"},
];
