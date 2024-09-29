<?php
// File: nerf-gun-db-operations.php

function create_nerf_gun_config_table() {
    global $wpdb;
    $table_name = $wpdb->prefix . 'system_config';

    // Check if the table already exists
    if($wpdb->get_var("SHOW TABLES LIKE '$table_name'") != $table_name) {
        $charset_collate = $wpdb->get_charset_collate();
        $sql = "CREATE TABLE $table_name (
            config_key VARCHAR(50) PRIMARY KEY,
            config_value VARCHAR(255) NOT NULL
        ) $charset_collate;";

        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
        dbDelta($sql);

        // Insert default values
        $default_values = array(
            'min_horizontal_angle' => '-45',
            'max_horizontal_angle' => '45',
            'min_vertical_angle' => '0',
            'max_vertical_angle' => '60',
            'gun_active' => '0'  // Default to inactive
        );
        foreach ($default_values as $key => $value) {
            $wpdb->insert(
                $table_name,
                array('config_key' => $key, 'config_value' => $value),
                array('%s', '%s')
            );
        }
    }
}

function get_nerf_gun_config() {
    global $wpdb;
    $table_name = $wpdb->prefix . 'system_config';

    $config_values = $wpdb->get_results("
        SELECT config_key, config_value 
        FROM $table_name 
        WHERE config_key IN ('min_horizontal_angle', 'max_horizontal_angle', 'min_vertical_angle', 'max_vertical_angle', 'gun_active')
    ", OBJECT_K);

    return array(
        'min_horizontal' => isset($config_values['min_horizontal_angle']) ? $config_values['min_horizontal_angle']->config_value : -45,
        'max_horizontal' => isset($config_values['max_horizontal_angle']) ? $config_values['max_horizontal_angle']->config_value : 45,
        'min_vertical' => isset($config_values['min_vertical_angle']) ? $config_values['min_vertical_angle']->config_value : 0,
        'max_vertical' => isset($config_values['max_vertical_angle']) ? $config_values['max_vertical_angle']->config_value : 60,
        'gun_active' => isset($config_values['gun_active']) ? $config_values['gun_active']->config_value : '0'
    );
}


function update_nerf_gun_config($config) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'system_config';

    // Start transaction
    $wpdb->query('START TRANSACTION');

    try {
        $keys = ['min_horizontal_angle', 'max_horizontal_angle', 'min_vertical_angle', 'max_vertical_angle', 'gun_active'];
        $values = [$config['min_horizontal'], $config['max_horizontal'], $config['min_vertical'], $config['max_vertical'], $config['gun_active']];

        for ($i = 0; $i < count($keys); $i++) {
            $wpdb->query($wpdb->prepare("
                UPDATE $table_name
                SET config_value = %s
                WHERE config_key = %s
            ", $values[$i], $keys[$i]));
        }

        // If no exception is thrown, commit the transaction
        $wpdb->query('COMMIT');
    } catch (Exception $e) {
        // An exception has been thrown
        // We must rollback the transaction
        $wpdb->query('ROLLBACK');
    }
}

function bad_update_nerf_gun_config($config) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'system_config';

    $wpdb->query($wpdb->prepare("
        INSERT INTO $table_name (config_key, config_value) 
        VALUES 
        ('min_horizontal_angle', %s),
        ('max_horizontal_angle', %s),
        ('min_vertical_angle', %s),
        ('max_vertical_angle', %s),
        ('gun_active', %s)
        ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
    ", $config['min_horizontal'], $config['max_horizontal'], $config['min_vertical'], $config['max_vertical'], $config['gun_active']));
}



