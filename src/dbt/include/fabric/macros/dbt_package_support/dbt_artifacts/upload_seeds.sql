{% macro fabric__get_seeds_dml_sql(seeds) -%}

    {% if seeds != [] %}
        {% set seed_values %}
        select "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"
        from ( values
        {% for seed in seeds -%}
            (
                '{{ invocation_id }}', {# command_invocation_id #}
                '{{ seed.unique_id }}', {# node_id #}
                '{{ run_started_at }}', {# run_started_at #}
                '{{ seed.database }}', {# database #}
                '{{ seed.schema }}', {# schema #}
                '{{ seed.name }}', {# name #}
                '{{ seed.package_name }}', {# package_name #}
                '{{ seed.original_file_path }}', {# path #}
                '{{ seed.checksum.checksum }}', {# checksum #}
                '{{ tojson(seed.config.meta) | replace("'","''") }}', {# meta #}
                '{{ seed.alias }}', {# alias #}
                {% if var('dbt_artifacts_exclude_all_results', false) %}
                    null
                {% else %}
                    '{{ tojson(seed) | replace("'","''") }}' {# all_results #}
                {% endif %}
            )
            {%- if not loop.last %},{%- endif %}
        {%- endfor %}

        ) v ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12")

        {% endset %}
        {{ seed_values }}
    {% else %} {{ return("") }}
    {% endif %}
{% endmacro -%}
