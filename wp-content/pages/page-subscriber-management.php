<?php
/*
Template Name: Subscriber Management
*/

// Ensure only administrators can access this page
if (!current_user_can('manage_options')) {
    wp_die(__('You do not have sufficient permissions to access this page.'));
}

// Include the file with database operations
//require_once(get_template_directory() . '/subscriber-db-operations.php');
require_once(plugin_dir_path(__FILE__) . 'nerf/subscriber-db-operations.php');

// Create the subscriber table if it doesn't exist
create_subscriber_table();

// Enqueue jQuery and our custom script
function enqueue_subscriber_management_scripts() {
    wp_enqueue_script('jquery');
    wp_enqueue_script('subscriber-management', plugins_url('nerf/js/subscriber-management.js'), array('jquery'), '1.0', true);
}
add_action('wp_enqueue_scripts', 'enqueue_subscriber_management_scripts');

// Handle form submissions
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    if (isset($_POST['add_subscriber'])) {
        // Add new subscriber
        $new_subscriber = array(
            'user_id' => sanitize_text_field($_POST['user_id']),
            'subscription_level' => intval($_POST['subscription_level']),
            'current_credits' => intval($_POST['current_credits']),
            'subscription_anniversary' => sanitize_text_field($_POST['subscription_anniversary'])
        );
        add_subscriber($new_subscriber);
    } elseif (isset($_POST['update_subscriber'])) {
        // Update existing subscriber
        $id = intval($_POST['id']);
        $updated_subscriber = array(
            'user_id' => sanitize_text_field($_POST['user_id']),
            'subscription_level' => intval($_POST['subscription_level']),
            'current_credits' => intval($_POST['current_credits']),
            'subscription_anniversary' => sanitize_text_field($_POST['subscription_anniversary'])
        );
        update_subscriber($id, $updated_subscriber);
    } elseif (isset($_POST['delete_subscriber'])) {
        // Delete subscriber
        $id = intval($_POST['id']);
        delete_subscriber($id);
    }
}

// Fetch all subscribers
$subscribers = get_subscribers();

get_header();
?>

<div class="wrap">
    <h1>Subscriber Management</h1>

    <h2>Add New Subscriber</h2>
    <form method="post" action="">
        <input type="hidden" name="add_subscriber" value="1">
        <table class="form-table">
            <tr>
                <th><label for="user_id">User ID</label></th>
                <td><input type="text" name="user_id" id="user_id" class="regular-text" required></td>
            </tr>
            <tr>
                <th><label for="subscription_level">Subscription Level</label></th>
                <td><input type="number" name="subscription_level" id="subscription_level" class="small-text" required></td>
            </tr>
            <tr>
                <th><label for="current_credits">Current Credits</label></th>
                <td><input type="number" name="current_credits" id="current_credits" class="small-text" required></td>
            </tr>
            <tr>
                <th><label for="subscription_anniversary">Subscription Anniversary</label></th>
                <td><input type="date" name="subscription_anniversary" id="subscription_anniversary" class="regular-text" required></td>
            </tr>
        </table>
        <p class="submit"><input type="submit" name="submit" id="submit" class="button button-primary" value="Add Subscriber"></p>
    </form>

    <h2>Subscriber List</h2>
    <table class="wp-list-table widefat fixed striped">
        <thead>
            <tr>
                <th>User ID</th>
                <th>Subscription Level</th>
                <th>Current Credits</th>
                <th>Subscription Anniversary</th>
                <th>Last Reset Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($subscribers as $subscriber): ?>
                <tr>
                    <td><?php echo esc_html($subscriber->user_id); ?></td>
                    <td><?php echo esc_html($subscriber->subscription_level); ?></td>
                    <td><?php echo esc_html($subscriber->current_credits); ?></td>
                    <td><?php echo esc_html($subscriber->subscription_anniversary); ?></td>
                    <td><?php echo esc_html($subscriber->last_reset_date); ?></td>
                    <td>
                        <form method="post" action="" style="display:inline;">
                            <input type="hidden" name="id" value="<?php echo $subscriber->id; ?>">
                            <input type="hidden" name="delete_subscriber" value="1">
                            <input type="submit" class="button button-small" value="Delete" onclick="return confirm('Are you sure you want to delete this subscriber?');">
                        </form>
                        <button class="button button-small edit-subscriber" data-id="<?php echo $subscriber->id; ?>">Edit</button>
                    </td>
                </tr>
            <?php endforeach; ?>
        </tbody>
    </table>

    <div id="edit-subscriber-modal" style="display:none;">
        <h2>Edit Subscriber</h2>
        <form method="post" action="">
            <input type="hidden" name="update_subscriber" value="1">
            <input type="hidden" name="id" id="edit-id">
            <table class="form-table">
                <tr>
                    <th><label for="edit-user_id">User ID</label></th>
                    <td><input type="text" name="user_id" id="edit-user_id" class="regular-text" required></td>
                </tr>
                <tr>
                    <th><label for="edit-subscription_level">Subscription Level</label></th>
                    <td><input type="number" name="subscription_level" id="edit-subscription_level" class="small-text" required></td>
                </tr>
                <tr>
                    <th><label for="edit-current_credits">Current Credits</label></th>
                    <td><input type="number" name="current_credits" id="edit-current_credits" class="small-text" required></td>
                </tr>
                <tr>
                    <th><label for="edit-subscription_anniversary">Subscription Anniversary</label></th>
                    <td><input type="date" name="subscription_anniversary" id="edit-subscription_anniversary" class="regular-text" required></td>
                </tr>
            </table>
            <p class="submit">
                <input type="submit" name="submit" id="submit" class="button button-primary" value="Update Subscriber">
                <button type="button" class="button" id="cancel-edit">Cancel</button>
            </p>
        </form>
    </div>
</div>

<?php
get_footer();
?>
