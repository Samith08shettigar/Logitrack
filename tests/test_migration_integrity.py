import os
import unittest
import sqlite3
import tempfile
from app import create_app
from app.models import (
    db, User, Role, Branch, Driver, Customer, Vehicle,
    Shipment, Payment, Invoice, ContainerTransfer,
    ShipmentHistory, TrackingLog, Setting, Address, Feedback, Notification, ActivityLog
)
from migrate_sqlite_to_postgres import ORDERED_TABLES, parse_val_for_column, find_source_database

class TestMigrationIntegrity(unittest.TestCase):
    def setUp(self):
        # Create a temporary sqlite target database for migration testing
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.temp_db_fd)
        
        self.app = create_app('testing')
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.temp_db_path}'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_migration_and_data_recovery(self):
        src_db_path = find_source_database()
        self.assertIsNotNone(src_db_path, "Source database must be resolved")
        self.assertTrue(os.path.exists(src_db_path), f"Source database file must exist at {src_db_path}")
        
        src_conn = sqlite3.connect(f'file:{os.path.abspath(src_db_path)}?mode=ro', uri=True)
        src_conn.row_factory = sqlite3.Row
        src_cur = src_conn.cursor()

        metadata = db.metadata
        from sqlalchemy import select, insert

        # Run migration into temp database
        for table_name in ORDERED_TABLES:
            target_table = metadata.tables[table_name]
            src_cur.execute(f"SELECT * FROM \"{table_name}\"")
            src_rows = src_cur.fetchall()

            with db.engine.connect() as conn:
                for row in src_rows:
                    row_dict = dict(row)
                    valid_data = {}
                    for col in target_table.columns:
                        if col.name in row_dict:
                            valid_data[col.name] = parse_val_for_column(col.type, row_dict[col.name])
                    conn.execute(insert(target_table).values(**valid_data))
                conn.commit()

        src_conn.close()

        # 1. Verify exact row counts
        self.assertEqual(User.query.count(), 35, "Expected 35 users")
        self.assertEqual(Branch.query.count(), 5, "Expected 5 branches")
        self.assertEqual(Driver.query.count(), 20, "Expected 20 drivers")
        self.assertEqual(Customer.query.count(), 8, "Expected 8 customers")
        self.assertEqual(Vehicle.query.count(), 20, "Expected 20 vehicles")
        self.assertEqual(Shipment.query.count(), 11, "Expected 11 shipments")
        self.assertEqual(Payment.query.count(), 11, "Expected 11 payments")
        self.assertEqual(Invoice.query.count(), 10, "Expected 10 invoices")
        self.assertEqual(ContainerTransfer.query.count(), 8, "Expected 8 container transfers")
        self.assertEqual(ShipmentHistory.query.count(), 203, "Expected 203 history records")
        self.assertEqual(TrackingLog.query.count(), 147, "Expected 147 tracking logs")
        self.assertEqual(Setting.query.count(), 68, "Expected 68 settings")
        self.assertEqual(Notification.query.count(), 150, "Expected 150 notifications")
        self.assertEqual(ActivityLog.query.count(), 1475, "Expected 1475 activity logs")

        # 2. Verify Managers
        mgr_role = Role.query.filter_by(name='Branch Manager').first()
        self.assertIsNotNone(mgr_role)
        managers = User.query.filter_by(role_id=mgr_role.id).all()
        self.assertEqual(len(managers), 5, "Expected 5 branch managers")
        manager_usernames = [m.username for m in managers]
        self.assertIn('Mumbai_Manager01', manager_usernames)
        self.assertIn('Mangalore_Manager01', manager_usernames)
        self.assertIn('Bangalore_Manager01', manager_usernames)
        self.assertIn('Delhi_Manager01', manager_usernames)
        self.assertIn('Kerala_manager01', manager_usernames)

        # 3. Verify Drivers
        driver_users = User.query.join(Role).filter(Role.name == 'Driver').all()
        self.assertEqual(len(driver_users), 20, "Expected 20 driver user accounts")

        # 4. Verify password checking works for migrated user
        mumbai_mgr = User.query.filter_by(username='Mumbai_Manager01').first()
        self.assertIsNotNone(mumbai_mgr)
        self.assertTrue(mumbai_mgr.check_password('Mumbai@2022'))

        # 5. Verify read/write capability on migrated data
        new_act = ActivityLog(user_id=mumbai_mgr.id, action="Migration Verification", details="Verified write capability", ip_address="127.0.0.1")
        db.session.add(new_act)
        db.session.commit()
        self.assertEqual(ActivityLog.query.count(), 1476)

if __name__ == '__main__':
    unittest.main()
