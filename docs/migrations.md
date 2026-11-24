# Database migrations

DDL rules for PostgreSQL 19 under load, aiming for zero or near-zero downtime.
Migrations are written with Alembic.

## Backward compatibility

- Every migration is backward compatible: the application works with the latest schema and the one before it. So:
  - In the first iteration the schema can be a little more complex than it ultimately needs to be.
  - No drop of a column, table or enum value that a rollback could still use.
  - A constraint is dropped only in extraordinary circumstances, and only when it can be recreated without blocking.
- A column or table is dropped in a later release, over several releases where possible:
  1. Deprecate it.
  2. Stop the application using it.
  3. Make sure the system runs stable without it.
  4. Drop it in a new migration, as a cleanup release.
- Always have a rollback plan, even if it needs complex steps. A controlled short downtime is better than an uncontrolled breakdown.
- Lint every migration with [Squawk](https://squawkhq.com/docs/web-frameworks#alembic-and-sqlalchemy).

## Lock levels

| | `ACCESS EXCLUSIVE` | `SHARE ROW EXCLUSIVE` | `SHARE UPDATE EXCLUSIVE` |
| --- | --- | --- | --- |
| DDL | blocked | blocked | blocked |
| insert / update / delete | blocked | blocked | allowed |
| select | blocked | allowed | allowed |

## Create and drop indexes concurrently

A standard index build locks out writes (not reads) on the table until it finishes, and so does a standard drop.
On any table that changes often, create and drop indexes concurrently.

```sql
CREATE INDEX CONCURRENTLY sales_quantity_index ON sales.sales_table (quantity);

DROP INDEX CONCURRENTLY sales.sales_quantity_index;
```

### Alembic

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "sales_quantity_index",
            "sales_table",
            ["quantity"],
            unique=False,
            postgresql_concurrently=True,
            schema="sales",
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "sales_quantity_index",
            table_name="sales_table",
            postgresql_concurrently=True,
            schema="sales",
        )
```

### Good to know

- `CONCURRENTLY` takes longer but does not block table access.
- It cannot run inside a transaction block, hence `autocommit_block()`.
- It may fail and leave an invalid index behind, which has to be dropped before retrying.
- With the asyncpg driver there is a [known issue](https://github.com/sqlalchemy/alembic/discussions/1461): inside `autocommit_block()` the migration can lose its connection and cannot tell whether the index was created. On a large index the migration fails while the build is still running in the database. Do not panic: check that the migration's changes are in the schema and the index exists, then set `alembic_version` in the database to the failed migration's revision and restart the deployment. The applied migration is skipped and the deployment continues.

### Sources

- [CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)
- [DROP INDEX](https://www.postgresql.org/docs/current/sql-dropindex.html)
- [Building indexes concurrently](https://www.postgresql.org/docs/current/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY)

## Add a foreign key without blocking writes

Declaring a foreign key does not create an index on the referencing columns.
On a rarely queried table that does not matter, but on a loaded system joins get noticeably slower.

Adding a foreign key also scans the table and takes a `SHARE ROW EXCLUSIVE` lock on both tables, which blocks writes to each.
Instead, in separate migrations:

1. Add the foreign key as `NOT VALID`: only new rows are checked.
2. Validate it: this allows reads and writes on the table.
3. Create the index on the referencing column concurrently.

```sql
-- Migration 1
ALTER TABLE child_table
ADD CONSTRAINT parent_id_fk
FOREIGN KEY (parent_id)
REFERENCES parent_table (id)
ON UPDATE CASCADE
ON DELETE CASCADE
NOT VALID;

-- Migration 2
ALTER TABLE child_table VALIDATE CONSTRAINT parent_id_fk;

