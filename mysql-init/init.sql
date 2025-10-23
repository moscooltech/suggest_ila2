-- MySQL initialization script
-- This will be run when the MySQL container starts for the first time

-- Create database if it doesn't exist (already handled by environment variables)
-- But we can add any additional setup here

-- Set timezone
SET time_zone = '+00:00';

-- Create additional users or permissions if needed
-- GRANT ALL PRIVILEGES ON suggestions_db.* TO 'suggestions_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;