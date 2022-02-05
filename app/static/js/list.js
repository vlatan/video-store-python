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
        var url = `/post/${remove.dataset.id}/${action}`;
        fetch(url, { method: 'POST' }).then(response => {
            var alert = document.createElement('div');
            document.body.appendChild(alert);
            alert.classList.add('alert');
            if (response.ok) {
                remove.parentElement.remove();
                alert.innerText = messageText;
            } else {
                alert.innerText = "Something went wrong!";
            }
            // function sleep is defined in shared.js
            sleep(2000).then(() => {
                alert.remove();
            });
        });
    }
});