-- Migration 3
CREATE INDEX CONCURRENTLY parent_id_index ON child_table (parent_id);
```

### Alembic

Migration 1:

```python
def upgrade() -> None:
    op.create_foreign_key(
        "parent_id_fk",
        "child_table",
        "parent_table",
        ["parent_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        onupdate="CASCADE",
        ondelete="CASCADE",
        postgresql_not_valid=True,
    )
```

Migration 2:

```python
def upgrade() -> None:
    op.execute("ALTER TABLE child_table VALIDATE CONSTRAINT parent_id_fk")
```

Migration 3:

```python
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "parent_id_index",
            "child_table",
            ["parent_id"],
            unique=False,
            postgresql_concurrently=True,
            schema="public",
        )
```

### Good to know

- A foreign key references a primary key, the columns of a unique constraint, or the columns of a non-partial unique index.
- Check the data in both tables is consistent before adding the foreign key, or validation fails.
- Think through the cascade behaviour when adding a foreign key.
- An index on the referencing column speeds up a cascading delete but slows writes. Decide which matters more for the table.

### Sources

- [Foreign keys](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [Adding foreign keys with zero downtime](https://travisofthenorth.com/blog/2017/2/2/postgres-adding-foreign-keys-with-zero-downtime)

## Add a value to an enum

By default Alembic adds an enum value by recreating the enum, which changes the column's type and takes an exclusive lock on the table.
`ALTER TYPE ... ADD VALUE` adds it without that lock.
Alembic has no operation for it, so use `op.execute`:

```python
def upgrade() -> None:
    op.execute("ALTER TYPE users.userstatusenum ADD VALUE IF NOT EXISTS 'ACTIVE'")
```

### Good to know

- `IF NOT EXISTS` makes the statement idempotent, and `BEFORE` / `AFTER` keeps the values in order.
- A value added in a transaction cannot be used until that transaction commits.
- A value cannot be dropped without recreating the enum, which changes the column's type twice and locks the table. There is rarely a need: leave the value deprecated.
- When a value really must go: add a new column with a new enum type, copy the values across without the dropped one, drop the old column and type, then rename the new column and type to the old names. Each step follows the backward-compatibility rules above.

### Sources

- [ALTER TYPE](https://www.postgresql.org/docs/current/sql-altertype.html)

## Make a column not null

`ALTER COLUMN ... SET NOT NULL` scans the whole table under an `ACCESS EXCLUSIVE` lock (no reads, no writes) to check every row.
Since PostgreSQL 18, add the not-null constraint as `NOT VALID` instead, then validate it in a separate migration.
Verified on PostgreSQL 19.0: once validated, the column is fully `NOT NULL`, with no further step or cleanup.

```sql
-- Migration 1: brief ACCESS EXCLUSIVE lock, no scan, only new writes are checked
ALTER TABLE users ADD CONSTRAINT users_email_not_null NOT NULL email NOT VALID;

-- Migration 2: SHARE UPDATE EXCLUSIVE lock, reads and writes continue
ALTER TABLE users VALIDATE CONSTRAINT users_email_not_null;
```

Alembic has no operation for either step, so use `op.execute`.

Migration 1:

```python
def upgrade() -> None:
    op.execute("ALTER TABLE users ADD CONSTRAINT users_email_not_null NOT NULL email NOT VALID")
```

Migration 2:

```python
def upgrade() -> None:
    op.execute("ALTER TABLE users VALIDATE CONSTRAINT users_email_not_null")
```

### Good to know

- Validation fails while any row is still null: every existing null is filled before migration 2 runs.
- Validation can take a long time on a big table. Mind the migration timeout.
- Never run `SET NOT NULL` on a column with an invalid not-null constraint: it validates it with the full-table scan under `ACCESS EXCLUSIVE` this recipe avoids.

### Sources

- [ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [NOT NULL as NOT VALID in PostgreSQL 18](https://neon.com/postgresql/postgresql-18/not-null-as-not-valid)

## Further reading

- [Squawk, a linter for PostgreSQL migrations](https://squawkhq.com/)
- [Common DB schema change mistakes](https://postgres.ai/blog/20220525-common-db-schema-change-mistakes)
- [How to update your PostgreSQL database without downtime](https://devcenter.upsun.com/posts/no-downtime-postgres-updates/)
