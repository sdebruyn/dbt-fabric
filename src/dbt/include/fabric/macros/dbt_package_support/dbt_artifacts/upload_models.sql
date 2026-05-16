{% macro fabric__get_models_dml_sql(models) -%}

    {% if models != [] %}
        {% set model_values %}
        select
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"
        from ( values
        {% for model in models -%}
                {% set model_copy = dbt_artifacts.safe_copy_mapping(model) -%}
            (
                '{{ invocation_id }}', {# command_invocation_id #}
                '{{ model_copy.unique_id }}', {# node_id #}
                '{{ run_started_at }}', {# run_started_at #}
                '{{ model_copy.database }}', {# database #}
                '{{ model_copy.schema }}', {# schema #}
                '{{ model_copy.name }}', {# name #}
                '{{ tojson(model_copy.depends_on.nodes) }}', {# depends_on_nodes #}
                '{{ model_copy.package_name }}', {# package_name #}
                '{{ model_copy.original_file_path }}', {# path #}
                '{{ model_copy.checksum.checksum }}', {# checksum #}
                '{{ model_copy.config.materialized }}', {# materialization #}
                '{{ tojson(model_copy.tags) }}', {# tags #}
                '{{ tojson(model_copy.config.meta) | replace("'","''") }}', {# meta #}
                '{{ model_copy.alias }}', {# alias #}
                {% if var('dbt_artifacts_exclude_all_results', false) %}
                    null
                {% else %}
                    '{{ tojson(model_copy) | replace("'","''") }}' {# all_results #}
                {% endif %}
            )
            {%- if not loop.last %},{%- endif %}
        {%- endfor %}

        ) v ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15")

        {% endset %}
        {{ model_values }}
    {% else %} {{ return("") }}
    {% endif %}
{% endmacro -%}
