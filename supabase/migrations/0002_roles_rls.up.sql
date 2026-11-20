-- Least-privilege roles + row-level security.
-- Login users are created per deployment and granted one of these roles.
do $$ begin
  if not exists (select from pg_roles where rolname = 'marketlens_reader') then
    create role marketlens_reader nologin;
  end if;
  if not exists (select from pg_roles where rolname = 'marketlens_writer') then
    create role marketlens_writer nologin;
  end if;
end $$;

grant usage on schema public to marketlens_reader, marketlens_writer;
grant select on all tables in schema public to marketlens_reader, marketlens_writer;
grant insert, update, delete on all tables in schema public to marketlens_writer;
grant usage on all sequences in schema public to marketlens_writer;

-- Supabase exposes tables to its 'anon'/'authenticated' roles via PostgREST: remove that access.
do $$ declare r text; begin
  foreach r in array array['anon','authenticated'] loop
    if exists (select from pg_roles where rolname = r) then
      execute format('revoke all on all tables in schema public from %I', r);
    end if;
  end loop;
end $$;

do $$ declare t text; begin
  foreach t in array array['companies','universe_membership','stock_prices','technical_indicators',
    'news_articles','article_companies','model_versions','sentiment_predictions',
    'aggregated_sentiment','evaluation_labels','model_evaluations','ingestion_logs','llm_usage']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy %I on %I for select to marketlens_reader using (true)',
                   t || '_read', t);
    execute format('create policy %I on %I for all to marketlens_writer using (true) with check (true)',
                   t || '_write', t);
  end loop;
end $$;

-- The read-only API never needs internal operational tables.
revoke select on ingestion_logs, llm_usage from marketlens_reader;
