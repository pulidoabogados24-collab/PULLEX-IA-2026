-- Biblioteca privada de Pullex IA. Se aplica solo al esquema pullex de Umbral.
-- No modifica ni migra las tablas existentes.
create table if not exists pullex.biblioteca_documentos (
    id bigint generated always as identity primary key,
    proveedor text not null default 'google_drive',
    drive_id text not null,
    coleccion text not null check (coleccion in ('PACK JURIDICO 1', 'PACK JURIDICO 2')),
    ruta text not null,
    nombre text not null,
    mime_type text not null,
    tamano_bytes bigint not null check (tamano_bytes >= 0),
    url_origen text not null,
    estado_procesamiento text not null default 'ENCONTRADO'
        check (estado_procesamiento in ('ENCONTRADO', 'LEIDO', 'EXTRAIDO', 'INDEXADO', 'PENDIENTE', 'ERROR')),
    sensibilidad text not null default 'PENDIENTE',
    derechos text not null default 'POR_CONFIRMAR',
    jurisdiccion text,
    autoridad text,
    fecha_fuente date,
    vigencia text not null default 'PENDIENTE',
    sha256_original text check (sha256_original is null or sha256_original ~ '^[0-9a-f]{64}$'),
    almacenamiento_original text,
    error_procesamiento text,
    inventariado_en timestamptz not null default now(),
    actualizado_en timestamptz not null default now(),
    unique (proveedor, drive_id)
);

create index if not exists biblioteca_documentos_coleccion_estado_idx
    on pullex.biblioteca_documentos (coleccion, estado_procesamiento);
create index if not exists biblioteca_documentos_sha256_idx
    on pullex.biblioteca_documentos (sha256_original) where sha256_original is not null;

create table if not exists pullex.biblioteca_fragmentos (
    id bigint generated always as identity primary key,
    documento_id bigint not null references pullex.biblioteca_documentos(id) on delete restrict,
    ordinal integer not null check (ordinal >= 0),
    ubicacion text not null,
    contenido text not null,
    texto_busqueda tsvector generated always as (to_tsvector('spanish', contenido)) stored,
    creado_en timestamptz not null default now(),
    unique (documento_id, ordinal)
);

create index if not exists biblioteca_fragmentos_busqueda_idx
    on pullex.biblioteca_fragmentos using gin (texto_busqueda);

alter table pullex.biblioteca_documentos enable row level security;
alter table pullex.biblioteca_fragmentos enable row level security;

-- Los documentos y sus nombres pueden contener datos personales. Ninguna política
-- habilita lectura desde navegador; solo el proceso servidor, con credencial privada,
-- puede importarlos hasta definir autorización por usuario y revisión jurídica.
revoke all on pullex.biblioteca_documentos, pullex.biblioteca_fragmentos
    from public, anon, authenticated;
revoke all on sequence pullex.biblioteca_documentos_id_seq,
    pullex.biblioteca_fragmentos_id_seq from public, anon, authenticated;
