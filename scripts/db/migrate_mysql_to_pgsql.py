#!/usr/bin/env python3
"""
One-off migration helper for moving the main application database from MySQL to PostgreSQL.

The repository runtime no longer depends on MySQL. This tool keeps source-MySQL connectivity
as an operator concern by accepting an external SQLAlchemy URL at execution time.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import yaml
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError, SQLAlchemyError
from sqlalchemy.sql.sqltypes import Boolean, JSON


REPO_ROOT = Path(__file__).resolve().parents[2]
API_SERVER_DIR = REPO_ROOT / "backend" / "api-server"
DEFAULT_TARGET_CONFIG = API_SERVER_DIR / "conf" / "config.prod.yaml"

if str(API_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(API_SERVER_DIR))

from db.database import Base  # noqa: E402
import db.init  # noqa: F401,E402


def _fail(message: str, code: int = 1) -> int:
    print(f"[ERROR] {message}", file=sys.stderr)
    return code


def _warn(message: str) -> None:
    print(f"[WARN] {message}", file=sys.stderr)


def _info(message: str) -> None:
    print(f"[INFO] {message}")


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file {path} does not contain a mapping")
    return data


def _build_pgsql_url_from_config(path: Path) -> str:
    config = _load_yaml(path)
    database = config.get("database") or {}
    if database.get("type") != "pgsql":
        raise ValueError(f"{path} is not configured with database.type=pgsql")

    options = config.get("pgsql_options") or {}
    required = ["user", "password", "host", "port", "database"]
    missing = [item for item in required if not options.get(item)]
    if missing:
        raise ValueError(f"{path} is missing pgsql_options fields: {', '.join(missing)}")

    return (
        f"postgresql+psycopg://{options['user']}:{options['password']}"
        f"@{options['host']}:{options['port']}/{options['database']}"
    )


def _create_engine(url: str, role: str) -> Engine:
    try:
        return create_engine(url, future=True)
    except NoSuchModuleError as exc:
        raise RuntimeError(
            f"{role} database URL driver is unavailable: {exc}. "
            f"Install the matching DBAPI only in the migration environment."
        ) from exc


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _target_tables() -> List[Table]:
    return [table for table in Base.metadata.sorted_tables if table.schema is None]


def _quoted_table_name(engine: Engine, table: Table) -> str:
    preparer = engine.dialect.identifier_preparer
    return preparer.format_table(table)


def _resolve_tables(
    *,
    source_engine: Engine,
    include_tables: Sequence[str],
    exclude_tables: Sequence[str],
) -> List[Table]:
    source_table_names = set(inspect(source_engine).get_table_names())
    exclude = set(exclude_tables)

    target_table_map = {table.name: table for table in _target_tables()}
    if include_tables:
        missing = [name for name in include_tables if name not in target_table_map]
        if missing:
            raise ValueError(f"Unknown target tables: {', '.join(missing)}")
        names = [name for name in include_tables if name not in exclude]
    else:
        names = [table.name for table in _target_tables() if table.name not in exclude]

    tables = [target_table_map[name] for name in names if name in source_table_names]
    skipped = [name for name in names if name not in source_table_names]
    for table_name in skipped:
        _warn(f"Table not found in source MySQL, skipping: {table_name}")

    if not tables:
        raise ValueError("No overlapping tables remain between source MySQL and target PostgreSQL")
    return tables


def _ensure_target_schema(target_engine: Engine, tables: Sequence[Table]) -> None:
    target_names = set(inspect(target_engine).get_table_names())
    missing = [table.name for table in tables if table.name not in target_names]
    if missing:
        raise ValueError(
            "Target PostgreSQL is missing tables: "
            + ", ".join(missing)
            + ". Apply schema migrations before copying data."
        )


def _source_table(source_engine: Engine, table_name: str) -> Table:
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=source_engine)


def _normalize_value(value, target_column):
    if value is None:
        return None

    if isinstance(target_column.type, Boolean):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "t", "yes", "y"}:
                return True
            if lowered in {"0", "false", "f", "no", "n"}:
                return False

    if isinstance(target_column.type, JSON) and isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    return value


def _normalize_row(row: Dict[str, object], target_table: Table) -> Dict[str, object]:
    normalized = {}
    for column in target_table.columns:
        if column.name not in row:
            continue
        normalized[column.name] = _normalize_value(row[column.name], column)
    return normalized


def _table_count(engine: Engine, table: Table) -> int:
    with engine.connect() as connection:
        return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def _source_count(engine: Engine, table_name: str) -> int:
    table = _source_table(engine, table_name)
    return _table_count(engine, table)


def _truncate_target_tables(target_engine: Engine, tables: Sequence[Table]) -> None:
    if not tables:
        return

    quoted_names = ", ".join(_quoted_table_name(target_engine, table) for table in tables)
    statement = text(f"TRUNCATE TABLE {quoted_names} RESTART IDENTITY CASCADE")
    with target_engine.begin() as connection:
        connection.execute(statement)


def _reset_sequences(target_engine: Engine, tables: Sequence[Table]) -> None:
    if target_engine.dialect.name != "postgresql":
        return

    with target_engine.begin() as connection:
        for table in tables:
            if "id" not in table.columns:
                continue
            quoted_name = _quoted_table_name(target_engine, table)
            statement = text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(:table_name, 'id'),
                    COALESCE(MAX(id), 1),
                    MAX(id) IS NOT NULL
                )
                FROM {quoted_name}
                """
            )
            connection.execute(statement, {"table_name": table.name})


