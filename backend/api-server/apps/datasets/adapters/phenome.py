from typing import Any, Dict, List, Tuple

from fastapi import HTTPException
from sqlalchemy import func, or_

from basis.core.sqlite_utils import query_sqlite
from db.database import mydb

from apps.datasets.models import PhenomeObservation, PhenomeSubject, PhenomeTrait

from .base import DatasetQueryAdapter


class PhenomeAdapter(DatasetQueryAdapter):
    adapter_name = "phenome"
    display_name = "Phenome SQLite Adapter"
    supported_dataset_types = ["phenome", "phenotype"]
    supported_file_formats = ["db", "sqlite"]

    def supports(self, dataset_payload: Dict[str, Any]) -> bool:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        asset_type = str(asset.get("asset_type") or "").lower()
        file_format = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()
        query_engine = str(asset.get("query_engine") or dataset_payload.get("query_profile", {}).get("query_engine") or "").lower()
        return asset_type == "phenotype_index" or query_engine == "phenome" or file_format in self.supported_file_formats

    def _quote_identifier(self, value: str) -> str:
        return '"' + str(value or "").replace('"', '""') + '"'

    def _list_tables(self, file_path: str) -> List[str]:
        rows = query_sqlite(file_path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [str(item["name"]) for item in rows if item.get("name")]

    def _is_new_schema(self, file_path: str) -> bool:
        """Return True if the SQLite file has trial/plot/observation tables."""
        tables = self._list_tables(file_path)
        return "trial" in tables and "plot" in tables and "observation" in tables

    def _require_phenotype_table(self, file_path: str) -> str:
        tables = self._list_tables(file_path)
        if "phenotype" not in tables:
            raise HTTPException(status_code=400, detail="phenome sqlite does not contain phenotype table")
        return "phenotype"

    def _get_columns(self, file_path: str, table_name: str) -> List[Dict[str, Any]]:
        return query_sqlite(file_path, f"PRAGMA table_info({self._quote_identifier(table_name)})")

    def _get_trait_columns(self, file_path: str, table_name: str) -> List[Dict[str, Any]]:
        columns = self._get_columns(file_path, table_name)
        return [item for item in columns if str(item.get("name") or "") != "ID"]

    def _resolve_index_scope(self, dataset_payload: Dict[str, Any]) -> Dict[str, int]:
        asset = self.get_query_entry_asset(dataset_payload) or {}
        dataset_id = int(dataset_payload.get("id") or 0)
        version_id = int(
            asset.get("version_id")
            or (dataset_payload.get("selected_version") or {}).get("id")
            or (dataset_payload.get("published_version") or {}).get("id")
            or 0
        )
        asset_id = int(asset.get("id") or 0)
        if not dataset_id or not version_id or not asset_id:
            raise HTTPException(status_code=400, detail="phenome index scope is incomplete")
        return {
            "dataset_id": dataset_id,
            "version_id": version_id,
            "asset_id": asset_id,
        }

    def _get_runtime_db(self, dataset_payload: Dict[str, Any]):
        runtime_context = dataset_payload.get("_runtime_context") or {}
        db = runtime_context.get("db")
        if db is not None:
            return db, False
        return mydb.get_dbs(), True

    def _get_index_scope_if_available(self, db, dataset_payload: Dict[str, Any]) -> Dict[str, int] | None:
        try:
            scope = self._resolve_index_scope(dataset_payload)
        except HTTPException:
            return None
        exists = db.query(PhenomeTrait.id).filter_by(**scope).first()
        return scope if exists else None

    def _serialize_trait_item(self, row: PhenomeTrait) -> Dict[str, Any]:
        return {
            "name": row.trait_name or row.trait_code,
            "trait_code": row.trait_code,
            "trait_name": row.trait_name,
            "declared_type": row.value_type,
            "position": row.display_order,
            "time_axis_type": row.time_axis_type,
        }

    def _query_pg_traits(
        self,
        db,
        *,
        scope: Dict[str, int],
        keyword: str | None = None,
        limit: int = 200,
    ) -> Tuple[List[PhenomeTrait], int]:
        query = db.query(PhenomeTrait).filter_by(**scope)
        keyword = str(keyword or "").strip()
        if keyword:
            like_value = f"%{keyword}%"
            query = query.filter(
                or_(
                    PhenomeTrait.trait_code.ilike(like_value),
                    PhenomeTrait.trait_name.ilike(like_value),
                    PhenomeTrait.trait_name_cn.ilike(like_value),
                    PhenomeTrait.trait_name_en.ilike(like_value),
                )
            )
        count = query.count()
        rows = query.order_by(PhenomeTrait.display_order.asc(), PhenomeTrait.id.asc()).limit(limit).all()
        return rows, count

    def _resolve_pg_trait(self, db, *, scope: Dict[str, int], trait_name: str) -> PhenomeTrait:
        normalized = str(trait_name or "").strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="trait is required")
        row = (
            db.query(PhenomeTrait)
            .filter_by(**scope)
            .filter(
                or_(
                    PhenomeTrait.trait_code == normalized,
                    PhenomeTrait.trait_name == normalized,
                )
            )
            .order_by(PhenomeTrait.id.asc())
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"trait not found: {normalized}")
        return row

    def describe(self, dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)
        fmt = str(dataset_payload.get("query_profile", {}).get("file_format") or "").lower()

        if not self._is_new_schema(file_path):
            # -- Old flat phenotype table path --
            table_name = self._require_phenotype_table(file_path)
            trait_columns = self._get_trait_columns(file_path, table_name)

            # Extract real example data from the actual dataset
            example_subject_id = ""
            example_trait_name = ""
            example_trait_search = "花瓣"
            example_timepoint = ""

            try:
                # Get a real subject ID
                rows = query_sqlite(
                    file_path,
                    f"SELECT ID FROM {self._quote_identifier(table_name)} ORDER BY ID ASC LIMIT 1",
                )
                if rows and rows[0].get("ID") is not None:
                    example_subject_id = str(rows[0]["ID"])
            except Exception:
                pass

            if trait_columns:
                example_trait_name = str(trait_columns[0].get("name") or "")
                # Use first real trait name as search keyword
                if example_trait_name:
                    example_trait_search = example_trait_name

            # Check if the table has a timepoint/time column
            try:
                columns = self._get_columns(file_path, table_name)
                col_names = [str(c.get("name") or "").lower() for c in columns]
                for tp_col in ("timepoint", "time_point", "time", "stage", "period"):
                    if tp_col in col_names:
                        tp_rows = query_sqlite(
                            file_path,
                            f"SELECT DISTINCT {self._quote_identifier(tp_col)} FROM {self._quote_identifier(table_name)} WHERE {self._quote_identifier(tp_col)} IS NOT NULL ORDER BY {self._quote_identifier(tp_col)} ASC LIMIT 1",
                        )
                        if tp_rows:
                            val = tp_rows[0].get(tp_col)
                            if val is not None:
                                example_timepoint = str(val)
                        break
            except Exception:
                pass

            return {
                "adapter": self.adapter_name,
                "display_name": self.display_name,
                "dataset_type": dataset_payload.get("dataset_type"),
                "file_format": dataset_payload.get("query_profile", {}).get("file_format"),
                "supported_operations": ["dataset_summary", "trait_list", "trait_search", "subject_list", "subject_detail", "trait_values"],
                "query_entrypoints": ["/api/v1/dataset/query/execute"],
                "examples": {
                    "dataset_summary": {"operation": "dataset_summary", "params": {}},
                    "trait_list": {"operation": "trait_list", "params": {"limit": 20}},
                    "trait_search": {"operation": "trait_search", "params": {"keyword": example_trait_search, "limit": 20}},
                    "subject_list": {"operation": "subject_list", "params": {"limit": 20}},
                    "subject_detail": {"operation": "subject_detail", "params": {"subject_id": example_subject_id}},
                    "trait_values": {"operation": "trait_values", "params": {"trait": example_trait_name, "limit": 20, "timepoint": example_timepoint} if example_timepoint else {"trait": example_trait_name, "limit": 20}},
                },
            }

        # -- New three-table path --
        example_trial_id = ""
        example_plot_id = ""
        example_trait_code = ""
        example_trait_codes: list = []
        example_plot_ids: list = []

        try:
            rows = query_sqlite(file_path, "SELECT id FROM trial ORDER BY id ASC LIMIT 1")
            if rows:
                example_trial_id = str(rows[0]["id"])
        except Exception:
            pass

        try:
            rows = query_sqlite(file_path, "SELECT id, plot_code FROM plot ORDER BY id ASC LIMIT 5")
            if rows:
                example_plot_id = str(rows[0]["id"])
                example_plot_ids = [str(r["id"]) for r in rows]
        except Exception:
            pass

        try:
            rows = query_sqlite(
                file_path,
                "SELECT DISTINCT trait_code FROM observation WHERE value_numeric IS NOT NULL ORDER BY trait_code ASC LIMIT 3",
            )
            if rows:
                example_trait_code = str(rows[0]["trait_code"])
                example_trait_codes = [str(r["trait_code"]) for r in rows]
        except Exception:
            pass

        return {
            "adapter": self.adapter_name,
            "display_name": self.display_name,
            "dataset_type": dataset_payload.get("dataset_type"),
            "file_format": fmt,
            "supported_operations": [
                "trial_list", "trial_detail", "trait_list", "trait_search",
                "plot_list", "plot_detail", "trait_values", "multi_trait_query",
            ],
            "query_entrypoints": ["/api/v1/dataset/query/execute"],
            "examples": {
                "trial_list": {"operation": "trial_list", "params": {}},
                "trial_detail": {"operation": "trial_detail", "params": {"trial_id": example_trial_id}},
                "trait_list": {"operation": "trait_list", "params": {"limit": 20}},
                "trait_search": {"operation": "trait_search", "params": {"keyword": example_trait_code, "limit": 20}},
                "plot_list": {"operation": "plot_list", "params": {"trial_id": example_trial_id, "limit": 20}},
                "plot_detail": {"operation": "plot_detail", "params": {"plot_id": example_plot_id}},
                "trait_values": {"operation": "trait_values", "params": {"trait": example_trait_code, "limit": 20}},
                "multi_trait_query": {
                    "operation": "multi_trait_query",
                    "params": {
                        "trait_codes": example_trait_codes[:2],
                        "plot_ids": example_plot_ids[:3],
                    },
                },
            },
        }

    def _query_trial_list(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get("limit") or 100)
        rows = query_sqlite(
            file_path,
            "SELECT id, trial_name, location, year, season, trial_type, design_type FROM trial ORDER BY id ASC LIMIT ?",
            (limit,),
        )
        return {"items": rows, "count": len(rows)}

    def _query_trial_detail(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        trial_id = params.get("trial_id")
        if not trial_id:
            raise HTTPException(status_code=400, detail="trial_id is required")
        rows = query_sqlite(file_path, "SELECT * FROM trial WHERE id = ?", (trial_id,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"trial not found: {trial_id}")
        plot_count = query_sqlite(
            file_path, "SELECT COUNT(*) AS cnt FROM plot WHERE trial_id = ?", (trial_id,)
        )[0]["cnt"]
        trait_count = query_sqlite(
            file_path,
            "SELECT COUNT(DISTINCT trait_code) AS cnt FROM observation o JOIN plot p ON p.id = o.plot_id WHERE p.trial_id = ?",
            (trial_id,),
        )[0]["cnt"]
        return {"trial": dict(rows[0]), "plot_count": plot_count, "trait_count": trait_count}

    def _query_plot_list(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        trial_id = params.get("trial_id")
        limit = int(params.get("limit") or 100)
        if trial_id:
            rows = query_sqlite(
                file_path,
                "SELECT id, plot_code, subject_name, subject_name_cn, block, rep, germplasm_id FROM plot WHERE trial_id = ? ORDER BY id ASC LIMIT ?",
                (trial_id, limit),
            )
        else:
            rows = query_sqlite(
                file_path,
                "SELECT id, plot_code, subject_name, subject_name_cn, block, rep, germplasm_id FROM plot ORDER BY id ASC LIMIT ?",
                (limit,),
            )
        return {"items": rows, "count": len(rows)}

    def _query_plot_detail(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        plot_id = params.get("plot_id")
        if not plot_id:
            raise HTTPException(status_code=400, detail="plot_id is required")
        rows = query_sqlite(file_path, "SELECT * FROM plot WHERE id = ?", (plot_id,))
        if not rows:
            raise HTTPException(status_code=404, detail=f"plot not found: {plot_id}")
        obs_rows = query_sqlite(
            file_path,
            "SELECT trait_code, value_numeric, value_text, value_category, timepoint, is_missing FROM observation WHERE plot_id = ? ORDER BY trait_code",
            (plot_id,),
        )
        return {"plot": dict(rows[0]), "observations": obs_rows, "observation_count": len(obs_rows)}

    def _query_trait_values_new(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        trait_code = params.get("trait") or params.get("trait_name") or params.get("trait_code")
        if not trait_code:
            raise HTTPException(status_code=400, detail="trait is required")
        trial_id = params.get("trial_id")
        timepoint = params.get("timepoint")
        limit = int(params.get("limit") or 200)

        sql = """
        SELECT p.plot_code, p.subject_name, p.subject_name_cn, o.value_numeric, o.value_text,
               o.value_category, o.timepoint, o.is_missing
        FROM observation o JOIN plot p ON p.id = o.plot_id
        WHERE o.trait_code = ?
        """
        args: list = [trait_code]

        if trial_id:
            sql += " AND p.trial_id = ?"
            args.append(trial_id)
        if timepoint:
            sql += " AND o.timepoint = ?"
            args.append(timepoint)

        sql += " ORDER BY p.id ASC LIMIT ?"
        args.append(limit)

        rows = query_sqlite(file_path, sql, tuple(args))
        items = []
        non_missing = 0
        for r in rows:
            if not r.get("is_missing"):
                non_missing += 1
            items.append({
                "plot_code": r.get("plot_code"),
                "subject_name": r.get("subject_name_cn") or r.get("subject_name"),
                "value_numeric": r.get("value_numeric"),
                "value_text": r.get("value_text"),
                "value_category": r.get("value_category"),
                "timepoint": r.get("timepoint"),
            })
        return {"trait": trait_code, "items": items, "count": len(items), "non_missing_count": non_missing}

    def _query_multi_trait(self, file_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        trait_codes = params.get("trait_codes") or []
        plot_ids = params.get("plot_ids") or []
        if not trait_codes or not plot_ids:
            raise HTTPException(status_code=400, detail="trait_codes and plot_ids are required")

        placeholders_t = ",".join("?" * len(trait_codes))
        placeholders_p = ",".join("?" * len(plot_ids))

        sql = f"""
        SELECT p.id AS plot_id, p.plot_code, p.subject_name, p.subject_name_cn,
               o.trait_code, o.value_numeric, o.value_text, o.timepoint, o.is_missing
        FROM observation o JOIN plot p ON p.id = o.plot_id
        WHERE o.trait_code IN ({placeholders_t}) AND o.plot_id IN ({placeholders_p})
        ORDER BY p.id, o.trait_code
        """
        rows = query_sqlite(file_path, sql, tuple(trait_codes + plot_ids))

        # Build plot x trait matrix
        matrix: Dict[str, Dict[str, Any]] = {}
        plot_info: Dict[str, str] = {}
        for r in rows:
            pid = str(r.get("plot_code") or r.get("plot_id") or "unknown")
            tc = str(r["trait_code"])
            if pid not in matrix:
                matrix[pid] = {}
                plot_info[pid] = str(r.get("subject_name_cn") or r.get("subject_name") or "")
            matrix[pid][tc] = r.get("value_numeric") if r.get("value_numeric") is not None else r.get("value_text")

        return {
            "trait_codes": trait_codes,
            "plot_ids": list(plot_info.keys()),
            "plot_names": plot_info,
            "matrix": matrix,
            "count": len(rows),
        }

    def _execute_old_trait_list(self, file_path: str, params: Dict[str, Any], dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        is_new = self._is_new_schema(file_path)
        limit = int(params.get("limit") or 200)

        db = None
        should_close_db = False
        try:
            db, should_close_db = self._get_runtime_db(dataset_payload)
            scope = self._get_index_scope_if_available(db, dataset_payload)
            if scope:
                rows, count = self._query_pg_traits(db, scope=scope, limit=limit)
                result = {
                    "adapter": self.adapter_name,
                    "operation": "trait_list",
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "postgresql",
                        "table": "phn_trait",
                        "items": [self._serialize_trait_item(item) for item in rows],
                        "count": count,
                    },
                }
                return result
            # SQLite fallback: old flat table vs new three-table
            if is_new:
                rows = query_sqlite(
                    file_path,
                    "SELECT DISTINCT trait_code FROM observation ORDER BY trait_code LIMIT ?",
                    (limit,),
                )
                items = [{"name": r["trait_code"], "declared_type": None, "position": None} for r in rows]
                return {
                    "adapter": self.adapter_name,
                    "operation": "trait_list",
                    "dataset_id": dataset_payload["id"],
                    "data": {"source": "sqlite", "items": items, "count": len(items), "table": "observation"},
                }
            table_name = self._require_phenotype_table(file_path)
            trait_columns = self._get_trait_columns(file_path, table_name)
            trait_names = [str(item["name"]) for item in trait_columns if item.get("name")]
            items = [
                {
                    "name": str(item["name"]),
                    "declared_type": item.get("type"),
                    "position": item.get("cid"),
                }
                for item in trait_columns[:limit]
            ]
            return {
                "adapter": self.adapter_name,
                "operation": "trait_list",
                "dataset_id": dataset_payload["id"],
                "data": {"source": "sqlite", "items": items, "count": len(trait_names), "table": table_name},
            }
        finally:
            if should_close_db and db is not None:
                db.close()

    def _execute_old_trait_search(self, file_path: str, params: Dict[str, Any], dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        is_new = self._is_new_schema(file_path)
        limit = int(params.get("limit") or 50)
        keyword = str(params.get("keyword") or "").strip()

        db = None
        should_close_db = False
        try:
            db, should_close_db = self._get_runtime_db(dataset_payload)
            scope = self._get_index_scope_if_available(db, dataset_payload)
            if scope:
                rows, count = self._query_pg_traits(db, scope=scope, keyword=keyword, limit=limit)
                result = {
                    "adapter": self.adapter_name,
                    "operation": "trait_search",
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "postgresql",
                        "keyword": keyword,
                        "items": [self._serialize_trait_item(item) for item in rows],
                        "count": count,
                        "table": "phn_trait",
                    },
                }
                return result
            # SQLite fallback: old flat table vs new three-table
            if is_new:
                if keyword:
                    rows = query_sqlite(
                        file_path,
                        "SELECT DISTINCT trait_code FROM observation WHERE trait_code LIKE ? ORDER BY trait_code LIMIT ?",
                        (f"%{keyword}%", limit),
                    )
                else:
                    rows = query_sqlite(
                        file_path,
                        "SELECT DISTINCT trait_code FROM observation ORDER BY trait_code LIMIT ?",
                        (limit,),
                    )
                items = [{"name": r["trait_code"], "declared_type": None, "position": None} for r in rows]
                return {
                    "adapter": self.adapter_name,
                    "operation": "trait_search",
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "sqlite",
                        "keyword": keyword,
                        "items": items,
                        "count": len(items),
                        "table": "observation",
                    },
                }
            table_name = self._require_phenotype_table(file_path)
            trait_columns = self._get_trait_columns(file_path, table_name)
            items = [
                {
                    "name": str(item["name"]),
                    "declared_type": item.get("type"),
                    "position": item.get("cid"),
                }
                for item in trait_columns
                if not keyword or keyword in str(item.get("name") or "")
            ][:limit]
            return {
                "adapter": self.adapter_name,
                "operation": "trait_search",
                "dataset_id": dataset_payload["id"],
                "data": {
                    "source": "sqlite",
                    "keyword": keyword,
                    "items": items,
                    "count": len(items),
                    "table": table_name,
                },
            }
        finally:
            if should_close_db and db is not None:
                db.close()

    def _execute_new(self, file_path: str, operation: str, params: Dict[str, Any], dataset_payload: Dict[str, Any]) -> Dict[str, Any]:
        if operation == "trial_list":
            data = self._query_trial_list(file_path, params)
        elif operation == "trial_detail":
            data = self._query_trial_detail(file_path, params)
        elif operation == "trait_list":
            return self._execute_old_trait_list(file_path, params, dataset_payload)
        elif operation == "trait_search":
            return self._execute_old_trait_search(file_path, params, dataset_payload)
        elif operation == "plot_list":
            data = self._query_plot_list(file_path, params)
        elif operation == "plot_detail":
            data = self._query_plot_detail(file_path, params)
        elif operation == "trait_values":
            data = self._query_trait_values_new(file_path, params)
        elif operation == "multi_trait_query":
            data = self._query_multi_trait(file_path, params)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")

        return {
            "adapter": self.adapter_name,
            "operation": operation,
            "dataset_id": dataset_payload["id"],
            "data": data,
        }

    def execute(self, dataset_payload: Dict[str, Any], operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.require_file_path(dataset_payload)

        if self._is_new_schema(file_path):
            return self._execute_new(file_path, operation, params, dataset_payload)

        # -- Existing old-path code below (unchanged) --
        table_name = self._require_phenotype_table(file_path)
        trait_columns = self._get_trait_columns(file_path, table_name)
        trait_names = [str(item["name"]) for item in trait_columns if item.get("name")]
        db = None
        should_close_db = False
        scope = None
        try:
            db, should_close_db = self._get_runtime_db(dataset_payload)
            scope = self._get_index_scope_if_available(db, dataset_payload)

            if operation == "dataset_summary":
                if scope:
                    subject_count = db.query(func.count(PhenomeSubject.id)).filter_by(**scope).scalar() or 0
                    trait_count = db.query(func.count(PhenomeTrait.id)).filter_by(**scope).scalar() or 0
                    observation_count = db.query(func.count(PhenomeObservation.id)).filter_by(**scope).scalar() or 0
                    preview_rows = (
                        db.query(PhenomeTrait)
                        .filter_by(**scope)
                        .order_by(PhenomeTrait.display_order.asc(), PhenomeTrait.id.asc())
                        .limit(10)
                        .all()
                    )
                    return {
                        "adapter": self.adapter_name,
                        "operation": operation,
                        "dataset_id": dataset_payload["id"],
                        "data": {
                            "source": "postgresql",
                            "table": "phn_*",
                            "subject_count": subject_count,
                            "trait_count": trait_count,
                            "observation_count": observation_count,
                            "traits_preview": [item.trait_name or item.trait_code for item in preview_rows],
                        },
                    }
                row_count = query_sqlite(file_path, f"SELECT COUNT(*) AS count FROM {self._quote_identifier(table_name)}")[0]["count"]
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "sqlite",
                        "table": table_name,
                        "subject_count": row_count,
                        "trait_count": len(trait_names),
                        "traits_preview": trait_names[:10],
                    },
                }

            if operation == "trait_list":
                return self._execute_old_trait_list(file_path, params, dataset_payload)

            if operation == "trait_search":
                return self._execute_old_trait_search(file_path, params, dataset_payload)

            if operation == "subject_list":
                limit = int(params.get("limit") or 100)
                rows = query_sqlite(
                    file_path,
                    f"SELECT ID FROM {self._quote_identifier(table_name)} ORDER BY ID ASC LIMIT ?",
                    (limit,),
                )
                items = [str(item["ID"]) for item in rows if item.get("ID") is not None]
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {"source": "sqlite", "items": items, "count": len(items), "table": table_name},
                }

            if operation == "subject_detail":
                subject_id = params.get("subject_id") or params.get("sample_id") or params.get("id")
                if not subject_id:
                    raise HTTPException(status_code=400, detail="subject_id is required")
                rows = query_sqlite(
                    file_path,
                    f"SELECT * FROM {self._quote_identifier(table_name)} WHERE ID = ? LIMIT 1",
                    (subject_id,),
                )
                if not rows:
                    raise HTTPException(status_code=404, detail=f"subject not found: {subject_id}")
                row = dict(rows[0])
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "sqlite",
                        "subject_id": row.get("ID"),
                        "traits": {key: value for key, value in row.items() if key != "ID"},
                        "table": table_name,
                    },
                }

            if operation == "trait_values":
                trait_name = params.get("trait") or params.get("trait_name") or params.get("trait_code")
                if scope:
                    trait_row = self._resolve_pg_trait(db, scope=scope, trait_name=trait_name)
                    timepoint = str(params.get("timepoint") or "").strip() or None
                    limit = int(params.get("limit") or 200)
                    query = (
                        db.query(PhenomeObservation, PhenomeSubject.subject_id)
                        .join(PhenomeSubject, PhenomeSubject.id == PhenomeObservation.subject_pk)
                        .filter(
                            PhenomeObservation.dataset_id == scope["dataset_id"],
                            PhenomeObservation.version_id == scope["version_id"],
                            PhenomeObservation.asset_id == scope["asset_id"],
                            PhenomeObservation.trait_code == trait_row.trait_code,
                            PhenomeSubject.dataset_id == scope["dataset_id"],
                            PhenomeSubject.version_id == scope["version_id"],
                            PhenomeSubject.asset_id == scope["asset_id"],
                        )
                    )
                    if timepoint:
                        query = query.filter(PhenomeObservation.timepoint == timepoint)
                    rows = (
                        query.order_by(PhenomeSubject.subject_id.asc(), PhenomeObservation.id.asc())
                        .limit(limit)
                        .all()
                    )
                    items = []
                    non_missing_count = 0
                    for observation, subject_id in rows:
                        value = observation.value_numeric
                        if value is None:
                            value = observation.value_text
                        if value is None:
                            value = observation.value_category
                        if not observation.is_missing:
                            non_missing_count += 1
                        items.append(
                            {
                                "subject_id": subject_id,
                                "value": value,
                                "raw_value": observation.raw_value,
                                "timepoint": observation.timepoint,
                            }
                        )
                    return {
                        "adapter": self.adapter_name,
                        "operation": operation,
                        "dataset_id": dataset_payload["id"],
                        "data": {
                            "source": "postgresql",
                            "trait": trait_row.trait_name or trait_row.trait_code,
                            "trait_code": trait_row.trait_code,
                            "timepoint": timepoint,
                            "items": items,
                            "count": len(items),
                            "non_missing_count": non_missing_count,
                            "table": "phn_observation",
                        },
                    }
                if not trait_name:
                    raise HTTPException(status_code=400, detail="trait is required")
                if trait_name not in trait_names:
                    raise HTTPException(status_code=404, detail=f"trait not found: {trait_name}")
                limit = int(params.get("limit") or 200)
                query = (
                    f"SELECT ID, {self._quote_identifier(trait_name)} AS trait_value "
                    f"FROM {self._quote_identifier(table_name)} ORDER BY ID ASC LIMIT ?"
                )
                rows = query_sqlite(file_path, query, (limit,))
                items = [
                    {"subject_id": item.get("ID"), "value": item.get("trait_value")}
                    for item in rows
                ]
                non_missing_count = sum(1 for item in items if item["value"] not in (None, "", "NA"))
                return {
                    "adapter": self.adapter_name,
                    "operation": operation,
                    "dataset_id": dataset_payload["id"],
                    "data": {
                        "source": "sqlite",
                        "trait": trait_name,
                        "items": items,
                        "count": len(items),
                        "non_missing_count": non_missing_count,
                        "table": table_name,
                    },
                }

            raise HTTPException(status_code=400, detail=f"Unsupported operation for phenome adapter: {operation}")
        finally:
            if should_close_db and db is not None:
                db.close()
