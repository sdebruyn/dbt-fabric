{%- macro fabric__measure_median(column_name, data_type, cte_name) -%}
{%- if dbt_profiler.is_numeric_dtype(data_type) and not dbt_profiler.is_struct_dtype(data_type) -%}
(select top 1 percentile_cont(0.5) within group (order by {{ adapter.quote(column_name) }}) over () from {{ cte_name }})
{%- else -%}
cast(null as {{ dbt.type_numeric() }})
{%- endif -%}
{%- endmacro -%}

{%- macro fabric__measure_std_dev_population(column_name, data_type) -%}
{%- if dbt_profiler.is_numeric_dtype(data_type) and not dbt_profiler.is_struct_dtype(data_type) -%}
stdevp({{ adapter.quote(column_name) }})
{%- else -%}
cast(null as {{ dbt.type_numeric() }})
{%- endif -%}
{%- endmacro -%}

{%- macro fabric__measure_std_dev_sample(column_name, data_type) -%}
{%- if dbt_profiler.is_numeric_dtype(data_type) and not dbt_profiler.is_struct_dtype(data_type) -%}
stdev({{ adapter.quote(column_name) }})
{%- else -%}
cast(null as {{ dbt.type_numeric() }})
{%- endif -%}
{%- endmacro -%}

{%- macro fabric__measure_is_unique(column_name, data_type) -%}
{%- if not dbt_profiler.is_struct_dtype(data_type) -%}
case when cast(count(*) as {{ dbt.type_bigint() }}) > 0 then
        case when count(distinct {{ adapter.quote(column_name) }}) = count(*) then 1 else 0 end
    else null
    end
{%- else -%}
null
{%- endif -%}
{%- endmacro -%}
