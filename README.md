# dbt-fabric-samdebruyn

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/sdebruyn/dbt-fabric/main/assets/dbt-signature_tm_light.png">
  <img alt="dbt logo" src="https://raw.githubusercontent.com/sdebruyn/dbt-fabric/main/assets/dbt-signature_tm.png">
</picture>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/sdebruyn/dbt-fabric/main/assets/fabric.png">
  <img alt="Fabric logo" src="https://raw.githubusercontent.com/sdebruyn/dbt-fabric/main/assets/fabric.png">
</picture>

A maintained and extended fork of the [dbt-fabric](https://github.com/microsoft/dbt-fabric) adapter, supporting **both** Microsoft Fabric compute engines:

- **Fabric Data Warehouse** — T-SQL, uses the mssql-python driver (`type: fabric`)
- **Fabric Lakehouse** — Spark SQL via Livy sessions (`type: fabricspark`)

This fork has [additional features and bugfixes](https://dbt-fabric.debruyn.dev/feature-comparison/) compared to the original adapter, which was [originally developed by the community](https://github.com/microsoft/dbt-fabric/graphs/contributors) and later adopted by Microsoft. Given Microsoft's limited investments in the adapter, this fork aims to continue its development and maintenance.

[![PyPI - Version](https://img.shields.io/pypi/v/dbt-fabric-samdebruyn)](https://pypi.org/project/dbt-fabric-samdebruyn/)

## Quick start

### Data Warehouse (T-SQL)

Drop-in replacement for the original `dbt-fabric` adapter:

```bash
pip install dbt-fabric-samdebruyn dbt-core
```

If you are migrating from the original adapter, all you need is `pip uninstall dbt-fabric` first.

### Lakehouse (Spark SQL)

```bash
pip install dbt-fabric-samdebruyn[spark] dbt-core
```

This installs [dbt-spark](https://github.com/dbt-labs/dbt-spark) as a dependency. See the [Lakehouse guide](https://dbt-fabric.debruyn.dev/lakehouse/) for configuration and usage.

## Documentation

Full documentation for using dbt with Microsoft Fabric is available at [dbt-fabric.debruyn.dev](https://dbt-fabric.debruyn.dev/).

## Code of Conduct

Everyone interacting in this project's codebases, issues, discussions, and related Slack channels is expected to follow the [dbt Code of Conduct](https://docs.getdbt.com/community/resources/code-of-conduct).

## Acknowledgements

Special thanks to:

* [Jacob Mastel](https://github.com/jacobm001): for his initial work on building dbt-sqlserver.
* [Mikael Ene](https://github.com/mikaelene): for his initial work and continued maintenance on the dbt-sqlserver adapter.
* [Anders Swanson](https://github.com/dataders): for his continued maintenance of the dbt-sqlserver adapter and the creation of the dbt-synapse adapter. And for his work at [dbt Labs](https://www.getdbt.com/).
* [dbt Labs](https://www.getdbt.com/): for their continued support of the dbt open source ecosystem.
* the Microsoft Fabric product team, for their support and contributions to the dbt-fabric adapter.
* every other contributor to dbt-sqlserver, dbt-synapse, and dbt-fabric.
