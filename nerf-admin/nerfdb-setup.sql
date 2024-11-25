-- Create the database
CREATE DATABASE IF NOT EXISTS nerfbot_db;
USE nerfbot_db;

-- Create the subscription_levels table
CREATE TABLE subscription_levels (
    subscription_level INT PRIMARY KEY,
    max_credits_per_day INT NOT NULL,
    credits_per_shot INT NOT NULL
);

-- Insert default subscription levels
INSERT INTO subscription_levels (subscription_level, max_credits_per_day, credits_per_shot)
VALUES
    (0, 5, 1), 
    (1, 100, 10),
    (2, 200, 8),
    (3, 300, 6);

-- Create the subscribers table
CREATE TABLE subscribers (
    user_id VARCHAR(50) PRIMARY KEY,
    id INT AUTO_INCREMENT UNIQUE,
    subscription_level INT NOT NULL,
    current_credits INT NOT NULL,
    subscription_anniversary DATE NOT NULL,
    last_reset_date DATE NOT NULL,
    FOREIGN KEY (subscription_level) REFERENCES subscription_levels(subscription_level)
);

-- Create the system_config table
CREATE TABLE system_config (
    config_key VARCHAR(50) PRIMARY KEY,
    config_value VARCHAR(255) NOT NULL
);

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value)
VALUES 
    ('min_horizontal_angle', '-45'),
    ('max_horizontal_angle', '45'),
    ('min_vertical_angle', '0'),
    ('max_vertical_angle', '60'),
    ('gun_active', '1'),
    ('subscriber_primary_key', 'user_id'),
    ('home_x', '0'),
    ('home_y', '0');
 
-- Create an event to reset credits every 31 days
DELIMITER //

CREATE EVENT reset_subscriber_credits
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    UPDATE subscribers s
    JOIN subscription_levels sl ON s.subscription_level = sl.subscription_level
    SET 
        s.current_credits = sl.max_credits_per_day,
        s.last_reset_date = CURDATE()
    WHERE DATEDIFF(CURDATE(), s.last_reset_date) >= 31;
END //

DELIMITER ;

-- Enable event scheduler
SET GLOBAL event_scheduler = ON;

-- Create index on subscription_anniversary for efficient credit reset
CREATE INDEX idx_subscription_anniversary ON subscribers(subscription_anniversary);

-- Create index on last_reset_date for efficient credit reset
CREATE INDEX idx_last_reset_date ON subscribers(last_reset_date);
