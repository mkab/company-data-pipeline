{#
    dbt's `relationships` on several columns at once: every row's combination of `columns`
    exists in `to`, under the same names there.
    A row with a null in any of them is skipped, as `relationships` skips a null
#}
{% test relationships_composite(model, columns, to) %}
    select child.*
    from {{ model }} as child
    where
        {% for column in columns %}
            child.{{ column }} is not null and
        {% endfor %}
        not exists (
            select 1
            from {{ to }} as parent
            where
                {% for column in columns %}
                    parent.{{ column }} = child.{{ column }}{% if not loop.last %} and{% endif %}
                {% endfor %}
        )
{% endtest %}
