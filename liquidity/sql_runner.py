"""Run a .sql file with DuckDB and print the result.

    python -m liquidity.sql_runner sql/01_data_quality.sql

DuckDB queries the parquet file in place (no loading into pandas first), which
is why it is the right tool for a 19-million-row file on a laptop.
"""

import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python -m liquidity.sql_runner <file.sql>")
    import duckdb  # imported here so the rest of the package works without it

    sql = Path(sys.argv[1]).read_text()
    print(duckdb.sql(sql).df().to_string(index=False))


if __name__ == "__main__":
    main()
