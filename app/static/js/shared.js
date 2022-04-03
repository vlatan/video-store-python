// sleep time expects milliseconds
function sleep(time) {
    return new Promise((resolve) => setTimeout(resolve, time));
}

// Send/recieve data to/from backend
async function PostData(url = '', data = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response;
}

// Set alert message
function SetAlert(message) {
    var alert = document.createElement('div');
    alert.classList.add('alert');
    alert.innerText = message;
    document.getElementById('footer').prepend(alert);
    sleep(2000).then(() => {
        alert.remove();
    });
}

document.addEventListener('click', function (event) {

    // Modals
    document.querySelectorAll('[data-modal]').forEach(function (element) {
        var modalName = element.dataset.modal;
        var modalBody = document.querySelector(`[data-body="${modalName}"]`);
        var closeModal = event.target.closest(`[data-close="${modalName}"]`);
        if (event.target.closest(`[data-modal="${modalName}"]`)) {
            modalBody.style.display = 'flex';
        } else if (event.target === modalBody || closeModal) {
            modalBody.removeAttribute('style');
        }
    });

    // Dropdown menu
    var dropContent = document.querySelector('.dropdown-content');
    if (dropContent) {
        var notDropped = !dropContent.classList.contains('show-dropdown');
        var usernameClicked = event.target.closest('.username');
        var deleteAccountClicked = event.target.closest('.delete-account');
        var menuNotClicked = !event.target.closest('.show-dropdown');
        if (notDropped && usernameClicked) {
            dropContent.classList.add('show-dropdown');
        } else if (deleteAccountClicked || menuNotClicked) {
            dropContent.classList.remove('show-dropdown');
        }
    }

    // Mobile search form
    var searchForm = document.getElementById('searchForm');
    var logo = document.querySelector('a.logo');
    var arrow = document.querySelector('button.search-arrow')
    var arrowClicked = event.target.closest('button.search-arrow');
    var outsideFormClicked = !event.target.closest('#searchForm');
    if (event.target.closest('.search-button-mobile')) {
        searchForm.style.display = 'flex'
        logo.style.display = "none";
        arrow.style.display = "block";
    } else if (arrowClicked || outsideFormClicked) {
        searchForm.removeAttribute('style');
        logo.removeAttribute('style');
        arrow.removeAttribute('style');
    }
});

// save login state for parent window
var loginState = localStorage.getItem('LoggedIn');
if (loginState) {
    if (loginState === 'bingo') {
        SetAlert("You've been logged in!");
    } else if (loginState === 'bummer') {
        SetAlert("Sorry, something went wrong!");
    }
}
// remove login state
localStorage.removeItem('LoggedIn');