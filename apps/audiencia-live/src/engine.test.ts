import { describe, it, expect } from "vitest";
import { compareStatement, DEMO_SOURCES, getHour } from "./engine";
describe("motor de contraste documental",()=>{
  it("normaliza las nueve de la noche",()=>expect(getHour("Llegué aproximadamente a las nueve de la noche")).toBe(21));
  it("normaliza las once de la noche",()=>expect(getHour("Llegué sobre las once de la noche")).toBe(23));
  it("marca horario diferente como posible contradicción",()=> {
    const f=compareStatement("Yo llegué al establecimiento sobre las once de la noche","Boris","demo",DEMO_SOURCES);
    expect(f?.category).toBe("possible-contradiction");
    expect(f?.priorQuote).toBe(DEMO_SOURCES[0].quote);
  });
  it("reconoce coincidencia de chaqueta negra",()=>expect(compareStatement("El agresor tenía una chaqueta negra","Boris","demo",DEMO_SOURCES)?.category).toBe("coincides"));
  it("reconoce ampliación de motocicleta",()=>expect(compareStatement("La persona salió corriendo y después se subió a una motocicleta","Boris","demo",DEMO_SOURCES)?.category).toBe("expansion"));
  it("no mezcla declarantes",()=>expect(compareStatement("Llegué sobre las once de la noche","Otro","demo",DEMO_SOURCES)?.category).toBe("not-found"));
  it("no mezcla expedientes",()=>expect(compareStatement("Llegué sobre las once de la noche","Boris","otro",DEMO_SOURCES)?.category).toBe("not-found"));
});