def _copy_table(
    *,
    source_engine: Engine,
    target_engine: Engine,
    target_table: Table,
    batch_size: int,
) -> int:
    source_table = _source_table(source_engine, target_table.name)
    copied = 0

    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        result = source_connection.execution_options(stream_results=True).execute(select(source_table))
        while True:
            rows = result.mappings().fetchmany(batch_size)
            if not rows:
                break

            payload = [_normalize_row(dict(row), target_table) for row in rows]
            if payload:
                target_connection.execute(target_table.insert(), payload)
                copied += len(payload)

    return copied


def cmd_plan(args: argparse.Namespace) -> int:
    source_engine = _create_engine(args.source_url, "source")
    target_engine = _create_engine(args.target_url, "target")
    tables = _resolve_tables(
        source_engine=source_engine,
        include_tables=_parse_csv(args.tables),
        exclude_tables=_parse_csv(args.exclude_tables),
    )
    _ensure_target_schema(target_engine, tables)

    _info(f"Source: {args.source_url}")
    _info(f"Target: {args.target_url}")
    _info(f"Tables selected: {len(tables)}")

    for table in tables:
        if args.with_counts:
            source_count = _source_count(source_engine, table.name)
            target_count = _table_count(target_engine, table)
            print(f"{table.name}: source={source_count} target={target_count}")
        else:
            print(table.name)

    return 0


def cmd_copy(args: argparse.Namespace) -> int:
    source_engine = _create_engine(args.source_url, "source")
    target_engine = _create_engine(args.target_url, "target")
    tables = _resolve_tables(
        source_engine=source_engine,
        include_tables=_parse_csv(args.tables),
        exclude_tables=_parse_csv(args.exclude_tables),
    )
    _ensure_target_schema(target_engine, tables)

    if args.truncate_target:
        _info("Truncating selected PostgreSQL tables before copy")
        _truncate_target_tables(target_engine, tables)

    for table in tables:
        _info(f"Copying table: {table.name}")
        copied = _copy_table(
            source_engine=source_engine,
            target_engine=target_engine,
            target_table=table,
            batch_size=args.batch_size,
        )
        print(f"{table.name}: copied={copied}")

    _reset_sequences(target_engine, tables)
    _info("Copy complete")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    source_engine = _create_engine(args.source_url, "source")
    target_engine = _create_engine(args.target_url, "target")
    tables = _resolve_tables(
        source_engine=source_engine,
        include_tables=_parse_csv(args.tables),
        exclude_tables=_parse_csv(args.exclude_tables),
    )
    _ensure_target_schema(target_engine, tables)

    mismatches = []
    for table in tables:
        source_count = _source_count(source_engine, table.name)
        target_count = _table_count(target_engine, table)
        status = "OK" if source_count == target_count else "MISMATCH"
        print(f"{table.name}: source={source_count} target={target_count} status={status}")
        if source_count != target_count:
            mismatches.append(table.name)

    if mismatches:
        return _fail("Row-count mismatch detected in: " + ", ".join(mismatches))

    _info("Verification succeeded")
    return 0


def _resolve_target_url(args: argparse.Namespace) -> str:
    if args.target_url:
        return args.target_url
    config_path = Path(args.target_config).resolve()
    return _build_pgsql_url_from_config(config_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate main DB data from MySQL to PostgreSQL")
    parser.add_argument(
        "--source-url",
        default=os.environ.get("MYSQL_SOURCE_URL"),
        help="SQLAlchemy URL for the source MySQL database. Can also be provided via MYSQL_SOURCE_URL.",
    )
    parser.add_argument(
        "--target-url",
        default=os.environ.get("PGSQL_TARGET_URL"),
        help="SQLAlchemy URL for the target PostgreSQL database. Can also be provided via PGSQL_TARGET_URL.",
    )
    parser.add_argument(
        "--target-config",
        default=str(DEFAULT_TARGET_CONFIG),
        help="Fallback PostgreSQL YAML config used when --target-url is omitted.",
    )
    parser.add_argument(
        "--tables",
        help="Comma-separated table allowlist. Defaults to all known ORM tables that also exist in source.",
    )
    parser.add_argument(
        "--exclude-tables",
        help="Comma-separated table denylist.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Show overlapping tables and optional row counts")
    plan_parser.add_argument("--with-counts", action="store_true", help="Query source and target row counts")
    plan_parser.set_defaults(handler=cmd_plan)

    copy_parser = subparsers.add_parser("copy", help="Copy data from MySQL to PostgreSQL")
    copy_parser.add_argument("--batch-size", type=int, default=1000, help="Rows per insert batch")
    copy_parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate selected target tables before copying",
    )
    copy_parser.set_defaults(handler=cmd_copy)

    verify_parser = subparsers.add_parser("verify", help="Compare source and target row counts")
    verify_parser.set_defaults(handler=cmd_verify)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.source_url:
        return _fail("Missing source MySQL URL. Provide --source-url or MYSQL_SOURCE_URL.")

    try:
        args.target_url = _resolve_target_url(args)
        return args.handler(args)
    except (RuntimeError, ValueError, SQLAlchemyError) as exc:
        return _fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
