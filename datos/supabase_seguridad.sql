-- PULLEX IA — seguridad específica de Supabase para el esquema de la app
--
-- Qué hace: quita a los roles públicos de Supabase (anon y authenticated, los que usa la API automática) todo
-- permiso sobre el esquema de PULLEX IA y lo que contiene. La app no usa esa API: se conecta directo a
-- PostgreSQL con el usuario dueño de las tablas. Así, aunque alguien agregue por error este esquema a los
-- «esquemas expuestos» de la API, no se puede leer ni escribir nada desde un navegador.
--
-- Cómo se aplica: igual que esquema_postgres.sql, con el search_path puesto y dentro de una transacción:
--     BEGIN;
--     SET LOCAL search_path TO pullex;
--     \i datos/supabase_seguridad.sql
--     COMMIT;
-- Es idempotente y no falla en un PostgreSQL que no tenga esos roles (por ejemplo, el de las pruebas).
-- Solo toca el esquema de destino: no cambia roles ni nada global de la base, que se comparte con otros
-- productos. Vuelve a aplicarlo cuando se agreguen tablas.

DO $pullex$
DECLARE
    ruta text := current_setting('search_path');
    destino text := btrim(split_part(ruta, ',', 1), ' "');
    rol text;
BEGIN
    IF destino = '' OR destino IN ('public', '$user', 'information_schema') OR left(destino, 3) = 'pg_' THEN
        RAISE EXCEPTION 'PULLEX IA: antes de aplicar este archivo fija el esquema de destino (SET LOCAL search_path TO pullex). search_path actual: %', ruta;
    END IF;
    IF to_regnamespace(quote_ident(destino)) IS NULL THEN
        RAISE EXCEPTION 'PULLEX IA: el esquema % no existe. Aplica primero datos/esquema_postgres.sql.', destino;
    END IF;
    FOREACH rol IN ARRAY ARRAY['anon', 'authenticated'] LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = rol) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA %I FROM %I', destino, rol);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA %I FROM %I', destino, rol);
            EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA %I FROM %I', destino, rol);
            EXECUTE format('REVOKE ALL ON ALL ROUTINES IN SCHEMA %I FROM %I', destino, rol);
        END IF;
    END LOOP;
END
$pullex$;
