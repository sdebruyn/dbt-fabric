{% macro fabricspark__persist_docs(relation, model, for_relation, for_columns) -%}
  {% if for_relation and config.persist_relation_docs() and model.description %}
    {% set escaped_comment = model.description | replace("'", "\\'") %}
    {% set comment_query %}
      comment on table {{ relation }} is '{{ escaped_comment }}';
    {% endset %}
    {% do run_query(comment_query) %}
  {% endif %}
  {% if for_columns and config.persist_column_docs() and model.columns %}
    {% do alter_column_comment(relation, model.columns) %}
  {% endif %}
{% endmacro %}

{% macro fabricspark__alter_column_comment(relation, column_dict) %}
  {% set existing_columns = adapter.get_columns_in_relation(relation) %}
  {% set existing_column_names = existing_columns | map(attribute='name') | list %}
  {% for column_name in column_dict %}
    {% if column_name in existing_column_names %}
      {% set comment = column_dict[column_name]['description'] %}
      {% set escaped_comment = comment | replace('\'', '\\\'') %}
      {% set comment_query %}
        alter table {{ relation }} change column
            {{ adapter.quote(column_name) if column_dict[column_name]['quote'] else column_name }}
            comment '{{ escaped_comment }}';
      {% endset %}
      {% do run_query(comment_query) %}
    {% endif %}
  {% endfor %}
{% endmacro %}
