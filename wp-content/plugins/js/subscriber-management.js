// File: js/subscriber-management.js

(function() {
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    function showModal(modal) {
        modal.style.display = 'block';
    }

    function hideModal(modal) {
        modal.style.display = 'none';
    }

    ready(function() {
        var $ = window.jQuery;
        var editModal = document.getElementById('edit-subscriber-modal');
        var editButtons = document.querySelectorAll('.edit-subscriber');
        var cancelButton = document.getElementById('cancel-edit');

        function handleEditClick(event) {
            var button = event.target;
            var id = button.getAttribute('data-id');
            var row = button.closest('tr');
            var cells = row.getElementsByTagName('td');

            document.getElementById('edit-id').value = id;
            document.getElementById('edit-user_id').value = cells[0].textContent;
            document.getElementById('edit-subscription_level').value = cells[1].textContent;
            document.getElementById('edit-current_credits').value = cells[2].textContent;
            document.getElementById('edit-subscription_anniversary').value = cells[3].textContent;

            showModal(editModal);
        }

        editButtons.forEach(function(button) {
            button.addEventListener('click', handleEditClick);
        });

        cancelButton.addEventListener('click', function() {
            hideModal(editModal);
        });

        // If jQuery is available, use it for any additional functionality
        if ($) {
            // Add any jQuery-specific functionality here
        }
    });
})();

