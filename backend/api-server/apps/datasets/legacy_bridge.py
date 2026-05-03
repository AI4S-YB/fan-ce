"""Legacy compatibility layer — wraps dataset_registry with the old databases interface.

All methods that previously read/wrote the ``databases`` / ``databases_file`` /
``databases_metadata`` / ``project_database`` tables now use ``DatasetRegistry``
and ``asset_file`` instead.
"""

from types import SimpleNamespace

from apps.datasets.models import AssetFile, DatasetRegistry, DatasetAsset, DatasetVersion


class DatasetLegacyBridge:

    # ── database-level (replaces databases table) ──────────────────────────

    def get_database(self, db, dataset_id):
        """Return a namespace mimicking the old Databases row.

        ``dataset_id`` is the legacy ``databases.id``, which matches
        ``dataset_registry.database_id``.
        """
        registry = db.query(DatasetRegistry).filter(
            DatasetRegistry.database_id == dataset_id,
        ).first()
        if registry:
            return SimpleNamespace(
                id=dataset_id,
                name=registry.title or "",
                user_id=registry.owner_id,
                is_public=bool(registry.is_public),
                is_active=registry.lifecycle_state != "archived",
                type=registry.dataset_type or "generic",
                remark=registry.description_md or "",
                status=0,
                create_time=registry.create_time,
            )
        return None

    def list_databases(self, db, page=0, size=0, filters=None, filters_exp=None, sort="-id"):
        """Return SimpleNamespace list mimicking old database_db.get_list."""
        filters = filters or {}
        query = db.query(DatasetRegistry)

        # Apply simple equality filters
        if filters.get("id"):
            query = query.filter(DatasetRegistry.database_id == filters["id"])
        if filters.get("name"):
            query = query.filter(DatasetRegistry.title.ilike(f"%{filters['name']}%"))
        if filters.get("user_id"):
            query = query.filter(DatasetRegistry.owner_id == filters["user_id"])

        total = query.count()

        # Sort (must be applied before limit/offset)
        if sort:
            desc = sort.startswith("-")
            col_name = sort.lstrip("-")
            col = getattr(DatasetRegistry, col_name, DatasetRegistry.id)
            query = query.order_by(col.desc() if desc else col.asc())

        # Apply pagination
        if size and size > 0:
            query = query.offset((page - 1) * size if page > 0 else 0).limit(size)

        items = []
        for reg in query.all():
            items.append(SimpleNamespace(
                id=reg.database_id,
                name=reg.title or "",
                user_id=reg.owner_id,
                is_public=bool(reg.is_public),
                is_active=reg.lifecycle_state != "archived",
                type=reg.dataset_type or "generic",
                remark=reg.description_md or "",
                status=0,
                create_time=reg.create_time,
            ))

        return {"total": total, "dataList": items}

    def create_database(self, db, obj_in):
        """Create a DatasetRegistry row with auto-generated database_id."""
        # Generate the next database_id
        max_db_id = db.query(DatasetRegistry.database_id).order_by(
            DatasetRegistry.database_id.desc()
        ).first()
        next_db_id = (max_db_id[0] or 0) + 1 if max_db_id else 1

        registry = DatasetRegistry(
            database_id=next_db_id,
            title=obj_in.get("name", "") if isinstance(obj_in, dict) else getattr(obj_in, "name", ""),
            dataset_type="unknown",
            owner_id=obj_in.get("user_id") if isinstance(obj_in, dict) else getattr(obj_in, "user_id", None),
            is_public=obj_in.get("is_public", False) if isinstance(obj_in, dict) else getattr(obj_in, "is_public", False),
            lifecycle_state="draft",
            visibility="private",
            create_time=obj_in.get("create_time") if isinstance(obj_in, dict) else getattr(obj_in, "create_time", None),
        )
        db.add(registry)
        db.flush()
        return registry

    def update_database(self, db, db_obj, obj_in):
        """Update fields on the DatasetRegistry row."""
        registry = db.query(DatasetRegistry).filter(
            DatasetRegistry.database_id == db_obj.id,
        ).first()
        if not registry:
            return

        updates = obj_in if isinstance(obj_in, dict) else obj_in.__dict__
        for key in ("name", "user_id", "is_public", "status", "is_active", "create_time"):
            val = updates.get(key)
            if val is not None:
                if key == "name":
                    registry.title = val
                elif key == "user_id":
                    registry.owner_id = val
                elif key == "is_public":
                    registry.is_public = val
                    registry.visibility = "public" if val else "private"
                # status, is_active — skip, handled by lifecycle_state

        db.flush()

    # ── file-level (replaces databases_file) ───────────────────────────────

    def get_primary_file(self, db, dataset_id):
        """Return the primary file info for a dataset.

        Finds the first query_entry asset and its primary file.
        """
        # Find the current version for this dataset
        version = db.query(DatasetVersion).filter(
            DatasetVersion.database_id == dataset_id,
            DatasetVersion.is_current == 1,
        ).first()
        if not version:
            return None

        # Find query_entry asset
        asset = db.query(DatasetAsset).filter(
            DatasetAsset.dataset_version_id == version.id,
            DatasetAsset.is_query_entry == 1,
        ).first()
        if not asset:
            return None

        # Find primary file on that asset
        file_row = db.query(AssetFile).filter(
            AssetFile.dataset_asset_id == asset.id,
            AssetFile.file_role == "primary",
        ).first()
        if not file_row:
            return None

        return SimpleNamespace(
            id=file_row.id,
            database_id=dataset_id,
            file_name=file_row.file_name,
            name=file_row.file_name,
            path=file_row.local_path or file_row.storage_uri,
            url=file_row.storage_uri,
            size=file_row.file_size or 0,
            type=file_row.file_format,
            data_type=file_row.file_format,
            meta_json=file_row.meta_json or "",
        )

    def create_primary_file(self, db, obj_in):
        """No-op — asset_file creation is handled by the new pipeline."""
        return None

    def update_primary_file(self, db, db_obj, obj_in):
        """No-op — asset_file updates are handled by the new pipeline."""
        return None

    # ── metadata (replaces databases_metadata) ──────────────────────────────

    def list_meta(self, db, dataset_id):
        """Metadata is now on dataset_registry columns and extra_json. Return empty."""
        return []

    # ── project links (replaces project_database) ───────────────────────────

    def list_project_links_by_dataset(self, db, dataset_id):
        """Project links are now in breeding link tables. Return empty."""
        return []

    def list_project_links_by_project(self, db, project_id):
        """Project links are now in breeding link tables. Return empty."""
        return []

    def create_project_link(self, db, obj_in):
        """No-op — project links are handled by breeding."""
        return None

    # ── cascade delete (still uses databases table until fully removed) ─────

    def delete_legacy_cascade(self, db, dataset_id):
        """Delete all legacy records for a dataset."""
        db.query(DatasetRegistry).filter(
            DatasetRegistry.database_id == dataset_id,
        ).delete(synchronize_session=False)


dataset_legacy_bridge = DatasetLegacyBridge()
