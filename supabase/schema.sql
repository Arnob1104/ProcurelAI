-- Run this once in the Supabase SQL editor (Project > SQL editor > New query).
-- The app talks to Supabase only from the server with the service role key,
-- so row level security is on and no public policies are created.

create extension if not exists pgcrypto;

create table if not exists purchase_request_items (
  id bigint generated always as identity primary key,
  pr_number text not null,
  item text not null,
  description text not null,
  unit text not null,
  quantity_requested numeric not null check (quantity_requested > 0),
  max_unit_price numeric(14,2) not null check (max_unit_price > 0),
  unique (pr_number, item)
);

create table if not exists analyses (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  filename text not null,
  supplier_name text,
  quotation_no text,
  pr_number text,
  -- What the system decided.
  decision text not null check (decision in ('Approve', 'Reject', 'Needs a person to check')),
  -- complete: clear answer. awaiting_person: the system stopped and asked. resolved: a person answered.
  status text not null check (status in ('complete', 'awaiting_person', 'resolved')),
  -- The answer that counts: the system's, or the person's once resolved.
  final_decision text not null check (final_decision in ('Approve', 'Reject', 'Needs a person to check')),
  -- Full result: fields with quotes, rule results, findings, step trace.
  result jsonb not null
);

create table if not exists human_reviews (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references analyses(id) on delete cascade,
  decision text not null check (decision in ('Approve', 'Reject')),
  note text not null check (length(trim(note)) >= 5),
  reviewer text,
  created_at timestamptz not null default now(),
  unique (analysis_id)
);

create index if not exists analyses_created_idx on analyses (created_at desc);

alter table purchase_request_items enable row level security;
alter table analyses enable row level security;
alter table human_reviews enable row level security;
