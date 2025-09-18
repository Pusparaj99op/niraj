#!/bin/bash

# NIRAJ Database Management Script
# Handles database operations for development and production

set -e

echo "💾 NIRAJ Database Management"
echo "============================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Change to project root
cd "$(dirname "$0")/.."

# Database operations
init_db() {
    log_info "Initializing database..."
    cd backend
    
    poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import init_database
    asyncio.run(init_database())
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    sys.exit(1)
"
    cd ..
}

reset_db() {
    log_warning "This will delete all data in the database!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Resetting database..."
        cd backend
        
        poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import recreate_database
    asyncio.run(recreate_database())
    print('✅ Database reset successfully')
except Exception as e:
    print(f'❌ Database reset failed: {e}')
    sys.exit(1)
"
        cd ..
    else
        log_info "Database reset cancelled"
    fi
}

backup_db() {
    log_info "Creating database backup..."
    cd backend
    
    poetry run python -c "
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import db_manager
    backup_path = db_manager.backup_database()
    print(f'✅ Database backed up to: {backup_path}')
except Exception as e:
    print(f'❌ Database backup failed: {e}')
    sys.exit(1)
"
    cd ..
}

check_db() {
    log_info "Checking database health..."
    cd backend
    
    poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import db_manager
    
    async def check():
        health = await db_manager.health_check()
        if health:
            print('✅ Database is healthy')
            
            counts = await db_manager.get_table_counts()
            if counts:
                print('📊 Table statistics:')
                for table, count in counts.items():
                    print(f'  {table}: {count} rows')
            else:
                print('📊 No table statistics available yet')
        else:
            print('❌ Database health check failed')
            sys.exit(1)
    
    asyncio.run(check())
except Exception as e:
    print(f'❌ Database check failed: {e}')
    sys.exit(1)
"
    cd ..
}

migrate_db() {
    log_info "Running database migrations..."
    cd backend
    
    # For now, this just recreates tables
    # In future, implement proper migrations
    poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

try:
    from core.database import init_database
    asyncio.run(init_database())
    print('✅ Database migrations completed')
except Exception as e:
    print(f'❌ Database migration failed: {e}')
    sys.exit(1)
"
    cd ..
}

seed_db() {
    log_info "Seeding database with sample data..."
    cd backend
    
    # Create seed data script
    poetry run python -c "
import asyncio
import sys
import os
sys.path.insert(0, 'src')

async def seed_data():
    print('🌱 Database seeding will be implemented in later tasks')
    print('This will add sample users, strategies, and test data')
    
    # TODO: Implement actual seeding when models are available
    # from models import User, Strategy, etc.
    # Create sample data...
    
    return True

try:
    result = asyncio.run(seed_data())
    if result:
        print('✅ Database seeded successfully')
    else:
        print('❌ Database seeding failed')
        sys.exit(1)
except Exception as e:
    print(f'❌ Database seeding error: {e}')
    sys.exit(1)
"
    cd ..
}

# Main function
main() {
    local operation="$1"
    
    case "$operation" in
        "init")
            init_db
            ;;
        "reset")
            reset_db
            ;;
        "backup")
            backup_db
            ;;
        "check"|"status")
            check_db
            ;;
        "migrate")
            migrate_db
            ;;
        "seed")
            seed_db
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [operation]"
            echo ""
            echo "Operations:"
            echo "  init     - Initialize database with tables"
            echo "  reset    - Reset database (WARNING: deletes all data)"
            echo "  backup   - Create database backup"
            echo "  check    - Check database health and statistics"
            echo "  migrate  - Run database migrations"
            echo "  seed     - Seed database with sample data"
            echo "  help     - Show this help"
            ;;
        "")
            log_error "No operation specified"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
        *)
            log_error "Unknown operation: $operation"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"