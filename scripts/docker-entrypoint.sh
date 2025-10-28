#!/bin/sh
set -e

# Non-interactive seed of DB; ignore failures so container can still start
if [ -f /app/scripts/seed_mock_db.py ]; then
  echo "Seeding mock DB (if needed)..."
  python /app/scripts/seed_mock_db.py || echo "Seeding failed; continuing"
fi

# Run the requested command (e.g., adk web ...)
exec "$@"
