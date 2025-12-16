-- Create table for storing database connections securely
-- Passwords will be hashed with salt for security

CREATE TABLE IF NOT EXISTS database_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL CHECK (port >= 1 AND port <= 65535),
    database_name VARCHAR(63) NOT NULL,
    username VARCHAR(63) NOT NULL,
    password_hash TEXT NOT NULL,  -- Hashed password with salt
    salt TEXT NOT NULL,           -- Unique salt for each password
    ssl_mode VARCHAR(20) DEFAULT 'require' CHECK (ssl_mode IN ('require', 'prefer', 'disable')),
    region VARCHAR(50),
    cloud_provider VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_database_connections_is_active ON database_connections(is_active);
CREATE INDEX IF NOT EXISTS idx_database_connections_cloud_provider ON database_connections(cloud_provider);
CREATE INDEX IF NOT EXISTS idx_database_connections_region ON database_connections(region);

-- Add trigger to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_database_connections_updated_at 
    BEFORE UPDATE ON database_connections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE database_connections IS 'Stores secure database connection configurations with hashed passwords';
COMMENT ON COLUMN database_connections.password_hash IS 'Password hashed with bcrypt/scrypt using individual salt';
COMMENT ON COLUMN database_connections.salt IS 'Unique salt for each password hash';
COMMENT ON COLUMN database_connections.database_name IS 'Name of the database to connect to';