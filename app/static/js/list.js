document.addEventListener('click', (event) => {
    var remove = event.target.closest('.remove-option');
    if (remove) {
        var path = window.location.pathname;
        if (path.includes('favorites')) {
            var action = 'unfave';
            var messageText = "Succesfully removed.";
        } else if (path.includes('liked')) {
            var action = 'unlike';
            var messageText = "Succesfully unliked.";
        }
        var url = `/video/${remove.dataset.id}/${action}`;
        fetch(url, { method: 'POST' }).then(response => {
            if (response.ok) {
                remove.parentElement.remove();
                setAlert(messageText);
            } else {
                setAlert("Something went wrong!");
            }
        });
    }
});