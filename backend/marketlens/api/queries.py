"""Read-only SQL used by the API. Every query is parameterized."""

LATEST_AGG = """
  select distinct on (company_id) company_id, as_of, score, label, n_articles, n_unique_stories
  from aggregated_sentiment where method_version = :mv
  order by company_id, as_of desc
"""

SCREENER = f"""
with px as (
  select company_id, trade_date, close, volume,
         lag(close, 1) over w as prev_close,
         lag(close, 21) over w as close_1m,
         lag(close, 63) over w as close_3m,
         lag(close, 252) over w as close_1y,
         row_number() over (partition by company_id order by trade_date desc) as rn
  from stock_prices window w as (partition by company_id order by trade_date)
),
latest as (select * from px where rn = 1),
mem as (
  select distinct on (company_id) company_id, rank, market_cap_usd
  from universe_membership order by company_id, effective_from desc
),
agg as ({LATEST_AGG}),
news7 as (
  select ac.company_id, count(*) as news_7d
  from article_companies ac join news_articles a on a.id = ac.article_id
  where a.duplicate_of is null
    and a.published_at > (select max(published_at) from news_articles) - interval '7 days'
  group by ac.company_id
)
select c.ticker, c.name, c.industry, c.exchange, c.is_benchmark,
       mem.rank, mem.market_cap_usd,
       l.trade_date, l.close, l.volume,
       (l.close / nullif(l.prev_close, 0) - 1) as change_1d,
       (l.close / nullif(l.close_1m, 0) - 1) as perf_1m,
       (l.close / nullif(l.close_3m, 0) - 1) as perf_3m,
       (l.close / nullif(l.close_1y, 0) - 1) as perf_1y,
       i.rsi_14, i.sma_50, i.sma_200, i.macd_hist, i.atr_14,
       agg.score as sentiment_score, agg.label as sentiment_label,
       agg.n_unique_stories, coalesce(news7.news_7d, 0) as news_7d
from companies c
left join latest l on l.company_id = c.id
left join technical_indicators i on i.company_id = c.id and i.trade_date = l.trade_date
left join mem on mem.company_id = c.id
left join agg on agg.company_id = c.id
left join news7 on news7.company_id = c.id
order by c.is_benchmark, mem.rank nulls last, c.ticker
"""

PRICES = """
select p.trade_date, p.open, p.high, p.low, p.close, p.volume, p.source,
       i.sma_20, i.sma_50, i.sma_200, i.ema_12, i.ema_26, i.rsi_14, i.macd, i.macd_signal,
       i.macd_hist, i.bb_upper, i.bb_mid, i.bb_lower, i.atr_14
from stock_prices p
left join technical_indicators i using (company_id, trade_date)
where p.company_id = :cid and p.trade_date between :start and :end
order by p.trade_date
"""

NEWS = """
select a.id as article_id, a.headline, a.summary, a.url, a.source_name, a.provider,
       a.published_at, a.event_type, a.duplicate_of,
       c.ticker, c.name as company, c.industry,
       p.label, p.confidence, p.p_positive, p.p_negative, p.p_neutral,
       p.explanation, p.explanation_method, p.evidence_quotes, p.needs_review,
       ac.relevance, mv.name as model_name, mv.version as model_version
from sentiment_predictions p
join news_articles a on a.id = p.article_id
join companies c on c.id = p.company_id
join article_companies ac on ac.article_id = p.article_id and ac.company_id = p.company_id
join model_versions mv on mv.id = p.model_version_id
where (cast(:ticker as text) is null or c.ticker = :ticker)
  and (cast(:industry as text) is null or c.industry = :industry)
  and (cast(:label as text) is null or p.label = :label)
  and (cast(:event_type as text) is null or a.event_type = :event_type)
  and (cast(:source as text) is null or a.source_name = :source)
  and (cast(:start as timestamptz) is null or a.published_at >= :start)
  and (cast(:end as timestamptz) is null or a.published_at < :end)
  and (cast(:q as text) is null or a.headline ilike '%' || :q || '%')
  and (:include_duplicates or a.duplicate_of is null)
order by a.published_at desc, a.id, c.ticker
limit :limit offset :offset
"""
