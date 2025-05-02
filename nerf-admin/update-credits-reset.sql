DELIMITER //

DROP EVENT IF EXISTS reset_subscriber_credits;

CREATE EVENT reset_subscriber_credits
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP
DO
BEGIN
    UPDATE subscribers s
    JOIN subscription_levels sl ON s.subscription_level = sl.subscription_level
    SET 
        s.current_credits = sl.max_credits_per_day,
        s.last_reset_date = CURDATE();
END //

DELIMITER ;
