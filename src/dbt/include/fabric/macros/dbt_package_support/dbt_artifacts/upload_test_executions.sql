{% macro fabric__get_test_executions_dml_sql(tests) -%}
    {% if tests != [] %}
        {% set test_execution_values %}
        select
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"
        from ( values
        {% for test in tests -%}
            (
                '{{ invocation_id }}', {# command_invocation_id #}
                '{{ test.node.unique_id }}', {# node_id #}
                '{{ run_started_at }}', {# run_started_at #}

                {% set config_full_refresh = test.node.config.full_refresh %}
                {% if config_full_refresh is none %}
                    {% set config_full_refresh = flags.FULL_REFRESH %}
                {% endif %}
                '{{ config_full_refresh }}', {# was_full_refresh #}

                '{{ test.thread_id }}', {# thread_id #}
                '{{ test.status }}', {# status #}

                {% set compile_started_at = (test.timing | selectattr("name", "eq", "compile") | first | default({}))["started_at"] %}
                {% if compile_started_at %}'{{ compile_started_at }}'{% else %}null{% endif %}, {# compile_started_at #}
                {% set query_completed_at = (test.timing | selectattr("name", "eq", "execute") | first | default({}))["completed_at"] %}
                {% if query_completed_at %}'{{ query_completed_at }}'{% else %}null{% endif %}, {# query_completed_at #}

                {{ test.execution_time }}, {# total_node_runtime #}
                null, {# rows_affected - not available #}
                {{ 'null' if test.failures is none else test.failures }}, {# failures #}
                '{{ test.message | replace("'", "''") }}', {# message #}
                '{{ tojson(test.adapter_response) | replace("'", "''") }}' {# adapter_response #}
            )
            {%- if not loop.last %},{%- endif %}
        {%- endfor %}

        ) v ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13")

        {% endset %}
        {{ test_execution_values }}
    {% else %} {{ return("") }}
    {% endif %}
{% endmacro -%}
