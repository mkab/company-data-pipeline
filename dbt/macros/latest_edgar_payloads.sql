{#
    The payload of the latest fetch of each dataset and company (`cik`, null for the tickers file).
    A staging model selects its dataset from it.

    raw keeps every fetch, and staging reads the latest only.
    A company whose latest fetch of a dataset found nothing (a 404) has no row for it,
    even when an earlier fetch had a payload.
    `id` breaks a tie on `fetched_at`, so the pick never changes between runs
#}
{% macro latest_edgar_payloads() %}
    select
        latest_fetches.dataset,
        latest_fetches.cik,
        payloads.payload
    from (
        select distinct on (dataset, cik)
            dataset,
            cik,
            payload_id
        from {{ source('raw', 'edgar_fetches') }}
        order by dataset, cik, fetched_at desc, id desc
    ) as latest_fetches
    inner join {{ source('raw', 'edgar_payloads') }} as payloads
        on payloads.id = latest_fetches.payload_id
{% endmacro %}
