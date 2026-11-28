-- Every ticker in the tickers file, the only source of tickers
select
    cik,
    ticker,
    exchange
from {{ ref('stg_edgar__company_tickers') }}
