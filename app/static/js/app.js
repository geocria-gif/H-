document.addEventListener('DOMContentLoaded', function() {
    var alerts = document.querySelectorAll('#flash-messages .alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });

    var tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(function(el) {
        new bootstrap.Tooltip(el);
    });
});

function confirmDelete(message) {
    return confirm(message || 'Tem certeza que deseja excluir?');
}
