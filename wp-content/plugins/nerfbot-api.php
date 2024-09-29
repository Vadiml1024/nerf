<?php
/**
 * Plugin Name: NerfBot API
 * Description: Provides HTTP endpoints for NerfBot system management
 * Version: 1.1
 * Author: Vadim Lebedev
 */

// Exit if accessed directly
if (!defined('ABSPATH')) {
    exit;
}

// Include necessary files
require_once(plugin_dir_path(__FILE__) . 'nerf/subscriber-db-operations.php');
require_once(plugin_dir_path(__FILE__) . 'nerf/nerf-gun-db-operations.php');

// Register REST API routes
add_action('rest_api_init', function () {
    $routes = array(
        array('route' => '/subscribers', 'methods' => 'GET', 'callback' => 'get_all_subscribers'),
        array('route' => '/subscribers/(?P<id>\d+)', 'methods' => 'GET', 'callback' => 'get_subscriber'),
        array('route' => '/subscribers', 'methods' => 'POST', 'callback' => 'create_subscriber'),
        array('route' => '/subscribers/(?P<id>\d+)', 'methods' => 'PUT', 'callback' => 'update_subscriber_info'),
        array('route' => '/subscribers/(?P<id>\d+)', 'methods' => 'DELETE', 'callback' => 'delete_subscriber_info'),
        array('route' => '/config', 'methods' => 'GET', 'callback' => 'get_nerf_config'),
        array('route' => '/config', 'methods' => 'PUT', 'callback' => 'update_nerf_config'),
        array('route' => '/subscription-levels', 'methods' => 'GET', 'callback' => 'get_subscription_levels'),
        array('route' => '/subscription-levels', 'methods' => 'PUT', 'callback' => 'update_subscription_levels'),
    );

    foreach ($routes as $route) {
        register_rest_route('nerfbot/v1', $route['route'], array(
            'methods' => $route['methods'],
            'callback' => $route['callback'],
            'permission_callback' => 'nerfbot_api_permissions_check',
        ));
    }
});

// Enhanced permission check for API endpoints
function nerfbot_api_permissions_check($request) {
    // Check if user is logged in
    if (!is_user_logged_in()) {
        return new WP_Error('rest_forbidden', 'You must be logged in to access this endpoint.', array('status' => 401));
    }

    // Check if user is an administrator
    if (!current_user_can('manage_options')) {
        return new WP_Error('rest_forbidden', 'You must be an administrator to access this endpoint.', array('status' => 403));
    }

    // Check for a valid nonce in the request headers
    $nonce = $request->get_header('X-WP-Nonce');
    if (!wp_verify_nonce($nonce, 'wp_rest')) {
        return new WP_Error('rest_forbidden', 'Invalid nonce. Please provide a valid nonce.', array('status' => 403));
    }

    // If all checks pass, return true to allow access
    return true;
}

// Subscriber endpoint callbacks
function get_all_subscribers($request) {
    $subscribers = get_subscribers();
    return new WP_REST_Response($subscribers, 200);
}

function get_subscriber($request) {
    $id = $request['id'];
    $subscriber = get_subscriber_by_id($id);
    if ($subscriber) {
        return new WP_REST_Response($subscriber, 200);
    } else {
        return new WP_Error('not_found', 'Subscriber not found', array('status' => 404));
    }
}

function create_subscriber($request) {
    $subscriber = $request->get_json_params();
    $result = add_subscriber($subscriber);
    if ($result) {
        return new WP_REST_Response($subscriber, 201);
    } else {
        return new WP_Error('creation_failed', 'Failed to create subscriber', array('status' => 500));
    }
}

function update_subscriber_info($request) {
    $id = $request['id'];
    $subscriber = $request->get_json_params();
    $result = update_subscriber($id, $subscriber);
    if ($result) {
        return new WP_REST_Response($subscriber, 200);
    } else {
        return new WP_Error('update_failed', 'Failed to update subscriber', array('status' => 500));
    }
}

function delete_subscriber_info($request) {
    $id = $request['id'];
    $result = delete_subscriber($id);
    if ($result) {
        return new WP_REST_Response(null, 204);
    } else {
        return new WP_Error('delete_failed', 'Failed to delete subscriber', array('status' => 500));
    }
}

// Configuration endpoint callbacks
function get_nerf_config($request) {
    $config = get_nerf_gun_config();
    return new WP_REST_Response($config, 200);
}

function update_nerf_config($request) {
    $config = $request->get_json_params();
    $result = update_nerf_gun_config($config);
    if ($result) {
        return new WP_REST_Response($config, 200);
    } else {
        return new WP_Error('update_failed', 'Failed to update configuration', array('status' => 500));
    }
}

// Subscription level endpoint callbacks
function get_subscription_levels($request) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'subscription_levels';
    $levels = $wpdb->get_results("SELECT * FROM $table_name");
    return new WP_REST_Response($levels, 200);
}

function update_subscription_levels($request) {
    global $wpdb;
    $table_name = $wpdb->prefix . 'subscription_levels';
    $levels = $request->get_json_params();
    
    $wpdb->query('START TRANSACTION');
    
    $success = true;
    foreach ($levels as $level) {
        $result = $wpdb->replace(
            $table_name,
            array(
                'subscription_level' => $level['subscription_level'],
                'max_credits_per_day' => $level['max_credits_per_day'],
                'credits_per_shot' => $level['credits_per_shot']
            ),
            array('%d', '%d', '%d')
        );
        if ($result === false) {
            $success = false;
            break;
        }
    }
    
    if ($success) {
        $wpdb->query('COMMIT');
        return new WP_REST_Response($levels, 200);
    } else {
        $wpdb->query('ROLLBACK');
        return new WP_Error('update_failed', 'Failed to update subscription levels', array('status' => 500));
    }
}

function create_subscription_levels_table() {
    // Create subscription_levels table if it doesn't exist
    global $wpdb;
    $table_name = $wpdb->prefix . 'subscription_levels';
    $charset_collate = $wpdb->get_charset_collate();

    $sql = "CREATE TABLE IF NOT EXISTS $table_name (
        subscription_level INT PRIMARY KEY,
        max_credits_per_day INT NOT NULL,
        credits_per_shot INT NOT NULL
    ) $charset_collate;";

    require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
    dbDelta($sql);

    // Insert default subscription levels if the table is empty
    $count = $wpdb->get_var("SELECT COUNT(*) FROM $table_name");
    if ($count == 0) {
        $default_levels = array(
            array('subscription_level' => 1, 'max_credits_per_day' => 100, 'credits_per_shot' => 10),
            array('subscription_level' => 2, 'max_credits_per_day' => 200, 'credits_per_shot' => 8),
            array('subscription_level' => 3, 'max_credits_per_day' => 300, 'credits_per_shot' => 6)
        );
        foreach ($default_levels as $level) {
            $wpdb->insert($table_name, $level);
        }
    }
}

function getSubscriptionDetails($level) {
    global $subscription_levels;

    foreach ($subscription_levels as $subscription) {
        if ($subscription['subscription_level'] == $level) {
            return array(
                'max_credits_per_day' => $subscription['max_credits_per_day'],
                'credits_per_shot' => $subscription['credits_per_shot']
            );
        }
    }

    return null; // Return null if the level does not exist
}
// Activation hook
register_activation_hook(__FILE__, 'nerfbot_api_activate');

function nerfbot_api_activate() {
   // Create necessary tables
    create_subscriber_table();
    create_nerf_gun_config_table();
    create_subscription_levels_table();
    
    // load default subscription levels from the table int a global variable
    global $subscription_levels;
    $subscription_levels = get_subscription_levels();

}

