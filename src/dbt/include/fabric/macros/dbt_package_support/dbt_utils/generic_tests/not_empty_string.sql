{% macro fabric__test_not_empty_string(model, column_name, trim_whitespace=true) %}

    with
    
    all_values as (

        select 


            {% if trim_whitespace == true -%}

                trim({{ column_name }}) as {{ column_name }}

            {%- else -%}

                {{ column_name }}

            {%- endif %}
            
        from {{ model }}

    ),

    errors as (

        select * from all_values
        {#- Override: upstream uses `where col = ''`. T-SQL/varchar uses SQL-92 trailing-whitespace-insensitive equality, so `'   ' = ''` is true; that would flag whitespace-only rows even when `trim_whitespace=false`. Using `datalength()` measures real byte length and preserves the `trim_whitespace=false` semantics. -#}
        where datalength({{ column_name }}) = 0

    )

    select * from errors

{% endmacro %}