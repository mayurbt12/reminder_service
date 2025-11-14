"""Simple test script for Reminder Service.

Tests basic CRUD operations with datetime handling.
"""

from datetime import datetime, timedelta, timezone
import crud
import database

def test_reminder_service():
    """Test basic reminder operations"""
    print("=" * 60)
    print("Testing Reminder Service - CRUD Operations")
    print("=" * 60)

    # Get database session
    db = database.SessionLocal()

    try:
        # Test 1: Create a reminder
        print("\n[1] Creating a reminder...")
        due_dt = datetime.now(timezone.utc) + timedelta(hours=2)
        reminder_data = {
            'user_mobile': '+1234567890',
            'title': 'Test Meeting',
            'description': 'This is a test reminder',
            'due_datetime': due_dt,  # datetime object
            'priority': 'high',
            'destination_mobile': '+9876543210',
            'context': {'location': '123 Main St', 'type': 'meeting'}
        }

        reminder = crud.create_reminder(db, reminder_data)
        print(f"✓ Reminder created: {reminder.id}")
        print(f"  Title: {reminder.title}")
        print(f"  Due: {reminder.due_datetime.isoformat()}")
        print(f"  Type of due_datetime: {type(reminder.due_datetime)}")
        assert isinstance(reminder.due_datetime, datetime), "due_datetime should be datetime object!"

        # Test 2: List reminders
        print("\n[2] Listing reminders for user...")
        reminders = crud.get_reminders_by_user(db, '+1234567890')
        print(f"✓ Found {len(reminders)} reminder(s)")
        for r in reminders:
            print(f"  - {r.title} (Due: {r.due_datetime.isoformat()})")
            assert isinstance(r.due_datetime, datetime), "due_datetime should be datetime object!"

        # Test 3: Get specific reminder
        print("\n[3] Getting specific reminder...")
        fetched = crud.get_reminder(db, reminder.id, '+1234567890')
        print(f"✓ Retrieved: {fetched.title}")
        print(f"  Created at: {fetched.created_at.isoformat()}")
        assert isinstance(fetched.created_at, datetime), "created_at should be datetime object!"

        # Test 4: Update reminder
        print("\n[4] Updating reminder...")
        new_due = datetime.now(timezone.utc) + timedelta(hours=3)
        updates = {
            'title': 'Updated Test Meeting',
            'due_datetime': new_due,  # datetime object
            'status': 'completed'
        }
        updated = crud.update_reminder(db, reminder.id, '+1234567890', updates)
        print(f"✓ Updated: {updated.title}")
        print(f"  New due: {updated.due_datetime.isoformat()}")
        print(f"  Status: {updated.status.value}")
        assert isinstance(updated.due_datetime, datetime), "due_datetime should be datetime object!"

        # Test 5: Search reminders
        print("\n[5] Searching reminders...")
        results = crud.search_reminders(db, '+1234567890', 'Test')
        print(f"✓ Found {len(results)} match(es)")

        # Test 6: Check due reminders (should be empty since we set future date)
        print("\n[6] Checking due reminders...")
        due_reminders = crud.get_due_reminders(db, '+1234567890')
        print(f"✓ Due reminders: {len(due_reminders)}")

        # Test 7: Delete reminder
        print("\n[7] Deleting reminder...")
        success = crud.delete_reminder(db, reminder.id, '+1234567890')
        print(f"✓ Deleted: {success}")

        # Verify deletion
        deleted = crud.get_reminder(db, reminder.id, '+1234567890')
        assert deleted is None, "Reminder should be deleted"
        print("✓ Verified deletion")

        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("✓ DateTime handling is correct - using datetime objects, not strings")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_reminder_service()
