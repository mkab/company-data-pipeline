with tickers_file as (
    select
        cik,
        payload
    from ({{ latest_edgar_payloads() }}) as latest_payloads
    where dataset = 'company_tickers'
)

-- Each entry of `data` is a row of the fields `fields` names, in that order:
-- cik, name, ticker, exchange
select
    (ticker_rows.ticker_row ->> 0)::bigint as cik,
    ticker_rows.ticker_row ->> 1 as name,
    ticker_rows.ticker_row ->> 2 as ticker,
    ticker_rows.ticker_row ->> 3 as exchange
from tickers_file
cross join lateral jsonb_array_elements(tickers_file.payload -> 'data') as ticker_rows (ticker_row)
