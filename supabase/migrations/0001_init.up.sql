-- MarketLens AI core schema. All timestamps are UTC (timestamptz).

create table companies (
  id            bigint generated always as identity primary key,
  ticker        text not null unique,
  name          text not null,
  aliases       text[] not null default '{}',
  industry      text not null,
  exchange      text,
  cik           text unique,           -- one row per issuer: prevents double-counting share classes
  is_benchmark  boolean not null default false,
  created_at    timestamptz not null default now(),
  check (is_benchmark or cik is not null)
);

create table universe_membership (
  company_id      bigint not null references companies(id),
  effective_from  date not null,
  effective_to    date,
  rank            int check (rank > 0),
  market_cap_usd  numeric check (market_cap_usd > 0),
  method_version  text not null,
  primary key (company_id, effective_from),
  check (effective_to is null or effective_to > effective_from)
);

create table stock_prices (
  company_id   bigint not null references companies(id),
  trade_date   date not null,
  open         numeric not null check (open > 0),
  high         numeric not null,
  low          numeric not null,
  close        numeric not null check (close > 0),
  adj_close    numeric,
  volume       bigint not null check (volume >= 0),
  source       text not null,           -- provider name, or 'demo' for synthetic data
  ingested_at  timestamptz not null default now(),
  primary key (company_id, trade_date),
  check (high >= low)
);

create table technical_indicators (
  company_id   bigint not null,
  trade_date   date not null,
  sma_20 numeric, sma_50 numeric, sma_200 numeric, ema_12 numeric, ema_26 numeric,
  rsi_14 numeric, macd numeric, macd_signal numeric, macd_hist numeric,
  bb_upper numeric, bb_mid numeric, bb_lower numeric, atr_14 numeric,
  computed_at  timestamptz not null default now(),
  primary key (company_id, trade_date),
  foreign key (company_id, trade_date) references stock_prices(company_id, trade_date) on delete cascade
);

create table news_articles (
  id                   bigint generated always as identity primary key,
  provider             text not null,   -- 'finnhub', 'alphavantage', 'demo', ...
  provider_article_id  text,
  url                  text not null,
  canonical_url_hash   text not null unique,
  headline             text not null,
  summary              text,            -- provider summary only, never full article text
  source_name          text not null,
  published_at         timestamptz not null,
  ingested_at          timestamptz not null default now(),
  content_fingerprint  text not null,
  duplicate_of         bigint references news_articles(id),
  event_type           text,
  unique (provider, provider_article_id),
  check (duplicate_of is null or duplicate_of <> id)
);
create index news_articles_published_idx on news_articles (published_at desc);
create index news_articles_fingerprint_idx on news_articles (content_fingerprint);

create table article_companies (
  article_id    bigint not null references news_articles(id) on delete cascade,
  company_id    bigint not null references companies(id),
  relevance     numeric not null check (relevance between 0 and 1),
  match_method  text not null check (match_method in ('ticker','alias','ner','provider_tag')),
  passage       text not null,
  primary key (article_id, company_id)
);
create index article_companies_company_idx on article_companies (company_id);

create table model_versions (
  id          bigint generated always as identity primary key,
  name        text not null,
  version     text not null,
  config      jsonb not null,
  created_at  timestamptz not null default now(),
  unique (name, version)
);

create table sentiment_predictions (
  id                  bigint generated always as identity primary key,
  article_id          bigint not null,
  company_id          bigint not null,
  model_version_id    bigint not null references model_versions(id),
  label               text not null
                      check (label in ('bullish','bearish','neutral','insufficient_evidence')),
  p_positive          numeric check (p_positive between 0 and 1),
  p_negative          numeric check (p_negative between 0 and 1),
  p_neutral           numeric check (p_neutral between 0 and 1),
  confidence          numeric check (confidence between 0 and 1),
  explanation         text,
  explanation_method  text check (explanation_method in ('evidence_template','claude')),
  evidence_quotes     jsonb not null default '[]',
  needs_review        boolean not null default false,
  created_at          timestamptz not null default now(),
  foreign key (article_id, company_id)
    references article_companies(article_id, company_id) on delete cascade,
  unique (article_id, company_id, model_version_id)
);
create index sentiment_predictions_company_idx on sentiment_predictions (company_id, created_at desc);

create table aggregated_sentiment (
  company_id        bigint not null references companies(id),
  as_of             timestamptz not null,
  method_version    text not null,
  score             numeric not null check (score between -1 and 1),
  label             text not null
                    check (label in ('bullish','bearish','neutral','insufficient_evidence')),
  n_articles        int not null check (n_articles >= 0),
  n_unique_stories  int not null check (n_unique_stories >= 0),
  primary key (company_id, as_of, method_version)
);

create table evaluation_labels (
  article_id  bigint not null,
  company_id  bigint not null,
  label       text not null
              check (label in ('bullish','bearish','neutral','insufficient_evidence')),
  labeler     text not null,
  labeled_at  timestamptz not null default now(),
  notes       text,
  primary key (article_id, company_id, labeler),
  foreign key (article_id, company_id)
    references article_companies(article_id, company_id) on delete cascade
);

create table model_evaluations (
  id                bigint generated always as identity primary key,
  model_version_id  bigint not null references model_versions(id),
  dataset           text not null,
  split             text not null,
  metrics           jsonb not null,
  confusion_matrix  jsonb not null,
  created_at        timestamptz not null default now()
);

create table ingestion_logs (
  id             bigint generated always as identity primary key,
  job            text not null,
  provider       text,
  started_at     timestamptz not null default now(),
  finished_at    timestamptz,
  status         text not null check (status in ('running','success','partial','failed')),
  rows_upserted  int not null default 0,
  api_calls      int not null default 0,
  error_summary  text
);
create index ingestion_logs_job_idx on ingestion_logs (job, started_at desc);

create table llm_usage (
  usage_date     date primary key,
  requests       int not null default 0 check (requests >= 0),
  input_tokens   bigint not null default 0,
  output_tokens  bigint not null default 0,
  est_cost_usd   numeric not null default 0
);
