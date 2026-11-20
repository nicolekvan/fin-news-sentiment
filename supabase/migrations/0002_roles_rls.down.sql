do $$ declare t text; begin
  foreach t in array array['companies','universe_membership','stock_prices','technical_indicators',
    'news_articles','article_companies','model_versions','sentiment_predictions',
    'aggregated_sentiment','evaluation_labels','model_evaluations','ingestion_logs','llm_usage']
  loop
    execute format('drop policy if exists %I on %I', t || '_read', t);
    execute format('drop policy if exists %I on %I', t || '_write', t);
    execute format('alter table %I disable row level security', t);
  end loop;
end $$;
revoke all on all tables in schema public from marketlens_reader, marketlens_writer;
revoke all on all sequences in schema public from marketlens_writer;
revoke usage on schema public from marketlens_reader, marketlens_writer;
