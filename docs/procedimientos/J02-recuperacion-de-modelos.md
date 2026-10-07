# J02 — Recuperación de modelos

Módulo: `procedimientos/j02_modelos.py` · Ruta: `POST /api/procedimientos/modelos` · Versión 1.0.0 ·
Estado: PROBADO sobre el catálogo interno; la biblioteca de Drive **no está conectada**.

## Interfaz

```python
buscar_modelos(consulta, filtros=None, limite=8, usuario=None) -> dict
registrar_proveedor(nombre, funcion)      # funcion(consulta, filtros, usuario) -> [candidato, …]
```

- Proveedor incluido: `catalogo`, adaptador a los 203 tipos de `documentos.py`.
- Punto de extensión: la biblioteca (`/api/biblioteca/buscar`, que construye otro componente) se conecta con
  `registrar_proveedor("biblioteca", funcion)`. Cada candidato debe traer `id` y `titulo`; puede traer `puntaje`,
  `razones`, `enlace_original` y `estado_validacion`. El proveedor recibe el usuario y **responde por aplicar los
  permisos antes de devolver nombres o extractos**.
- Un proveedor que falla no tumba la búsqueda: queda en `errores_de_proveedores`.

## Entradas

`consulta` (finalidad, materia, trámite, características) y `filtros`: `area`, `para` (abogado, ciudadano,
funcionario, estudiante) y `funcionario` (solo proyectos para despacho).

## Reglas

Búsqueda textual sin tildes, con raíz simple para plurales y derivados. Puntaje por campo: nombre 4, palabras
clave 3, trámite 2, descripción 1, área 1, ajustado por la parte de la consulta que cubre el modelo. No hay
búsqueda semántica en este procedimiento.

## Salida

`estado` (`CANDIDATOS`, `SIN_MODELO_ADECUADO`, `ABSTENCION`, `CONTRADICCION`) y, por candidato: identificador,
origen, título, área, finalidad, `razones` (qué palabras coincidieron y dónde), `terminos_sin_coincidencia`,
`requisitos` (datos obligatorios, número de opcionales, estructura), advertencias del tipo, estado de validación
y enlace original.

## Excepciones

- Sin consulta ni filtros → `ABSTENCION`.
- Área o destinatario desconocidos → `CONTRADICCION`.
- Ninguna coincidencia → `SIN_MODELO_ADECUADO`, y se dice que lo que se redacte será un borrador nuevo, no una
  plantilla recuperada.

## Límites

- La similitud textual no demuestra procedencia jurídica (advertencia fija en cada respuesta).
- Los tipos del catálogo interno son plantillas generadas por el sistema, sin revisión profesional
  (`PLANTILLA_GENERADA_SIN_REVISION_HUMANA`), y no tienen enlace a un original.
- No compara versiones similares ni detecta duplicados: eso corresponde a la biblioteca.

## Pseudocódigo

```
términos = palabras útiles de la consulta
para cada proveedor (catálogo + registrados):
    intentar: candidatos += proveedor(consulta, filtros, usuario)
    si falla: anotar el error y seguir
catálogo: filtrar por área y destinatario ; puntaje por campo ; descartar si ningún término coincide
ordenar por puntaje ; cortar en el límite ; añadir advertencias fijas
```

## Pruebas

`tests/test_procedimientos_otros.py`: candidatos con razones y requisitos; filtros; plural; sin modelo;
abstención; proveedor externo simulado (recibe el usuario, entra en el orden, convive con un proveedor que falla).

## Pendiente con dependencia concreta

Conectar el proveedor `biblioteca` cuando exista `/api/biblioteca/buscar` con control de permisos por usuario.
