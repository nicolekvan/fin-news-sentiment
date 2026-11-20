-- SEC filings (shown as chart events) and macro series (FRED).
create table sec_filings (
  company_id        bigint not null references companies(id),
  accession_number  text primary key,
  form              text not null,
  filed_date        date not null,
  report_date       date,
  primary_document  text,
  url               text not null,
  ingested_at       timestamptz not null default now()
);
create index sec_filings_company_idx on sec_filings (company_id, filed_date desc);

create table macro_observations (
  series_id  text not null,
  obs_date   date not null,
  value      numeric,            -- null where the source reports a missing value
  source     text not null,
  primary key (series_id, obs_date)
);

grant select on sec_filings, macro_observations to marketlens_reader, marketlens_writer;
grant insert, update, delete on sec_filings, macro_observations to marketlens_writer;

do $$ declare t text; begin
  foreach t in array array['sec_filings','macro_observations'] loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy %I on %I for select to marketlens_reader using (true)',
                   t || '_read', t);
    execute format('create policy %I on %I for all to marketlens_writer using (true) with check (true)',
                   t || '_write', t);
  end loop;
end $$;
