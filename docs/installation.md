# Installation

## Prerequisites

### Python

Make sure you have [Python](https://www.python.org/) 3.11 or higher installed. You can check your Python version by running:

```bash
python --version
```

No other system-level dependencies are required. Unlike Microsoft's upstream dbt-fabric adapter (which depends on pyODBC and requires installing ODBC drivers like `msodbcsql18` and `unixODBC`), this adapter uses [`mssql-python`](https://github.com/microsoft/mssql-python) -- Microsoft's official pure Python driver for SQL Server and Fabric. It handles TDS protocol communication natively, so there is nothing else to install on your system.

## Install dbt-fabric-samdebruyn

=== "Data Warehouse (T-SQL)"

<<<<<<< HEAD
    Install dbt-fabric-samdebruyn for use with Fabric Data Warehouse:

    ```bash
    pip install dbt-fabric-samdebruyn dbt-core
    ```

    This is a drop-in replacement for the original `dbt-fabric` adapter. If you are migrating, run `pip uninstall dbt-fabric` first.

=== "Lakehouse (Spark SQL)"

    Install dbt-fabric-samdebruyn with the Spark extra for use with Fabric Lakehouse:

    ```bash
    pip install dbt-fabric-samdebruyn[spark] dbt-core
    ```

    The `[spark]` extra installs [dbt-spark](https://github.com/dbt-labs/dbt-spark) as a dependency, which provides the base Spark SQL adapter that the FabricSpark adapter builds on.

    !!! info "The `[spark]` extra is only needed for Lakehouse"

        If you only use Fabric Data Warehouse, you do not need the `[spark]` extra. The base `pip install dbt-fabric-samdebruyn dbt-core` is sufficient.

    See the [Lakehouse guide](lakehouse.md) for configuration and usage details.
=======
```bash
pip install dbt-fabric-samdebruyn dbt-core
```

That's it. No ODBC driver setup, no platform-specific steps. The adapter works the same on Linux, macOS, and Windows.
>>>>>>> 8f2c84e (Document mssql-python driver as key differentiator from upstream dbt-fabric)
