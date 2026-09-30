"""
LogiTrack - Safe, Idempotent SQLite to PostgreSQL Data Migration Script
Transfers all existing data from local SQLite (app/logitrack.db) into Render PostgreSQL (or target database)
Preserves: Primary Keys (IDs), Foreign Key relationships, Timestamps, Manager/Driver profiles, Shipments, Invoices, and Payments.
"""

import os
import sys
import io
import sqlite3
from datetime import datetime, date

if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure app is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db

# Dependency-ordered table list to respect foreign keys
ORDERED_TABLES = [
    'roles',
    'branches',
    'settings',
    'users',
    'vehicles',
    'customers',
    'drivers',
    'addresses',
    'notifications',
    'activity_logs',
    'container_transfers',
    'shipments',
    'container_shipments',
    'shipment_history',
    'tracking',
    'payments',
    'invoices',
    'feedback'
]

def parse_val_for_column(col_type, val):
    if val is None or isinstance(val, (datetime, date)):
        return val
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        if isinstance(col_type, (db.DateTime, db.Date)):
            is_date_only = isinstance(col_type, db.Date)
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(val_str, fmt)
                    return dt.date() if is_date_only else dt
                except ValueError:
                    pass
            try:
                dt = datetime.fromisoformat(val_str)
                return dt.date() if is_date_only else dt
            except Exception:
                return val
    if isinstance(col_type, db.Boolean) and val is not None:
        return bool(val)
    return val

def migrate_data(source_db_path='app/logitrack.db', target_url=None):
    if not os.path.exists(source_db_path):
        fallback_path = os.path.join(os.path.dirname(__file__), 'app', 'logitrack.db')
        if os.path.exists(fallback_path):
            source_db_path = fallback_path
        else:
            print(f"[ERROR] Source SQLite database not found at {source_db_path}")
            return False

    print("=" * 70)
    print("LOGITRACK DATA MIGRATION: SQLite -> Target Database")
    print("=" * 70)
    print(f"Source SQLite DB: {source_db_path} ({os.path.getsize(source_db_path)} bytes)")

    # Read-only connection to SQLite
    src_conn = sqlite3.connect(f'file:{os.path.abspath(source_db_path)}?mode=ro', uri=True)
    src_conn.row_factory = sqlite3.Row
    src_cur = src_conn.cursor()

    config_mode = os.environ.get('FLASK_CONFIG', os.environ.get('FLASK_ENV', 'production' if os.environ.get('RENDER') else 'default'))
    app = create_app(config_mode)

    with app.app_context():
        target_engine = db.engine
        target_dialect = target_engine.dialect.name
        target_db_url_masked = str(target_engine.url)
        if target_engine.url.password:
            target_db_url_masked = target_db_url_masked.replace(target_engine.url.password, '********')
        
        print(f"Target Database Dialect: {target_dialect}")
        print(f"Target Connection URL:  {target_db_url_masked}")
        print("-" * 70)

        # 1. Ensure target tables exist
        print("[1/3] Ensuring target schema tables exist...")
        db.create_all()
        print("Schema verified in target database.")

        if target_dialect == 'sqlite':
            target_file = target_engine.url.database
            if target_file and os.path.abspath(target_file) == os.path.abspath(source_db_path):
                print(f"[INFO] Target is already the source SQLite database ({source_db_path}).")
                print("[INFO] All data is intact in SQLite. When deploying to Render, set DATABASE_URL to migrate to PostgreSQL.")
                print("=" * 70)
                src_conn.close()
                return True

        # 2. Iterate tables in foreign-key dependency order
        print("\n[2/3] Migrating table data...")
        migration_stats = {}

        metadata = db.metadata
        from sqlalchemy import select, insert, text

        for table_name in ORDERED_TABLES:
            if table_name not in metadata.tables:
                print(f"  [SKIP] Table '{table_name}' not defined in SQLAlchemy metadata.")
                continue

            target_table = metadata.tables[table_name]
            
            src_cur.execute(f"SELECT * FROM \"{table_name}\"")
            src_rows = src_cur.fetchall()
            src_count = len(src_rows)

            inserted_count = 0
            skipped_count = 0

            with target_engine.connect() as conn:
                for row in src_rows:
                    row_dict = dict(row)

                    # Idempotency check: check if record already exists
                    if table_name == 'container_shipments':
                        check_stmt = select(target_table.c.container_id).where(
                            (target_table.c.container_id == row_dict['container_id']) &
                            (target_table.c.shipment_id == row_dict['shipment_id'])
                        )
                    elif 'id' in row_dict:
                        check_stmt = select(target_table.c.id).where(target_table.c.id == row_dict['id'])
                    elif 'setting_key' in row_dict:
                        check_stmt = select(target_table.c.setting_key).where(target_table.c.setting_key == row_dict['setting_key'])
                    else:
                        check_stmt = None

                    exists = False
                    if check_stmt is not None:
                        existing_row = conn.execute(check_stmt).fetchone()
                        if existing_row:
                            exists = True

                    if not exists:
                        valid_data = {}
                        for col in target_table.columns:
                            if col.name in row_dict:
                                valid_data[col.name] = parse_val_for_column(col.type, row_dict[col.name])
                        
                        conn.execute(insert(target_table).values(**valid_data))
                        inserted_count += 1
                    else:
                        skipped_count += 1

                conn.commit()

            # For PostgreSQL, reset sequence counter for tables with auto-increment ID
            if target_dialect == 'postgresql' and table_name != 'container_shipments':
                try:
                    with target_engine.connect() as conn:
                        seq_sql = text(f"""
                            SELECT setval(
                                pg_get_serial_sequence('"{table_name}"', 'id'),
                                coalesce((SELECT max(id) FROM "{table_name}"), 1),
                                true
                            );
                        """)
                        conn.execute(seq_sql)
                        conn.commit()
                except Exception:
                    pass

            with target_engine.connect() as conn:
                target_count = conn.execute(select(db.func.count()).select_from(target_table)).scalar()

            migration_stats[table_name] = {
                'source': src_count,
                'inserted': inserted_count,
                'already_present': skipped_count,
                'target_total': target_count
            }

            status_str = f"Source: {src_count:<4} | Inserted: {inserted_count:<4} | Existing: {skipped_count:<4} | Target Total: {target_count:<4}"
            print(f"  ✓ {table_name:<22} -> {status_str}")

        src_conn.close()

        # 3. Verification Report
        print("\n[3/3] Migration Summary & Key Records Verification:")
        print("-" * 70)
        
        from app.models import User, Role, Branch, Driver, Customer, Shipment, Payment, Invoice
        total_users = User.query.count()
        total_mgrs = User.query.join(Role).filter(Role.name == 'Branch Manager').count()
        total_drivers = Driver.query.count()
        total_customers = Customer.query.count()
        total_branches = Branch.query.count()
        total_shipments = Shipment.query.count()
        total_payments = Payment.query.count()
        total_invoices = Invoice.query.count()

        print(f" Total Users:         {total_users}")
        print(f" Branch Managers:     {total_mgrs}")
        print(f" Drivers:             {total_drivers}")
        print(f" Customers:           {total_customers}")
        print(f" Branches:            {total_branches}")
        print(f" Shipments:           {total_shipments}")
        print(f" Payments:            {total_payments}")
        print(f" Invoices:            {total_invoices}")
        print("=" * 70)
        print("Migration Completed Successfully!")
        return True

if __name__ == '__main__':
    migrate_data()
