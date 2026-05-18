# Pre/post hooks fail at every run boundary: dbt-adapters' default `run_hooks` emits `commit;` that Fabric Warehouse cannot execute

**Repo:** `microsoft/dbt-fabric`
**Labels (suggested):** `bug`, `priority/high`

> [x] **Validated by maintainer** — code refs, line numbers, and claims confirmed against upstream HEAD

> **Internal note (strip before filing):** Submittable as a PR — adds a single `hooks.sql` override file. Consider opening with the issue *and* a draft PR linked from it.

## Summary

The adapter ships no `materializations/hooks.sql`, so dbt-adapters' default `run_hooks` macro runs unchanged. That default emits `commit;` to exit the implicit transaction wrapping a model. Fabric Warehouse does not support `BEGIN`/`COMMIT TRAN`. Every project that uses `pre-hook` or `post-hook` therefore fails at every run boundary.

## Evidence (HEAD [`0de2190`](https://github.com/microsoft/dbt-fabric/tree/0de2190), v1.10.0)

[`dbt/include/fabric/macros/materializations/`](https://github.com/microsoft/dbt-fabric/tree/0de2190/dbt/include/fabric/macros/materializations) contains `models/`, `snapshots/`, `seeds/`, `snapshot/`, but no `hooks.sql`:

```shell
git ls-tree 0de2190 dbt/include/fabric/macros/materializations/ --name-only
# models/
# snapshot/
# snapshots/
# seeds/
```

No `fabric__run_hooks` override exists. dbt-adapters' default — at [`dbt/include/global_project/macros/materializations/hooks.sql`](https://github.com/dbt-labs/dbt-adapters/blob/main/dbt-adapters/src/dbt/include/global_project/macros/materializations/hooks.sql) — calls `commit;` between hook batches.

## Reproduction

Add any `pre-hook` or `post-hook` to a model in a Fabric DW dbt project:

```yaml
# dbt_project.yml
models:
  my_project:
    +pre-hook:
      - "select 1"
```

Run `dbt run`. The hook block fails with a T-SQL error around `commit;`.

## User impact

`pre-hook` / `post-hook` is a core dbt feature ([docs](https://docs.getdbt.com/reference/resource-configs/pre-hook-post-hook)). Any project using it on Fabric Warehouse cannot run unmodified.

## Suggested fix

Add `dbt/include/fabric/macros/materializations/hooks.sql` overriding `run_hooks`:

```jinja
{% macro fabric__run_hooks(hooks, inside_transaction=True) %}
    {% for hook in hooks | selectattr('transaction', 'equalto', inside_transaction) %}
        {% set rendered = render(hook.get('sql')) | trim %}
        {% if (rendered | length) > 0 %}
            {% call statement(auto_begin=inside_transaction) %}
                {{ rendered }}
            {% endcall %}
        {% endif %}
    {% endfor %}
{% endmacro %}
```

Reference fix in the fork: commit `62705a00`.

## Notes

- This is one of the most user-visible bugs in the adapter: anyone running a non-trivial dbt project on Fabric DW will hit it.
- The same fix is needed regardless of whether Fabric eventually supports transactions — `commit;` between non-transactional batches is meaningless and should be omitted.
