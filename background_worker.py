"""Background Worker for Reminder Service.

This module implements a background worker that polls the database for due reminders
and triggers outgoing calls via the SmartFlo API through the OneCall backend.

The worker:
- Runs continuously, checking for due reminders every 60 seconds (configurable)
- Filters reminders that have a destination_mobile and haven't been processed
- Makes HTTP POST requests to the outgoing call API endpoint
- Updates reminder context with call details on success
- Logs errors without retry on failure
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx

import crud
import database
from config import settings
from logger_config import setup_logger

# Configure logging
logger = setup_logger(__name__, 'worker.log')

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


async def initiate_outgoing_call(reminder) -> Optional[dict]:
    """Initiate an outgoing call for a reminder.

    Makes an HTTP POST request to the OneCall API's outgoing call endpoint.

    Args:
        reminder: Reminder object with destination_mobile

    Returns:
        dict: API response if successful, None if failed
    """
    try:
        # Prepare request payload matching OutgoingCallRequest schema
        # The destination_number expects 10 digits, so strip country code if present
        destination = reminder.destination_mobile
        if destination.startswith('+91'):
            destination = destination[3:]  # Remove +91
        elif destination.startswith('91') and len(destination) == 12:
            destination = destination[2:]  # Remove 91
        elif destination.startswith('+'):
            destination = destination[1:]  # Remove any + prefix

        # Ensure it's exactly 10 digits
        if len(destination) != 10 or not destination.isdigit():
            logger.error(f"Invalid destination number format for reminder {reminder.id}: {reminder.destination_mobile}")
            return None

        payload = {
            "destination_number": destination,
            "custom_identifier": f"reminder_{reminder.id}"
        }

        # Make async HTTP request to outgoing call API
        api_url = f"{settings.OUTGOING_CALL_API_URL}/api/call/initiate"
        logger.info(f"Initiating call for reminder {reminder.id} to {destination}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, json=payload)

            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Call initiated successfully for reminder {reminder.id}: {response_data}")
                return response_data
            else:
                logger.error(
                    f"Failed to initiate call for reminder {reminder.id}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None

    except httpx.TimeoutException:
        logger.error(f"Timeout while initiating call for reminder {reminder.id}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Network error while initiating call for reminder {reminder.id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while initiating call for reminder {reminder.id}: {str(e)}")
        return None


async def process_due_reminders():
    """Process all due reminders and trigger outgoing calls.

    This function:
    1. Queries the database for eligible reminders
    2. Attempts to initiate a call for each reminder
    3. Updates reminder context with call details on success
    4. Logs errors on failure without marking reminder as failed
    """
    db = database.SessionLocal()
    try:
        # Get all eligible reminders
        eligible_reminders = crud.get_due_reminders_for_calls(db)

        if not eligible_reminders:
            logger.debug("No due reminders requiring calls at this time")
            return

        logger.info(f"Found {len(eligible_reminders)} reminder(s) eligible for outgoing calls")

        # Process each reminder
        for reminder in eligible_reminders:
            logger.info(
                f"Processing reminder {reminder.id}: '{reminder.title}' "
                f"for user {reminder.user_mobile}, calling {reminder.destination_mobile}"
            )

            # Get current context and retry count
            context = reminder.context or {}
            retry_count = context.get('call_retry_count', 0)

            # Retry logic: up to 3 attempts with exponential backoff
            max_retries = 3
            call_response = None

            for attempt in range(1, max_retries + 1):
                logger.info(f"Attempt {attempt}/{max_retries} for reminder {reminder.id}")

                # Try to initiate call
                call_response = await initiate_outgoing_call(reminder)

                if call_response:
                    # Success! Update context with call details
                    context['call_initiated'] = True
                    context['call_id'] = call_response.get('call_id')
                    context['call_timestamp'] = datetime.now(timezone.utc).isoformat()
                    context['call_destination'] = reminder.destination_mobile
                    context['call_agent_number'] = call_response.get('agent_number')
                    context['call_retry_count'] = attempt

                    # Update the reminder
                    updates = {'context': context}
                    crud.update_reminder(db, reminder.id, reminder.user_mobile, updates)

                    logger.info(
                        f"Successfully initiated call for reminder {reminder.id} on attempt {attempt}. "
                        f"Call ID: {call_response.get('call_id')}"
                    )
                    break  # Success - exit retry loop
                else:
                    # Failed attempt
                    logger.warning(f"Attempt {attempt} failed for reminder {reminder.id}")

                    if attempt < max_retries:
                        # Wait before retry (exponential backoff: 2s, 4s)
                        delay = 2 ** attempt  # 2, 4, 8 seconds
                        logger.info(f"Waiting {delay}s before next retry...")
                        await asyncio.sleep(delay)
                    else:
                        # All retries exhausted - mark as permanently failed
                        context['call_failed'] = True
                        context['call_retry_count'] = max_retries
                        context['call_failed_timestamp'] = datetime.now(timezone.utc).isoformat()
                        context['call_failed_reason'] = 'Max retries exceeded'

                        logger.info(f"[PERSISTENCE DEBUG] Setting call_failed=True for reminder {reminder.id}")
                        logger.info(f"[PERSISTENCE DEBUG] Context before update: {context}")

                        # Update the reminder with failure info
                        updates = {'context': context}
                        updated_reminder = crud.update_reminder(db, reminder.id, reminder.user_mobile, updates)

                        if updated_reminder:
                            logger.info(f"[PERSISTENCE DEBUG] Context after update: {updated_reminder.context}")
                            logger.info(f"[PERSISTENCE DEBUG] call_failed flag: {updated_reminder.context.get('call_failed', 'NOT SET')}")

                        logger.error(
                            f"All {max_retries} attempts failed for reminder {reminder.id}. "
                            f"Marked as permanently failed. Will not retry again."
                        )

    except Exception as e:
        logger.error(f"Error in process_due_reminders: {str(e)}", exc_info=True)
    finally:
        db.close()


async def worker_loop():
    """Main worker loop that runs continuously.

    Checks for due reminders at the configured interval and processes them.
    """
    logger.info("Background worker started")
    logger.info(f"Worker enabled: {settings.WORKER_ENABLED}")
    logger.info(f"Check interval: {settings.WORKER_CHECK_INTERVAL} seconds")
    logger.info(f"Outgoing call API URL: {settings.OUTGOING_CALL_API_URL}")

    if not settings.WORKER_ENABLED:
        logger.warning("Worker is disabled in configuration. Exiting.")
        return

    iteration = 0
    while not shutdown_requested:
        try:
            iteration += 1
            logger.debug(f"Worker iteration {iteration} started")

            # Process due reminders
            await process_due_reminders()

            logger.debug(f"Worker iteration {iteration} completed")

            # Sleep for the configured interval
            # Break sleep into 1-second intervals to allow quick shutdown
            for _ in range(settings.WORKER_CHECK_INTERVAL):
                if shutdown_requested:
                    break
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in worker loop iteration {iteration}: {str(e)}", exc_info=True)
            # Continue running even if an error occurs
            await asyncio.sleep(5)  # Brief pause before retrying

    logger.info("Background worker shutting down gracefully")


def main():
    """Main entry point for the background worker."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("=" * 60)
    logger.info("Reminder Service - Background Worker")
    logger.info("=" * 60)

    try:
        # Run the worker loop
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in background worker: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info("Background worker stopped")
    sys.exit(0)


if __name__ == "__main__":
    main()
