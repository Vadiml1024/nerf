<?php
// File: includes/subscriber-db-operations.php

function create_subscriber_table() {
    global $wpdb;
    $table_name = $wpdb->prefix . 'nerfbot_subscribers';
    
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS $table_name (
        user_id VARCHAR(50) NOT NULL,
        subscription_level INT NOT NULL,
        current_credits INT NOT NULL,
        subscription_anniversary DATE NOT NULL,
        last_reset_date DATE NOT NULL,
        PRIMARY KEY  (user_id)
    ) $charset_collate;";

    require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
    dbDelta($sql);
}

function get_subscribers() {
    global $wpdb;
    $table_name = $wpdb->prefix . 'nerfbot_subscribers';
    return $wpdb->get_results("SELECT * FROM $table_name ORDER BY user_id ASC");
}

function add_subscriber($subscriber) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'nerfbot_subscribers';
    return $wpdb->insert(
        $table_name,
        array(
            'user_id' => $subscriber['user_id'],
            'subscription_level' => $subscriber['subscription_level'],
            'current_credits' => $subscriber['current_credits'],
            'subscription_anniversary' => $subscriber['subscription_anniversary'],
            'last_reset_date' => current_time('mysql', 1)
        )
    );
}


function update_subscriber($subscriber) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'nerfbot_subscribers';
    return $wpdb->update(
        $table_name,
        array(
            'subscription_level' => $subscriber['subscription_level'],
            'current_credits' => $subscriber['current_credits'],
            'subscription_anniversary' => $subscriber['subscription_anniversary'],
            'last_reset_date' => current_time('mysql', 1)
        ),
        array('user_id' => $subscriber['user_id'])
    );
}


function delete_subscriber($id) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'nerfbot_subscribers';
    return $wpdb->delete($table_name, array('user_id' => $id));
}

