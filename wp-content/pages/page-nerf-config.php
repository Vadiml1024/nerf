<?php
/*
Template Name: Nerf Gun Configuration
*/

// Ensure only administrators can access this page
if (!current_user_can('manage_options')) {
    wp_die(__('You do not have sufficient permissions to access this page.'));
}

// Include the database operations file
// require_once(get_template_directory() . '/nerf-gun-db-operations.php');
require_once(WP_PLUGIN_DIR . '/nerf/nerf-gun-db-operations.php');


// Create the table if it doesn't exist
create_nerf_gun_config_table();

// Handle form submission
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['update_config'])) {
    // Validate and sanitize input
    $config = array(
        'min_horizontal' => intval($_POST['min_horizontal']),
        'max_horizontal' => intval($_POST['max_horizontal']),
        'min_vertical' => intval($_POST['min_vertical']),
        'max_vertical' => intval($_POST['max_vertical']),
        'gun_active' => isset($_POST['gun_active']) ? '1' : '0'
    );

    // Update the database
    update_nerf_gun_config($config);

/*
    // Call API to update GUNCTRL
    $api_response = wp_remote_post('http://gunctrl-api-url/gun/config', array(
        'body' => $config,
    ));
*/
    if (false && is_wp_error($api_response)) {
        $update_message = 'Error updating GUNCTRL: ' . $api_response->get_error_message();
    } else {
        $update_message = 'Configuration updated successfully.';
    }
}

// Get current values from the database
$config = get_nerf_gun_config();

// get_header();
?>

<div class="wrap">
    <h1>Nerf Gun Configuration</h1>

    <?php if (isset($update_message)) : ?>
        <div class="notice notice-success">
            <p><?php echo esc_html($update_message); ?></p>
        </div>
    <?php endif; ?>

    <form method="post" action="">
        <table class="form-table">
            <tr>
                <th scope="row"><label for="min_horizontal">Minimum Horizontal Angle</label></th>
                <td><input name="min_horizontal" type="number" id="min_horizontal" value="<?php echo esc_attr($config['min_horizontal']); ?>" class="regular-text"></td>
            </tr>
            <tr>
                <th scope="row"><label for="max_horizontal">Maximum Horizontal Angle</label></th>
                <td><input name="max_horizontal" type="number" id="max_horizontal" value="<?php echo esc_attr($config['max_horizontal']); ?>" class="regular-text"></td>
            </tr>
            <tr>
                <th scope="row"><label for="min_vertical">Minimum Vertical Angle</label></th>
                <td><input name="min_vertical" type="number" id="min_vertical" value="<?php echo esc_attr($config['min_vertical']); ?>" class="regular-text"></td>
            </tr>
            <tr>
                <th scope="row"><label for="max_vertical">Maximum Vertical Angle</label></th>
                <td><input name="max_vertical" type="number" id="max_vertical" value="<?php echo esc_attr($config['max_vertical']); ?>" class="regular-text"></td>
            </tr>
            <tr>
                <th scope="row">Gun Status</th>
                <td>
                    <fieldset>
                        <legend class="screen-reader-text"><span>Gun Status</span></legend>
                        <label for="gun_active">
                            <input name="gun_active" type="checkbox" id="gun_active" value="1" <?php checked($config['gun_active'], '1'); ?>>
                            Activate Gun
                        </label>
                    </fieldset>
                </td>
            </tr>
        </table>
        <p class="submit">
            <input type="submit" name="update_config" id="submit" class="button button-primary" value="Update Configuration">
        </p>
    </form>
</div>

<?php get_footer(); ?>

